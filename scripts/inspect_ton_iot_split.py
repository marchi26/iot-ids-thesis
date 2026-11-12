from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.load_data import validate_dataset_file
from src.data.preprocess import build_feature_frame, build_preprocessor, prepare_target
from src.utils.paths import load_config

BASE_COMMIT = "852028abc5ff672bd8e75955cc2b52b23d86d94b"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(csv_path: Path, output: Path) -> None:
    config = load_config()
    targets = [config["dataset"]["binary_target"], config["dataset"]["multiclass_target"]]
    validate_dataset_file(csv_path, targets)
    # Pin the parser rather than silently changing inferred types.
    frame = pd.read_csv(csv_path, engine="pyarrow")
    with csv_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        next(reader)
        if sum(1 for _ in reader) != len(frame):
            raise ValueError("Independent CSV row count does not match the parser")
    features = build_feature_frame(frame, targets)
    requirements = ROOT / "research/ton_iot_audit/requirements.txt"
    packages = [line.split("==")[0] for line in requirements.read_text().splitlines() if "==" in line]
    sources = ["scripts/inspect_ton_iot_split.py", "src/data/preprocess.py",
               "src/data/load_data.py", "src/utils/paths.py", "config/config.yaml",
               "research/ton_iot_audit/requirements.txt"]
    manifest = {
        "stage": "Initial code, dataset and split inspection",
        "base_commit": BASE_COMMIT,
        "execution_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dataset": {"filename": csv_path.name, "sha256": sha256(csv_path),
                    "bytes": csv_path.stat().st_size, "rows": len(frame),
                    "columns": len(frame.columns), "parser": "pyarrow"},
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name) for name in packages},
        "split": {"test_size": float(config["experiment"]["test_size"]),
                  "random_seed": int(config["experiment"]["random_seed"]), "stratified": True,
                  "index_origin": "Reconstructed zero-based CSV data-row positions; header excluded",
                  "limitation": "Historical indices and environment lock are unavailable; matching class counts do not prove historical row identity."},
        "source_sha256": {name: sha256(ROOT / name) for name in sources}, "tasks": {},
    }
    index_frames, distributions, feature_rows = [], [], []
    for mode in ("binary", "multiclass"):
        y, names, _ = prepare_target(frame, mode, *targets)
        train, test = train_test_split(np.arange(len(frame)), stratify=y,
                                      test_size=manifest["split"]["test_size"],
                                      random_state=manifest["split"]["random_seed"])
        if not np.array_equal(np.sort(np.concatenate([train, test])), np.arange(len(frame))):
            raise ValueError("Split positions do not partition the dataset exactly once")
        labels = np.asarray(names)[y.to_numpy()]
        # Inspect training-only column selection; never fit a transformer or a model.
        _, numeric, categorical = build_preprocessor(features.iloc[train],
            scale_numeric=bool(config["preprocessing"].get("scale_numeric", True)))
        selected = list(dict.fromkeys(numeric + categorical))
        if set(selected) & set(targets):
            raise ValueError("A target column was selected as a feature")
        historical_path = ROOT / f"results/metrics/{mode}_random_forest_classification_report.csv"
        historical = pd.read_csv(historical_path, index_col=0)
        counts_match = all(int(historical.loc[name, "support"]) == int((labels[test] == name).sum()) for name in names)
        if not counts_match:
            raise ValueError(f"{mode}: reconstructed class counts differ from saved baseline report")
        manifest["source_sha256"][historical_path.relative_to(ROOT).as_posix()] = sha256(historical_path)
        manifest["tasks"][mode] = {
            "class_names": names, "train_rows": len(train), "test_rows": len(test),
            "numeric_columns": numeric, "categorical_columns": categorical,
            "transformer_input_order": numeric + categorical,
            "selected_source_columns": selected,
            "discarded_by_transformer": [name for name in features if name not in selected],
            "historical_test_class_counts_match": counts_match,
        }
        for partition, positions in (("train", train), ("test", test)):
            index_frames.append(pd.DataFrame({"task": mode, "partition": partition,
                "partition_position": np.arange(len(positions)), "csv_row_index": positions}))
            distributions.extend({"task": mode, "partition": partition, "class": name,
                                  "rows": int((labels[positions] == name).sum())} for name in names)
        for branch, columns in (("numeric", numeric), ("categorical", categorical), ("source_unique", selected)):
            feature_rows.extend({"task": mode, "branch": branch, "position": i, "column": name}
                                for i, name in enumerate(columns))
    output.mkdir(parents=True, exist_ok=True)
    pd.concat(index_frames, ignore_index=True).to_csv(output / "split_indices.csv.gz", index=False,
                                                     compression={"method": "gzip", "mtime": 0})
    pd.DataFrame(distributions).to_csv(output / "class_distribution.csv", index=False)
    pd.DataFrame(feature_rows).to_csv(output / "feature_columns.csv", index=False)
    pd.DataFrame({"column": frame.columns, "dtype": [str(t) for t in frame.dtypes],
                  "missing_rows": frame.isna().sum().to_numpy()}).to_csv(output / "schema.csv", index=False)
    artifacts = ("split_indices.csv.gz", "class_distribution.csv", "feature_columns.csv", "schema.csv")
    manifest["artifacts_sha256"] = {name: sha256(output / name) for name in artifacts}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(pd.DataFrame(distributions).to_string(index=False))
    print("Initial inspection complete. No training or duplicate analysis was executed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect TON IoT dataset, features and reconstructed baseline splits")
    parser.add_argument("--csv", type=Path, default=ROOT / "data/raw/train_test_network.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "research/ton_iot_audit/results")
    args = parser.parse_args()
    try:
        inspect(args.csv.resolve(), args.output.resolve())
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Initial inspection failed: {exc}\n")

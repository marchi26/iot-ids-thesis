"""Audit exact duplicates using the frozen indices from the initial inspection."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INITIAL = ROOT / "research/ton_iot_audit/results"
OUTPUT = INITIAL / "full_audit"
sys.path.insert(0, str(ROOT))

from src.data.preprocess import prepare_target
from src.utils.paths import load_config


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def validate_positions(train: np.ndarray, test: np.ndarray, rows: int) -> None:
    require(len(train) > 0 and len(test) > 0, "Both partitions must contain rows")
    require(all(np.issubdtype(part.dtype, np.integer) for part in (train, test)),
            "Split positions must be integers")
    require(np.array_equal(np.sort(np.concatenate([train, test])), np.arange(rows)),
            "Saved split must partition every CSV row exactly once")


def load_inputs(csv_path: Path, initial: Path):
    require(csv_path.is_file(), f"Dataset not found: {csv_path}. Place train_test_network.csv in data/raw/.")
    manifest = json.loads((initial / "manifest.json").read_text(encoding="utf-8"))
    require(sha256(csv_path) == manifest["dataset"]["sha256"], "Dataset SHA-256 differs from the first delivery")
    for name, expected in manifest["artifacts_sha256"].items():
        require(Path(name).name == name, "Initial artifact name must be a filename")
        require(sha256(initial / name) == expected, f"Initial artifact changed: {name}")
    for name, version in manifest["packages"].items():
        require(importlib.metadata.version(name) == version, f"Use the pinned environment: {name}=={version}")
    require(platform.python_version() == manifest["python"], "Use the Python version recorded in the initial manifest")
    # Ignore checkout newline conversion, but reject changes to the baseline logic.
    for name in ("src/data/preprocess.py", "src/data/load_data.py", "src/utils/paths.py",
                 "config/config.yaml", "src/experiments/export_embedded_model.py"):
        require((ROOT / name).read_text(encoding="utf-8").strip() == git("show", f"{manifest['base_commit']}:{name}"),
                f"Baseline source differs from the frozen base: {name}")
    require(manifest["dataset"]["parser"] == "pyarrow", "Unsupported initial CSV parser")
    frame = pd.read_csv(csv_path, engine="pyarrow")
    require(frame.columns.is_unique and len(frame) > 0, "CSV must have rows and unique columns")
    require(frame.shape == (manifest["dataset"]["rows"], manifest["dataset"]["columns"]), "CSV shape mismatch")
    with csv_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        next(reader)
        require(sum(1 for _ in reader) == len(frame), "Independent CSV row count mismatch")
    saved_schema = pd.read_csv(initial / "schema.csv")
    require(saved_schema["column"].tolist() == frame.columns.tolist(), "CSV column order mismatch")
    require(saved_schema["dtype"].tolist() == [str(t) for t in frame.dtypes], "CSV dtype mismatch")
    require(np.array_equal(saved_schema.missing_rows, frame.isna().sum()), "Missing-value counts changed")
    config = load_config()
    targets = [config["dataset"]["binary_target"], config["dataset"]["multiclass_target"]]
    indices = pd.read_csv(initial / "split_indices.csv.gz")
    distributions = pd.read_csv(initial / "class_distribution.csv")
    saved_features = pd.read_csv(initial / "feature_columns.csv")
    require(set(indices.task) == {"binary", "multiclass"}, "Unexpected tasks in the saved indices")
    require(set(indices.partition) == {"train", "test"}, "Unexpected partitions in the saved indices")
    tasks = {}
    for mode, info in manifest["tasks"].items():
        y, names, _ = prepare_target(frame, mode, *targets)
        require(names == info["class_names"], f"{mode}: class names changed")
        labels = np.asarray(names)[y.to_numpy()]
        positions = {}
        for partition in ("train", "test"):
            subset = indices[(indices.task == mode) & (indices.partition == partition)]
            require(np.array_equal(subset.partition_position, np.arange(len(subset))), "Saved partition order is invalid")
            positions[partition] = subset.csv_row_index.to_numpy()
            require(len(subset) == info[f"{partition}_rows"], "Saved partition size mismatch")
        validate_positions(positions["train"], positions["test"], len(frame))
        for partition, values in positions.items():
            saved = distributions[(distributions.task == mode) & (distributions.partition == partition)]
            require(dict(zip(saved["class"], saved.rows)) == {name: int((labels[values] == name).sum()) for name in names},
                    f"{mode}/{partition}: class distribution changed")
        selected = info["selected_source_columns"]
        saved = saved_features[(saved_features.task == mode) & (saved_features.branch == "source_unique")]
        require(saved["column"].tolist() == selected, "Saved feature order mismatch")
        require(len(selected) == len(set(selected)) and not set(selected) & set(targets), "Invalid source feature list")
        paths = {"A_full_row": frame.columns.tolist(), "B_baseline": selected}
        if mode == "binary":
            # Read the constant without importing or executing the model exporter.
            tree = ast.parse((ROOT / "src/experiments/export_embedded_model.py").read_text(encoding="utf-8"))
            assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                           and any(isinstance(t, ast.Name) and t.id == "EMBEDDED_FEATURES" for t in node.targets)]
            require(len(assignments) == 1, "Embedded feature definition is ambiguous")
            paths["B_embedded"] = ast.literal_eval(assignments[0].value)
        for name, columns in paths.items():
            require(bool(columns) and len(columns) == len(set(columns)) and set(columns) <= set(frame.columns),
                    f"Invalid columns for {name}")
            if name.startswith("B_"):
                require(not set(columns) & set(targets), "Targets must not enter feature-only comparisons")
        tasks[mode] = {"labels": labels, "positions": positions, "paths": paths}
    return frame, manifest, tasks


def duplicate_counts(ids: np.ndarray) -> dict:
    counts = pd.Series(ids).value_counts()
    repeated = counts[counts > 1]
    return {"duplicate_groups": int(len(repeated)), "involved_rows": int(repeated.sum()),
            "excess_rows": int((repeated - 1).sum())}


def audit(frame: pd.DataFrame, labels: np.ndarray, train: np.ndarray, test: np.ndarray):
    require(len(frame) > 0 and len(frame.columns) > 0 and frame.columns.is_unique, "Expected a nonempty frame with unique columns")
    require(len(labels) == len(frame) and not pd.isna(labels).any(), "Labels must be present for every row")
    validate_positions(train, test, len(frame))
    ids = frame.groupby(list(frame.columns), dropna=False, sort=False, observed=True).ngroup().to_numpy()
    shared = np.intersect1d(ids[train], ids[test])
    exposed = np.isin(ids[test], shared)
    label_counts = pd.DataFrame({"group": ids, "label": labels}).groupby("group").label.nunique()
    conflicts = label_counts.index[label_counts > 1].to_numpy()
    summary = {"train_rows": len(train), "test_rows": len(test),
               **{f"train_{k}": v for k, v in duplicate_counts(ids[train]).items()},
               **{f"test_{k}": v for k, v in duplicate_counts(ids[test]).items()},
               "shared_groups": len(shared), "exposed_test_rows": int(exposed.sum()),
               "exposed_test_percent": float(exposed.mean() * 100),
               "conflicting_groups_all": len(conflicts),
               "conflicting_rows_all": int(np.isin(ids, conflicts).sum()),
               "shared_conflicting_groups": len(np.intersect1d(shared, conflicts))}
    per_class = []
    for label in np.unique(labels):
        train_mask, test_mask = labels[train] == label, labels[test] == label
        denominator = int(test_mask.sum())
        per_class.append({"class": str(label), "train_rows": int(train_mask.sum()), "test_rows": denominator,
            **{f"train_{k}": v for k, v in duplicate_counts(ids[train][train_mask]).items()},
            **{f"test_{k}": v for k, v in duplicate_counts(ids[test][test_mask]).items()},
            "exposed_test_rows": int((exposed & test_mask).sum()),
            "exposed_test_percent": float((exposed & test_mask).sum() / denominator * 100) if denominator else None,
            "rows_in_conflicting_groups": int(((labels == label) & np.isin(ids, conflicts)).sum())})
    return summary, per_class


def run(csv_path: Path, initial: Path, output: Path) -> None:
    require(output != initial and output not in initial.parents, "Output must not overwrite the initial delivery")
    started = datetime.now(timezone.utc).isoformat()
    state = {"execution_commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
             "working_tree_status_at_start": git("status", "--porcelain=v1", "--untracked-files=all"),
             "status_scope": "Repository-wide tracked changes and nonignored untracked files; ignored files omitted"}
    frame, initial_manifest, tasks = load_inputs(csv_path, initial)
    sources = ["scripts/audit_ton_iot_split.py", "scripts/verify_ton_iot_audit.py",
               "scripts/test_audit_ton_iot_split.py", "src/data/preprocess.py", "src/data/load_data.py",
               "src/utils/paths.py", "src/experiments/export_embedded_model.py", "config/config.yaml",
               "research/ton_iot_audit/requirements.txt"]
    source_hashes = {name: sha256(ROOT / name) for name in sources}
    summaries, classes, columns = [], [], []
    for task, data in tasks.items():
        for name, features in data["paths"].items():
            summary, per_class = audit(frame[features], data["labels"], **data["positions"])
            summaries.append({"task": task, "audit": name, **summary})
            classes.extend({"task": task, "audit": name, **row} for row in per_class)
            columns.extend({"task": task, "audit": name, "position": i, "column": column}
                           for i, column in enumerate(features))
    require(sha256(csv_path) == initial_manifest["dataset"]["sha256"], "Dataset changed during execution")
    require(all(sha256(ROOT / name) == value for name, value in source_hashes.items()), "Source changed during execution")
    output.mkdir(parents=True, exist_ok=True)
    for filename, rows in (("audit_summary.csv", summaries), ("audit_by_class.csv", classes), ("audit_columns.csv", columns)):
        pd.DataFrame(rows).to_csv(output / filename, index=False, lineterminator="\n")
    manifest = {"stage": "Full exact-duplicate audit on the frozen reconstructed indices",
        "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(), **state,
        "command": "python scripts/audit_ton_iot_split.py",
        "arguments": {"csv": csv_path.as_posix(), "initial": initial.as_posix(), "output": output.as_posix()},
        "initial_manifest_sha256": sha256(initial / "manifest.json"),
        "initial_execution_commit": initial_manifest["execution_commit"],
        "initial_delivery_commit": "f46365e8e46da9b8a1fdb7de85e9150dec5cee25",
        "base_commit": initial_manifest["base_commit"], "dataset": initial_manifest["dataset"],
        "initial_artifacts_sha256": initial_manifest["artifacts_sha256"],
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name) for name in initial_manifest["packages"]},
        "source_sha256": source_hashes, "split": initial_manifest["split"],
        "equality": "Exact equality of parsed CSV values before preprocessing. Missing values in the same column compare equal. No rounding, scaling, deduplication, resampling or fitting.",
        "per_class_duplicates": "Computed within each class and partition; exposure matches training rows of any class.",
        "conflicts": "Distinct active target labels within identical-row groups over the whole CSV; shared conflicts occur in both partitions.",
        "percentage_denominator": "All test rows of the task; per-class percentages use all test rows of that class. Each exposed row is counted once.",
        "tasks": {task: {"audit_columns_in_order": data["paths"]} for task, data in tasks.items()},
        "artifacts_sha256": {name: sha256(output / name) for name in ("audit_summary.csv", "audit_by_class.csv", "audit_columns.csv")}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "data/raw/train_test_network.csv")
    parser.add_argument("--initial", type=Path, default=INITIAL)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        run(args.csv.resolve(), args.initial.resolve(), args.output.resolve())
    except (OSError, ValueError, KeyError, importlib.metadata.PackageNotFoundError) as exc:
        parser.exit(1, f"Audit failed: {exc}\nNo training was executed.\n")

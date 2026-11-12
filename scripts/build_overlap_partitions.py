"""Build SPLIT-02 feasibility artifacts; never fit a transformer or estimator."""
from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, train_test_split

from audit_ton_iot_split import ROOT, INITIAL, git, load_inputs, require, sha256

OUTPUT = ROOT / "research/ton_iot_overlap_impact/results"
SPLIT_SEEDS = [101, 211, 307, 401, 503]
REMOVAL_SEEDS = [601, 701, 809, 907, 1009]
MODEL_SEED = 1103
INNER_SEED = 1201


def exact_groups(frame):
    ids = frame.groupby(list(frame.columns), dropna=False, sort=False, observed=True).ngroup().to_numpy(dtype=np.int64)
    # Independently verify equivalence using full tuples, not digest equality.
    missing = object()
    forward, backward = {}, {}
    for group, row in zip(ids, frame.itertuples(index=False, name=None)):
        key = tuple(missing if pd.isna(value) else value for value in row)
        require(forward.setdefault(key, int(group)) == group, "Equal vectors have different groups")
        require(backward.setdefault(int(group), key) == key, "Different vectors share a group")
    return ids


def remove_overlap(train, test, groups):
    keep = ~np.isin(groups[train], groups[test])
    return train[keep], train[~keep]


def matched_control(train, removed, labels, seed):
    rng = np.random.default_rng(seed)
    selected = []
    for label in np.unique(labels):
        count = int((labels[removed] == label).sum())
        selected.extend(rng.choice(train[labels[train] == label], size=count, replace=False).tolist())
    selected = np.asarray(selected, dtype=np.int64)
    return train[~np.isin(train, selected)], selected


def group_split(rows, labels, groups, folds, seed):
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    left, right = next(splitter.split(np.zeros(len(rows)), labels[rows], groups[rows]))
    return rows[left], rows[right]


def validate(rows, parts, labels, groups, disjoint_test=False):
    joined = np.concatenate(list(parts.values()))
    require(np.array_equal(np.sort(joined), np.sort(rows)), "Partitions must cover each row exactly once")
    require(len(np.unique(joined)) == len(joined), "Overlapping row indices")
    shared = {}
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        shared[f"{a}_{b}"] = int(len(np.intersect1d(groups[parts[a]], groups[parts[b]])))
    if disjoint_test:
        require(not any(shared.values()), "Group leakage in group-disjoint split")
    missing = {part: sorted(set(labels) - set(labels[index])) for part, index in parts.items() if part != "removed"}
    return shared, missing


def save_csv(frame, path):
    if path.suffix == ".gz":
        with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as stream:
                frame.to_csv(stream, index=False, lineterminator="\n")
    else:
        frame.to_csv(path, index=False, lineterminator="\n")


def run(output):
    require(not output.exists(), f"Output already exists; choose a new directory: {output}")
    start = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    frame, initial, tasks = load_inputs(ROOT / "data/raw/train_test_network.csv", INITIAL)
    task = tasks["multiclass"]
    columns = task["paths"]["B_baseline"]
    require(len(columns) == 32 and not set(columns) & {"label", "type", "src_ip", "dst_ip"}, "Feature contract changed")
    labels = task["labels"]
    groups = exact_groups(frame[columns])
    rows = np.arange(len(frame))
    original, fixed_test = task["positions"]["train"], task["positions"]["test"]
    clean, removed = remove_overlap(original, fixed_test, groups)
    candidates = [("fixed_A", original, np.array([], dtype=np.int64), 0),
                  ("fixed_B", clean, removed, 0)]
    for seed in REMOVAL_SEEDS:
        retained, deleted = matched_control(original, removed, labels, seed)
        require(pd.Series(labels[deleted]).value_counts().to_dict() == pd.Series(labels[removed]).value_counts().to_dict(),
                "C removal class counts differ from B")
        candidates.append((f"fixed_C_{seed}", retained, deleted, seed))
    configurations = []
    for name, pool, deleted, seed in candidates:
        train, validation = group_split(pool, labels, groups, 5, INNER_SEED)
        configurations.append((name, {"train": train, "validation": validation, "test": fixed_test, "removed": deleted}, seed, name == "fixed_B"))
    for seed in SPLIT_SEEDS:
        pool, test = train_test_split(rows, test_size=0.2, stratify=labels, random_state=seed)
        train, validation = train_test_split(pool, test_size=0.25, stratify=labels[pool], random_state=INNER_SEED)
        configurations.append((f"random_{seed}", {"train": train, "validation": validation, "test": test}, seed, False))
        pool, test = group_split(rows, labels, groups, 5, seed)
        train, validation = group_split(pool, labels, groups, 4, INNER_SEED)
        configurations.append((f"group_{seed}", {"train": train, "validation": validation, "test": test}, seed, True))
    counts, summaries, indices, checks = [], [], [], []
    for name, parts, seed, group_disjoint in configurations:
        shared, missing = validate(rows, parts, labels, groups, group_disjoint)
        if name.startswith("fixed_"):
            require(np.array_equal(parts["test"], fixed_test), "Fixed test changed")
            require(shared["train_validation"] == 0, "Fixed inner split shares groups")
        pool = np.concatenate([parts["train"], parts["validation"]])
        exposed = np.isin(groups[parts["test"]], groups[pool])
        checks.append({"configuration": name, "missing_classes": missing, "class_coverage_pass": not any(missing.values())})
        summaries.append({"configuration": name, "seed": seed, "train_rows": len(parts["train"]),
                          "validation_rows": len(parts["validation"]), "test_rows": len(parts["test"]),
                          "removed_rows": len(parts.get("removed", [])), **{f"shared_groups_{k}": v for k, v in shared.items()},
                          "pool_test_shared_groups": len(np.intersect1d(groups[pool], groups[parts["test"]])),
                          "test_exposed_to_pool_rows": int(exposed.sum()),
                          "test_exposed_to_pool_percent": float(100 * exposed.mean()),
                          "class_coverage_pass": not any(missing.values())})
        for part, index in parts.items():
            indices.append(pd.DataFrame({"configuration": name, "partition": part, "position": np.arange(len(index)), "row_id": index}))
            for label in np.unique(labels):
                selected = index[labels[index] == label]
                counts.append({"configuration": name, "partition": part, "class": label,
                               "rows": len(selected), "groups": len(np.unique(groups[selected])),
                               "percent_partition": 100 * len(selected) / len(index) if len(index) else 0})
    output.mkdir(parents=True)
    save_csv(pd.concat(indices, ignore_index=True), output / "partition_indices.csv.gz")
    save_csv(pd.DataFrame(summaries), output / "feasibility.csv")
    save_csv(pd.DataFrame(counts), output / "class_counts.csv")
    save_csv(pd.DataFrame({"row_id": rows, "group_id": groups, "class": labels}), output / "row_groups.csv.gz")
    exposed_ids = fixed_test[np.isin(groups[fixed_test], groups[original])]
    save_csv(pd.DataFrame({"row_id": fixed_test, "exposed_to_A": np.isin(fixed_test, exposed_ids)}), output / "fixed_test_subgroups.csv.gz")
    conflict_counts = pd.DataFrame({"group_id": groups, "class": labels}).groupby("group_id")["class"].nunique()
    conflicts = conflict_counts[conflict_counts > 1].index
    details = pd.DataFrame({"group_id": groups, "class": labels})
    save_csv(details[details.group_id.isin(conflicts)].groupby(["group_id", "class"]).size().reset_index(name="rows"), output / "label_conflicts.csv")
    save_csv(pd.DataFrame({"position": range(len(columns)), "column": columns}), output / "feature_columns.csv")
    artifacts = {p.name: sha256(p) for p in sorted(output.iterdir())}
    sources = [Path(__file__), ROOT / "scripts/audit_ton_iot_split.py", ROOT / "src/data/preprocess.py"]
    manifest = {"stage": "SPLIT-02 feasibility only; no model or transformer fit", "started_at_utc": started,
                "execution_commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
                "working_tree_status_at_start": status, "command": "python scripts/build_overlap_partitions.py",
                "output": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
                "dataset": initial["dataset"], "python": initial["python"], "packages": initial["packages"],
                "initial_manifest_sha256": sha256(INITIAL / "manifest.json"),
                "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
                "split_seeds": SPLIT_SEEDS, "removal_seeds": REMOVAL_SEEDS, "inner_seed": INNER_SEED, "model_seed_proposed": MODEL_SEED,
                "group_definition": "Exact parsed 32-feature vector; missing values equal in the same column; no digest-based grouping",
                "group_id_definition": "First occurrence ordinal in the frozen CSV; independently verified with full tuples",
                "all_groups": int(len(np.unique(groups))), "conflicting_groups": int(len(conflicts)),
                "configuration_count": len(configurations), "coverage_checks": checks,
                "training_authorized": False, "feasible_all_classes": all(c["class_coverage_pass"] for c in checks),
                "artifacts_sha256": artifacts, "elapsed_seconds": time.perf_counter() - start}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(pd.DataFrame(summaries).to_string(index=False))
    print("Class coverage:", manifest["feasible_all_classes"], "No training executed.")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        result = run(args.output.resolve())
        sys.exit(0 if result["feasible_all_classes"] else 2)
    except (ValueError, FileNotFoundError) as error:
        print(f"Feasibility check stopped: {error}", file=sys.stderr)
        sys.exit(1)

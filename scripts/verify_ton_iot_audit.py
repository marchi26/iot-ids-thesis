"""Recount every reported value with Python tuples, sets and Counter."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from audit_ton_iot_split import INITIAL, OUTPUT, ROOT, load_inputs, require, sha256


def independent_counts(frame, labels, train, test):
    missing = object()
    rows = [tuple(missing if pd.isna(value) else value for value in row)
            for row in frame.itertuples(index=False, name=None)]
    train_counts = Counter(rows[i] for i in train)
    test_counts = Counter(rows[i] for i in test)
    label_sets = defaultdict(set)
    for row, label in zip(rows, labels):
        label_sets[row].add(label)
    conflicts = {row for row, values in label_sets.items() if len(values) > 1}

    def duplicates(counts):
        sizes = [value for value in counts.values() if value > 1]
        return {"duplicate_groups": len(sizes), "involved_rows": sum(sizes),
                "excess_rows": sum(value - 1 for value in sizes)}

    exposed = sum(count for row, count in test_counts.items() if row in train_counts)
    common = train_counts.keys() & test_counts.keys()
    summary = {"train_rows": len(train), "test_rows": len(test),
        **{f"train_{k}": value for k, value in duplicates(train_counts).items()},
        **{f"test_{k}": value for k, value in duplicates(test_counts).items()},
        "shared_groups": len(common), "exposed_test_rows": exposed,
        "exposed_test_percent": exposed / len(test) * 100,
        "conflicting_groups_all": len(conflicts),
        "conflicting_rows_all": sum(row in conflicts for row in rows),
        "shared_conflicting_groups": len(conflicts & common)}
    per_class = []
    for label in sorted(set(labels)):
        train_class = [i for i in train if labels[i] == label]
        test_class = [i for i in test if labels[i] == label]
        count = sum(rows[i] in train_counts for i in test_class)
        per_class.append({"class": str(label), "train_rows": len(train_class), "test_rows": len(test_class),
            **{f"train_{k}": value for k, value in duplicates(Counter(rows[i] for i in train_class)).items()},
            **{f"test_{k}": value for k, value in duplicates(Counter(rows[i] for i in test_class)).items()},
            "exposed_test_rows": count,
            "exposed_test_percent": count / len(test_class) * 100 if test_class else None,
            "rows_in_conflicting_groups": sum(row in conflicts and value == label for row, value in zip(rows, labels))})
    return summary, per_class


def compare(actual, expected, context):
    for key, value in expected.items():
        if value is None:
            require(pd.isna(actual[key]), f"{context}/{key}: expected an undefined percentage")
        elif isinstance(value, float):
            require(math.isclose(actual[key], value, rel_tol=1e-12, abs_tol=1e-12), f"{context}/{key}: mismatch")
        else:
            require(actual[key] == value, f"{context}/{key}: {actual[key]} != {value}")


def verify(csv_path: Path, initial: Path, output: Path):
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    require(sha256(initial / "manifest.json") == manifest["initial_manifest_sha256"], "Initial manifest changed")
    for name, expected in manifest["artifacts_sha256"].items():
        require(Path(name).name == name, "Invalid output filename")
        require(sha256(output / name) == expected, f"Result hash mismatch: {name}")
    frame, original, tasks = load_inputs(csv_path, initial)
    require(manifest["initial_execution_commit"] == original["execution_commit"], "Historical SHA changed")
    require(manifest["dataset"] == original["dataset"], "Dataset identity changed")
    summaries = pd.read_csv(output / "audit_summary.csv")
    classes = pd.read_csv(output / "audit_by_class.csv")
    columns = pd.read_csv(output / "audit_columns.csv")
    expected_summaries, expected_classes, expected_columns = 0, 0, 0
    for task, data in tasks.items():
        require(manifest["tasks"][task]["audit_columns_in_order"] == data["paths"], "Compared feature lists changed")
        for name, features in data["paths"].items():
            selected = columns[(columns.task == task) & (columns.audit == name)]
            require(selected["column"].tolist() == features and selected.position.tolist() == list(range(len(features))),
                    "Compared column order differs from the frozen definition")
            expected, by_class = independent_counts(frame[features], data["labels"], **data["positions"])
            saved = summaries[(summaries.task == task) & (summaries.audit == name)]
            require(len(saved) == 1, f"{task}/{name}: missing or repeated summary")
            compare(saved.iloc[0], expected, f"{task}/{name}")
            for row in by_class:
                saved = classes[(classes.task == task) & (classes.audit == name) & (classes["class"] == row["class"])]
                require(len(saved) == 1, f"{task}/{name}: missing or repeated class")
                compare(saved.iloc[0], row, f"{task}/{name}/{row['class']}")
            expected_summaries += 1
            expected_classes += len(by_class)
            expected_columns += len(features)
            print(f"{task}/{name}: every summary and per-class field agrees with independent tuple counts")
    require(len(summaries) == expected_summaries and len(classes) == expected_classes
            and len(columns) == expected_columns, "Unexpected extra output rows")
    print("Dataset, frozen indices, artifact hashes, counts and percentages: verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "data/raw/train_test_network.csv")
    parser.add_argument("--initial", type=Path, default=INITIAL)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        verify(args.csv.resolve(), args.initial.resolve(), args.output.resolve())
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Verification failed: {exc}\n")

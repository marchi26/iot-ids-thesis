"""Verify saved SPLIT-02 artifacts independently of the splitting algorithm."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from audit_ton_iot_split import ROOT, require, sha256


def verify_source(path, expected):
    """Match the historical digest exactly, allowing only LF/CRLF conversion."""
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    method = "exact"
    if actual != expected:
        # Reconstruct uniform newline variants, not a new reference digest.
        # Bare CR, whitespace, BOM and the final newline remain significant.
        lf = raw.replace(b"\r\n", b"\n")
        for method, candidate in (("lf", lf), ("crlf", lf.replace(b"\n", b"\r\n"))):
            if hashlib.sha256(candidate).hexdigest() == expected:
                break
        else:
            raise ValueError(f"Execution source changed (not only LF/CRLF): {path}")
    return {"historical_sha256": expected, "checkout_sha256": actual,
            "matched_variant": method}


def verify(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["artifacts_sha256"].items():
        require(sha256(directory / name) == expected, f"Artifact changed: {name}")
    source_checks = {name: verify_source(ROOT / name, expected)
                     for name, expected in manifest["source_sha256"].items()}
    membership = pd.read_csv(directory / "row_groups.csv.gz").set_index("row_id")
    indices = pd.read_csv(directory / "partition_indices.csv.gz")
    summaries = pd.read_csv(directory / "feasibility.csv").set_index("configuration")
    class_counts = pd.read_csv(directory / "class_counts.csv")
    reference_test, removal_counts = None, None
    checked = []
    for name, records in indices.groupby("configuration", sort=True):
        require(sorted(records.row_id.tolist()) == list(range(len(membership))), f"Invalid coverage: {name}")
        parts = {part: block.sort_values("position").row_id.to_numpy() for part, block in records.groupby("partition")}
        parts.setdefault("removed", np.array([], dtype=np.int64))
        for part, rows in parts.items():
            require(len(rows) == int(summaries.loc[name, f"{part}_rows"]), f"Count mismatch: {name}/{part}")
            partition_rows = membership.loc[rows]
            for label in membership["class"].unique():
                selected = partition_rows[partition_rows["class"] == label]
                saved = class_counts[(class_counts.configuration == name) & (class_counts.partition == part) & (class_counts["class"] == label)]
                if part == "removed" and not name.startswith("fixed_"):
                    continue
                require(len(saved) == 1 and int(saved.iloc[0].rows) == len(selected)
                        and int(saved.iloc[0].groups) == selected.group_id.nunique(), f"Class count mismatch: {name}/{part}/{label}")
        group_sets = {part: set(membership.loc[rows].group_id) for part, rows in parts.items()}
        for left, right in [("train", "validation"), ("train", "test"), ("validation", "test")]:
            shared = len(group_sets[left] & group_sets[right])
            require(shared == int(summaries.loc[name, f"shared_groups_{left}_{right}"]), f"Overlap mismatch: {name}")
            if name.startswith("group_") or name == "fixed_B" or (name.startswith("fixed_") and right == "validation"):
                require(shared == 0, f"Unexpected group overlap: {name}")
        pool_groups = group_sets["train"] | group_sets["validation"]
        exposed = membership.loc[parts["test"]].group_id.isin(pool_groups)
        require(int(exposed.sum()) == int(summaries.loc[name, "test_exposed_to_pool_rows"]), f"Exposure mismatch: {name}")
        if name.startswith("fixed_"):
            if reference_test is None:
                reference_test = parts["test"]
            require(np.array_equal(reference_test, parts["test"]), "Fixed test changed")
        if name == "fixed_B":
            removal_counts = membership.loc[parts["removed"], "class"].value_counts().to_dict()
            require(set(membership.loc[parts["removed"]].group_id) <= group_sets["test"], "B removed unrelated rows")
        if name.startswith("fixed_C_"):
            require(membership.loc[parts["removed"], "class"].value_counts().to_dict() == removal_counts, "C/B class mismatch")
        coverage = all(set(membership.loc[parts[p], "class"]) == set(membership["class"]) for p in ["train", "validation", "test"])
        require(coverage == bool(summaries.loc[name, "class_coverage_pass"]), f"Coverage flag mismatch: {name}")
        checked.append({"configuration": name, "checks_passed": True, "all_classes_present": coverage})
    require(len(checked) == manifest["configuration_count"], "Configuration count mismatch")
    test_script = ROOT / "scripts/test_overlap_partitions.py"
    tests = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True)
    require(tests.returncode == 0, f"Synthetic tests failed: {tests.stderr}")
    report = {"manifest_sha256": sha256(directory / "manifest.json"),
              "verifier_sha256": sha256(Path(__file__)), "training_executed": False,
              "source_checks": source_checks,
              "synthetic_tests": {"source_sha256": sha256(test_script), "exit_code": tests.returncode,
                                  "output": tests.stdout + tests.stderr},
              "configuration_checks": checked, "status": "PASS"}
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "research/ton_iot_overlap_impact/results")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    result = verify(args.directory)
    if args.save:
        destination = args.directory / "validation.json"
        require(not destination.exists(), "Validation already exists; will not overwrite")
        destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

import unittest
import tempfile
import json
from pathlib import Path

import numpy as np
import pandas as pd

from audit_ton_iot_split import audit, validate_positions, load_inputs, run, sha256
from verify_ton_iot_audit import independent_counts, compare


class AuditTests(unittest.TestCase):
    def test_known_counts_and_conflicts(self):
        frame = pd.DataFrame({"x": ["a", "a", "b", "a", "a", "c", "c"]})
        labels = np.array(["normal", "normal", "attack", "attack", "normal", "attack", "attack"])
        train, test = np.array([0, 1, 2]), np.array([3, 4, 5, 6])
        summary, classes = audit(frame, labels, train, test)
        self.assertEqual(summary, {"train_rows": 3, "test_rows": 4,
            "train_duplicate_groups": 1, "train_involved_rows": 2, "train_excess_rows": 1,
            "test_duplicate_groups": 2, "test_involved_rows": 2 + 2, "test_excess_rows": 2,
            "shared_groups": 1, "exposed_test_rows": 2, "exposed_test_percent": 50.0,
            "conflicting_groups_all": 1, "conflicting_rows_all": 4, "shared_conflicting_groups": 1})
        self.assertEqual(sum(row["exposed_test_rows"] for row in classes), 2)
        self.assertAlmostEqual(classes[0]["exposed_test_percent"], 100 / 3)
        full, _ = audit(frame.assign(target=labels), labels, train, test)
        self.assertEqual(full["exposed_test_rows"], 1)
        self.assertEqual(full["conflicting_groups_all"], 0)

    def test_counts_are_rows_not_matching_pairs(self):
        summary, _ = audit(pd.DataFrame({"x": [1] * 5}), np.array(["a"] * 5),
                           np.array([0, 1, 2]), np.array([3, 4]))
        self.assertEqual(summary["exposed_test_rows"], 2)
        self.assertEqual(summary["shared_groups"], 1)
        self.assertEqual(summary["exposed_test_percent"], 100)

    def test_no_overlap(self):
        summary, _ = audit(pd.DataFrame({"x": [1, 2, 3, 4]}), np.array(["a"] * 4),
                           np.array([0, 1]), np.array([2, 3]))
        self.assertEqual(summary["exposed_test_rows"], 0)

    def test_missing_values_and_no_rounding(self):
        frame = pd.DataFrame({"x": [np.nan, 1.0, np.nan, 1.0000000001]})
        summary, _ = audit(frame, np.array(["a"] * 4), np.array([0, 1]), np.array([2, 3]))
        self.assertEqual(summary["exposed_test_rows"], 1)

    def test_all_missing_column(self):
        frame = pd.DataFrame({"x": [np.nan] * 4, "s": ["-", "NA", "-", " NA"]})
        summary, _ = audit(frame, np.array(["a"] * 4), np.array([0, 1]), np.array([2, 3]))
        self.assertEqual(summary["exposed_test_rows"], 1)

    def test_class_absent_from_test(self):
        _, classes = audit(pd.DataFrame({"x": [1, 2, 1]}), np.array(["a", "b", "a"]),
                           np.array([0, 1]), np.array([2]))
        self.assertIsNone(classes[1]["exposed_test_percent"])

    def test_invalid_partitions_rejected(self):
        for train, test in (([0, 1], [1, 2]), ([0], [2]), ([0, -1], [2]), ([], [0, 1, 2])):
            with self.subTest(train=train, test=test), self.assertRaises(ValueError):
                validate_positions(np.array(train, dtype=int), np.array(test, dtype=int), 3)
        with self.assertRaises(ValueError):
            validate_positions(np.array([0.0]), np.array([1.0]), 2)

    def test_random_small_frames_match_independent_verifier(self):
        rng = np.random.default_rng(42)
        for _ in range(20):
            frame = pd.DataFrame({"x": rng.choice([0.0, 1.0, np.nan], 30),
                                  "y": rng.choice(["-", "normal", "attack"], 30)})
            labels = rng.choice(["a", "b", "c"], 30)
            order = rng.permutation(30)
            actual, classes = audit(frame, labels, order[:20], order[20:])
            expected, other = independent_counts(frame, labels, order[:20], order[20:])
            compare(actual, expected, "synthetic")
            for a, b in zip(classes, other):
                compare(a, b, "synthetic/class")

    def test_wrong_dataset_hash_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "sample.csv").write_text("x\n1\n", encoding="utf-8")
            (path / "manifest.json").write_text(json.dumps({"dataset": {"sha256": "wrong"}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_inputs(path / "sample.csv", path)

    def test_changed_initial_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            dataset = path / "sample.csv"
            dataset.write_text("x\n1\n", encoding="utf-8")
            (path / "indices.csv").write_text("changed", encoding="utf-8")
            (path / "manifest.json").write_text(json.dumps({"dataset": {"sha256": sha256(dataset)},
                "artifacts_sha256": {"indices.csv": "wrong"}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifact changed"):
                load_inputs(dataset, path)

    def test_initial_directory_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve()
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run(path / "absent.csv", path, path)

    def test_missing_dataset_creates_no_results(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve()
            with self.assertRaisesRegex(ValueError, "Dataset not found"):
                run(path / "absent.csv", path / "initial", path / "output")
            self.assertFalse((path / "output").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

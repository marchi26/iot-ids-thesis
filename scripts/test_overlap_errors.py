"""Synthetic checks for the additional paired-error analysis; no training."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from explain_overlap_errors import analyze, class_metrics, compare, paired_transitions, validate_pair


def frame(predictions):
    return pd.DataFrame({"row_id": range(5), "group_id": [10, 10, 20, 30, 40],
                         "y_true": ["a"] * 5, "exposed_to_A": [True] * 5,
                         "y_pred": predictions})


class ErrorAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.a = frame(["a", "a", "b", "b", "b"])
        self.b = frame(["a", "b", "a", "b", "c"])
        self.labels = ["a", "b", "c"]

    def test_all_five_transitions(self):
        actual = paired_transitions(self.a, self.b)
        self.assertEqual(actual.transition.tolist(), ["correct_to_correct", "correct_to_wrong",
                         "wrong_to_correct", "wrong_to_same_wrong", "wrong_to_other_wrong"])

    def test_groups_not_rows_and_zero_categories(self):
        changes, totals, destinations = compare(self.a, self.b, self.labels, {})
        self.assertEqual((changes[0]["rows"], changes[0]["groups"]), (5, 4))
        self.assertEqual(sum(item["rows"] for item in totals), 5)
        self.assertEqual(len(totals), 15)
        self.assertEqual(destinations.rows.sum(), 5)
        self.assertEqual(sum(item["groups"] for item in totals if item["class"] == "a"), 5)

    def test_false_positives_count_other_true_classes(self):
        sample = self.a.copy()
        sample["y_true"] = ["a", "a", "b", "b", "c"]
        sample["y_pred"] = ["a", "b", "a", "b", "a"]
        actual = class_metrics(sample, self.labels)
        self.assertEqual(tuple(actual.loc["a", ["tp", "fp", "fn"]]), (1, 2, 1))
        self.assertAlmostEqual(actual.loc["a", "f1"], .4)

    def test_identical_predictions_have_zero_delta(self):
        changes, totals, _ = compare(self.a, self.a, self.labels, {})
        np.testing.assert_equal([row["delta_f1"] for row in changes], [0, 0, 0])
        self.assertEqual(sum(row["rows"] for row in totals if row["transition"] == "correct_to_wrong"), 0)

    def test_reordered_or_changed_identities_rejected(self):
        for column in ("row_id", "group_id", "y_true", "exposed_to_A"):
            changed = self.b.copy()
            changed.loc[4, column] = {"row_id": 99, "group_id": 99, "y_true": "b", "exposed_to_A": False}[column]
            with self.subTest(column=column), self.assertRaises(ValueError):
                validate_pair(self.a, changed, self.labels)
        with self.assertRaises(ValueError):
            validate_pair(self.a, self.b.iloc[::-1], self.labels)

    def test_duplicate_rows_and_unknown_labels_rejected(self):
        changed = self.b.copy()
        changed.loc[1, "row_id"] = 0
        with self.assertRaises(ValueError):
            validate_pair(self.a, changed, self.labels)
        changed = self.b.copy()
        changed.loc[1, "y_pred"] = "unknown"
        with self.assertRaises(ValueError):
            validate_pair(self.a, changed, self.labels)

    def test_conflicting_labels_keep_shared_group(self):
        sample = self.a.copy()
        sample.loc[1, "y_true"] = "b"
        validate_pair(sample, sample, self.labels)
        actual = class_metrics(sample, self.labels)
        self.assertEqual(actual.loc["a", "groups"], 4)
        self.assertEqual(actual.loc["b", "groups"], 1)
        self.assertEqual(sample.group_id.nunique(), 4)

    def test_output_protection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "already exists"):
                analyze(root / "pilot/results", root)
            with self.assertRaisesRegex(ValueError, "outside the pilot"):
                analyze(root / "pilot/results", root / "pilot/addition")


if __name__ == "__main__":
    unittest.main()

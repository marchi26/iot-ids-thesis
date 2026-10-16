"""Synthetic tests for SPLIT-02; no model fitting."""
import unittest

import numpy as np
import pandas as pd

from build_overlap_partitions import exact_groups, matched_control, remove_overlap, validate, group_split


class PartitionTests(unittest.TestCase):
    def test_equal_vectors_and_missing_values(self):
        groups = exact_groups(pd.DataFrame({"x": [1, 1, 2, 2], "y": [None, None, "a", "b"]}))
        self.assertEqual(groups[0], groups[1])
        self.assertEqual(len(set(groups)), 3)

    def test_overlap_removes_all_copies(self):
        retained, removed = remove_overlap(np.array([0, 1, 2]), np.array([3]), np.array([7, 7, 8, 7]))
        np.testing.assert_array_equal(retained, [2])
        np.testing.assert_array_equal(removed, [0, 1])

    def test_control_preserves_class_counts_and_seed(self):
        labels = np.array(["a"] * 5 + ["b"] * 5)
        train, removed = np.arange(10), np.array([0, 1, 5])
        retained, deleted = matched_control(train, removed, labels, 601)
        self.assertEqual(pd.Series(labels[deleted]).value_counts().to_dict(), {"a": 2, "b": 1})
        self.assertEqual(len(retained), 7)
        np.testing.assert_array_equal(deleted, matched_control(train, removed, labels, 601)[1])

    def test_group_leakage_rejected(self):
        parts = {"train": np.array([0]), "validation": np.array([1]), "test": np.array([2])}
        with self.assertRaises(ValueError):
            validate(np.arange(3), parts, np.array(["a"] * 3), np.array([0, 1, 0]), True)

    def test_duplicate_indices_rejected(self):
        parts = {"train": np.array([0]), "validation": np.array([0]), "test": np.array([2])}
        with self.assertRaises(ValueError):
            validate(np.arange(3), parts, np.array(["a"] * 3), np.arange(3))

    def test_missing_class_reported(self):
        parts = {"train": np.array([0]), "validation": np.array([1]), "test": np.array([2])}
        _, missing = validate(np.arange(3), parts, np.array(["a", "a", "b"]), np.arange(3), True)
        self.assertEqual(missing["train"], ["b"])

    def test_group_split_reproducible_and_disjoint(self):
        rows = np.arange(40)
        groups = rows // 2
        labels = np.array(["a", "b"] * 20)
        train, test = group_split(rows, labels, groups, 5, 101)
        self.assertFalse(set(groups[train]) & set(groups[test]))
        np.testing.assert_array_equal(test, group_split(rows, labels, groups, 5, 101)[1])
        self.assertEqual(sorted(np.concatenate([train, test])), list(rows))

    def test_conflicting_labels_do_not_change_group(self):
        frame = pd.DataFrame({"x": [1, 1, 2]})
        groups = exact_groups(frame)
        labels = np.array(["normal", "attack", "normal"])
        self.assertNotEqual(labels[0], labels[1])
        self.assertEqual(groups[0], groups[1])


if __name__ == "__main__":
    unittest.main()

"""Synthetic tests for SPLIT-02; no model fitting."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from build_overlap_partitions import exact_groups, matched_control, remove_overlap, validate, group_split
from verify_overlap_partitions import verify_source


class SourceHashTests(unittest.TestCase):
    def check_source(self, historical, checkout):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.py"
            path.write_bytes(checkout)
            expected = hashlib.sha256(historical).hexdigest()
            result = verify_source(path, expected)
            self.assertEqual(path.read_bytes(), checkout)
            self.assertEqual(result["historical_sha256"], expected)
            self.assertEqual(result["checkout_sha256"], hashlib.sha256(checkout).hexdigest())
            return result

    def test_exact_bytes(self):
        for data in (b"x = 1\n", b"x = 1\r\n", b"x = 1\r\ny = 2\n"):
            with self.subTest(data=data):
                self.assertEqual(self.check_source(data, data)["matched_variant"], "exact")

    def test_lf_checkout_matches_historical_crlf(self):
        self.assertEqual(self.check_source(b"x = 1\r\ny = 2\r\n", b"x = 1\ny = 2\n")
                         ["matched_variant"], "crlf")

    def test_crlf_checkout_matches_historical_lf(self):
        self.assertEqual(self.check_source(b"x = 1\ny = 2\n", b"x = 1\r\ny = 2\r\n")
                         ["matched_variant"], "lf")

    def test_mixed_checkout_matches_uniform_history(self):
        self.assertEqual(self.check_source(b"x = 1\ny = 2\n", b"x = 1\r\ny = 2\n")
                         ["matched_variant"], "lf")

    def test_real_edits_rejected_with_newline_conversion(self):
        for changed in (b"x = 2\n", b"x=1\n", b"x = 1 \n", b"x = 1\n# comment\n",
                        b"x = 1", b"x = 1\n\n", b"\xef\xbb\xbfx = 1\n", b"x = 1\r"):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "not only LF/CRLF"):
                self.check_source(b"x = 1\r\n", changed)

    def test_unmatched_historical_digest_rejected(self):
        # No historical mixed-newline layout is guessed from an unknown digest.
        with self.assertRaises(ValueError):
            self.check_source(b"x = 1\r\ny = 2\n", b"x = 1\ny = 2\n")

    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(FileNotFoundError):
            verify_source(Path(directory) / "missing.py", "0" * 64)


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

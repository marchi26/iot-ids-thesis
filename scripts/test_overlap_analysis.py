"""Check paired group-bootstrap calculations without classifier training."""
import unittest

import numpy as np

from analyze_overlap_pilot import bootstrap, group_confusions, percentile_interval, scores
from run_overlap_pilot import metrics_from_matrix


class AnalysisTests(unittest.TestCase):
    def test_vectorized_scores_match_scalar(self):
        matrices = np.array([[[7, 2, 1], [3, 9, 1], [0, 1, 3]], [[0, 0, 0], [0, 4, 1], [0, 0, 0]]])
        for matrix, actual in zip(matrices, scores(matrices, 0)):
            expected = metrics_from_matrix(matrix, 0)[0]
            np.testing.assert_allclose(actual, [expected[key] for key in ["macro_f1", "balanced_accuracy", "fpr", "fnr"]], equal_nan=True)

    def test_groups_keep_all_rows_and_conflicting_labels(self):
        truth = np.array([0, 1, 1])
        predictions = np.array([[0, 1, 0], [1, 1, 1]])
        matrix, groups = group_confusions(np.array([7, 7, 9]), truth, predictions, 2)
        np.testing.assert_array_equal(groups, [7, 9])
        weighted = (matrix.T @ np.array([2, 0])).reshape(2, 2, 2)
        np.testing.assert_array_equal(weighted[0], [[2, 0], [0, 2]])
        np.testing.assert_array_equal(weighted[1], [[0, 2], [0, 2]])

    def test_identical_models_have_zero_paired_difference(self):
        matrix, _ = group_confusions(np.array([1, 2, 3]), np.array([0, 1, 1]), np.array([[0, 0, 1], [0, 0, 1]]), 2)
        point, draws, missing = bootstrap(matrix, 2, 2, 0, np.random.default_rng(1301), replicates=80)
        np.testing.assert_allclose(draws[:, 0], draws[:, 1], equal_nan=True)
        np.testing.assert_allclose(point[0], point[1])
        self.assertGreater((missing > 0).sum(), 0)
        low, high, count = percentile_interval(draws[:, 0, 0] - draws[:, 1, 0], missing == 0)
        self.assertEqual((low, high), (0., 0.))
        self.assertEqual(count, int((missing == 0).sum()))

    def test_rng_reproducible(self):
        matrix, _ = group_confusions(np.array([0, 1, 2]), np.array([0, 1, 1]), np.array([[1, 1, 0]]), 2)
        first = bootstrap(matrix, 2, 1, 0, np.random.default_rng(1301), 20)
        second = bootstrap(matrix, 2, 1, 0, np.random.default_rng(1301), 20)
        for left, right in zip(first, second):
            np.testing.assert_allclose(left, right, equal_nan=True)

    def test_invalid_draws_not_replaced(self):
        low, high, count = percentile_interval(np.array([1., 999., np.nan]), np.array([True, False, True]))
        self.assertEqual((low, high, count), (1., 1., 1))
        low, high, count = percentile_interval(np.array([np.nan]), np.array([True]))
        self.assertTrue(np.isnan(low) and np.isnan(high))
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()

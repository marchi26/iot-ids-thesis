"""Synthetic checks for the approved pilot; no classifier training."""
import unittest

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score

from run_overlap_pilot import (CONFIGURATIONS, build_model, evaluation_tables, fit_plan,
                               make_preprocessor, metrics_from_matrix, rows_for_fit)


class PilotTests(unittest.TestCase):
    def test_exact_scope_and_fit_count(self):
        plan = fit_plan()
        self.assertEqual(len(plan), 28)
        self.assertEqual(len(set(plan)), 28)
        self.assertEqual(len(CONFIGURATIONS), 7)
        self.assertTrue(all(name.startswith("fixed_") for _, name, _ in plan))

    def test_parameters_frozen(self):
        lr, rf = build_model("logistic_regression"), build_model("random_forest")
        self.assertEqual((lr.C, lr.solver, lr.max_iter, lr.random_state), (1, "lbfgs", 3000, 1103))
        self.assertEqual((rf.n_estimators, rf.max_depth, rf.min_samples_leaf, rf.n_jobs, rf.random_state),
                         (200, None, 1, 1, 1103))
        self.assertIsNone(lr.class_weight)
        self.assertIsNone(rf.class_weight)
        with self.assertRaises(ValueError):
            build_model("lightgbm")

    def test_diagnostic_and_refit_rows(self):
        indices = pd.DataFrame({"configuration": ["fixed_A"] * 4,
                                "partition": ["train", "validation", "test", "removed"],
                                "position": [0] * 4, "row_id": [1, 2, 3, 4]})
        train, validation = rows_for_fit(indices, "fixed_A", "diagnostic")
        np.testing.assert_array_equal(train, [1])
        np.testing.assert_array_equal(validation, [2])
        pool, test = rows_for_fit(indices, "fixed_A", "refit")
        np.testing.assert_array_equal(pool, [1, 2])
        np.testing.assert_array_equal(test, [3])
        with self.assertRaises(ValueError):
            rows_for_fit(indices, "group_101", "refit")

    def test_transformer_training_only_and_unknown_category(self):
        processor = make_preprocessor(["value"], ["category"])
        processor.fit(pd.DataFrame({"value": [1., 3., np.nan], "category": ["a", "b", "a"]}))
        transformed = processor.transform(pd.DataFrame({"value": [999.], "category": ["unseen"]}))
        self.assertEqual(processor.named_transformers_["num"]["scaler"].mean_[0], 2.)
        self.assertEqual(list(processor.named_transformers_["cat"]["onehot"].categories_[0]), ["a", "b"])
        np.testing.assert_array_equal(transformed[:, 1:], [[0., 0.]])

    def test_dual_feature_role_preserved(self):
        processor = make_preprocessor(["code"], ["code"])
        transformed = processor.fit_transform(pd.DataFrame({"code": [1, 2, 1]}))
        self.assertEqual(transformed.shape, (3, 3))

    def test_metrics_against_sklearn(self):
        matrix = np.array([[4, 1, 2], [3, 5, 1], [1, 2, 6]])
        true, predicted = [], []
        for i in range(3):
            for j in range(3):
                true.extend([i] * matrix[i, j])
                predicted.extend([j] * matrix[i, j])
        metrics, _, _, _, _ = metrics_from_matrix(matrix, 0)
        self.assertAlmostEqual(metrics["accuracy"], accuracy_score(true, predicted))
        self.assertAlmostEqual(metrics["macro_f1"], f1_score(true, predicted, average="macro"))
        self.assertAlmostEqual(metrics["balanced_accuracy"], balanced_accuracy_score(true, predicted))
        self.assertAlmostEqual(metrics["fpr"], 3 / 7)
        self.assertAlmostEqual(metrics["fnr"], 4 / 18)

    def test_missing_class_and_undefined_rates(self):
        metrics, _, _, _, _ = metrics_from_matrix(np.array([[0, 0], [0, 3]]), 0)
        self.assertEqual(metrics["macro_f1"], .5)
        self.assertEqual(metrics["balanced_accuracy"], 1.)
        self.assertTrue(np.isnan(metrics["fpr"]))
        self.assertEqual(metrics["fnr"], 0.)

    def test_subgroups_stay_relative_to_A(self):
        predictions = pd.DataFrame({"row_id": [1, 2, 3], "group_id": [8, 9, 9],
                                    "y_true": ["normal", "attack", "attack"],
                                    "y_pred": ["attack", "attack", "normal"], "exposed_to_A": [False, True, True]})
        overall, per_class, matrices = evaluation_tables(predictions, ["attack", "normal"],
                                                        {"phase": "refit", "configuration": "fixed_B"})
        self.assertEqual([row["rows"] for row in overall], [3, 2, 1])
        self.assertEqual(len(per_class), 6)
        self.assertEqual(len(matrices), 12)


if __name__ == "__main__":
    unittest.main()

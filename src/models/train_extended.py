from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.preprocess import PreparedData
from src.models.evaluate import compute_classification_metrics, measure_inference_time, measure_training_time


def stratified_sample_arrays(
    X: np.ndarray,
    y: np.ndarray,
    max_samples: int | None,
    random_seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    if max_samples is None or max_samples <= 0 or len(y) <= max_samples:
        return X, y

    rng = np.random.default_rng(random_seed)
    selected_indices: list[int] = []
    classes, counts = np.unique(y, return_counts=True)

    for class_label, class_count in zip(classes, counts):
        class_indices = np.flatnonzero(y == class_label)
        class_quota = max(2, int(round(max_samples * (class_count / len(y)))))
        class_quota = min(class_quota, len(class_indices))
        selected_indices.extend(rng.choice(class_indices, size=class_quota, replace=False).tolist())

    if len(selected_indices) > max_samples:
        selected_indices = rng.choice(selected_indices, size=max_samples, replace=False).tolist()

    selected = np.array(sorted(selected_indices))
    return X[selected], y[selected]


def train_smote_comparison(
    original: PreparedData,
    balanced: PreparedData,
    mode: str,
    random_seed: int,
    max_train_samples: int | None = None,
) -> pd.DataFrame:
    from lightgbm import LGBMClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from xgboost import XGBClassifier

    def build_fast_models() -> dict[str, Any]:
        return {
            "random_forest": RandomForestClassifier(
                n_estimators=100,
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=random_seed,
            ),
            "lightgbm": LGBMClassifier(
                objective="binary" if mode == "binary" else "multiclass",
                n_estimators=100,
                learning_rate=0.05,
                num_leaves=31,
                class_weight="balanced",
                random_state=random_seed,
                n_jobs=-1,
                verbose=-1,
            ),
            "xgboost": XGBClassifier(
                objective="binary:logistic" if mode == "binary" else "multi:softprob",
                n_estimators=100,
                max_depth=4,
                learning_rate=0.08,
                eval_metric="logloss" if mode == "binary" else "mlogloss",
                tree_method="hist",
                n_jobs=-1,
                random_state=random_seed,
            ),
            "logistic_regression": LogisticRegression(
                max_iter=500,
                class_weight="balanced",
                random_state=random_seed,
            ),
        }

    rows: list[dict[str, Any]] = []
    for label, prepared in [("without_smote", original), ("with_smote", balanced)]:
        X_train, y_train = stratified_sample_arrays(prepared.X_train, prepared.y_train, max_train_samples, random_seed)
        for model_name, model in build_fast_models().items():
            trained_model, training_time = measure_training_time(lambda model=model: model.fit(X_train, y_train))
            y_pred, inference_time = measure_inference_time(trained_model, original.X_test)
            row = compute_classification_metrics(original.y_test, y_pred, model_name, mode, training_time, inference_time)
            row["balancing"] = label
            row["training_samples"] = len(y_train)
            row["test_samples"] = len(original.y_test)
            rows.append(row)
    return pd.DataFrame(rows)


def tune_models(
    prepared: PreparedData,
    mode: str,
    random_seed: int,
    max_train_samples: int | None = None,
    n_iter: int = 2,
    cv_folds: int = 2,
) -> pd.DataFrame:
    from lightgbm import LGBMClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import f1_score, make_scorer
    from sklearn.model_selection import RandomizedSearchCV
    from xgboost import XGBClassifier

    scoring = make_scorer(f1_score, average="macro", zero_division=0)
    X_tune, y_tune = stratified_sample_arrays(prepared.X_train, prepared.y_train, max_train_samples, random_seed)
    min_class_count = int(pd.Series(y_tune).value_counts().min())
    if min_class_count < 2:
        raise ValueError("Hyperparameter tuning requires at least two training samples in every class.")
    cv_folds = min(cv_folds, min_class_count)
    searches = {
        "random_forest": (
            RandomForestClassifier(class_weight="balanced_subsample", n_jobs=-1, random_state=random_seed),
            {"n_estimators": [50, 100], "max_depth": [None, 12], "min_samples_split": [2, 5]},
        ),
        "xgboost": (
            XGBClassifier(
                objective="binary:logistic" if mode == "binary" else "multi:softprob",
                eval_metric="logloss" if mode == "binary" else "mlogloss",
                tree_method="hist",
                n_jobs=-1,
                random_state=random_seed,
            ),
            {"n_estimators": [50, 100], "max_depth": [3, 5], "learning_rate": [0.05, 0.1], "subsample": [0.8, 1.0]},
        ),
        "lightgbm": (
            LGBMClassifier(
                objective="binary" if mode == "binary" else "multiclass",
                class_weight="balanced",
                n_jobs=-1,
                random_state=random_seed,
                verbose=-1,
            ),
            {"n_estimators": [50, 100], "num_leaves": [31, 64], "learning_rate": [0.05, 0.1]},
        ),
    }

    rows: list[dict[str, Any]] = []
    for model_name, (estimator, params) in searches.items():
        search = RandomizedSearchCV(
            estimator=estimator,
            param_distributions=params,
            n_iter=n_iter,
            scoring=scoring,
            cv=cv_folds,
            n_jobs=-1,
            random_state=random_seed,
        )
        tuned_model, training_time = measure_training_time(lambda search=search: search.fit(X_tune, y_tune))
        y_pred, inference_time = measure_inference_time(tuned_model.best_estimator_, prepared.X_test)
        row = compute_classification_metrics(
            prepared.y_test,
            y_pred,
            model_name,
            mode,
            training_time,
            inference_time,
        )
        row["best_params"] = str(tuned_model.best_params_)
        row["best_cv_macro_f1"] = tuned_model.best_score_
        row["training_samples"] = len(y_tune)
        row["test_samples"] = len(prepared.y_test)
        rows.append(row)
    return pd.DataFrame(rows)


def train_additional_models(
    prepared: PreparedData,
    mode: str,
    random_seed: int,
    max_train_samples: int | None = None,
) -> pd.DataFrame:
    from sklearn.ensemble import IsolationForest
    from sklearn.neural_network import MLPClassifier

    models: dict[str, Any] = {
        "mlp_classifier": MLPClassifier(
            hidden_layer_sizes=(64, 32),
            max_iter=150,
            random_state=random_seed,
            early_stopping=True,
        )
    }

    if mode == "binary":
        models["isolation_forest"] = IsolationForest(contamination="auto", random_state=random_seed, n_jobs=-1)

    rows: list[dict[str, Any]] = []
    X_train_sample, y_train_sample = stratified_sample_arrays(prepared.X_train, prepared.y_train, max_train_samples, random_seed)
    for model_name, model in models.items():
        if model_name == "isolation_forest":
            normal_class = 0
            X_train_normal = X_train_sample[y_train_sample == normal_class]
            if len(X_train_normal) == 0:
                raise ValueError("Isolation Forest requires at least one normal training sample with label 0.")
            trained_model, training_time = measure_training_time(lambda model=model: model.fit(X_train_normal))
            raw_pred, inference_time = measure_inference_time(trained_model, prepared.X_test)
            y_pred = np.where(raw_pred == -1, 1, 0)
        else:
            trained_model, training_time = measure_training_time(lambda model=model: model.fit(X_train_sample, y_train_sample))
            y_pred, inference_time = measure_inference_time(trained_model, prepared.X_test)

        row = compute_classification_metrics(
                prepared.y_test,
                y_pred,
                model_name,
                mode,
                training_time,
                inference_time,
            )
        row["training_samples"] = len(X_train_normal) if model_name == "isolation_forest" else len(y_train_sample)
        row["test_samples"] = len(prepared.y_test)
        rows.append(row)
    return pd.DataFrame(rows)

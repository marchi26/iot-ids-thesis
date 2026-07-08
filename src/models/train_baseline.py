from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

from src.data.preprocess import PreparedData
from src.models.evaluate import compute_classification_metrics, measure_inference_time, measure_training_time
from src.utils.paths import ensure_directory


def build_baseline_models(mode: str, random_seed: int) -> dict[str, Any]:
    from lightgbm import LGBMClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from xgboost import XGBClassifier

    objective = "binary:logistic" if mode == "binary" else "multi:softprob"
    lgbm_objective = "binary" if mode == "binary" else "multiclass"

    return {
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=random_seed,
        ),
        "lightgbm": LGBMClassifier(
            objective=lgbm_objective,
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=64,
            subsample=0.9,
            colsample_bytree=0.9,
            class_weight="balanced",
            random_state=random_seed,
            n_jobs=-1,
            verbose=-1,
        ),
        "xgboost": XGBClassifier(
            objective=objective,
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss" if mode == "binary" else "mlogloss",
            tree_method="hist",
            n_jobs=-1,
            random_state=random_seed,
        ),
        "logistic_regression": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            n_jobs=-1,
            random_state=random_seed,
        ),
    }


def train_and_evaluate_baseline(
    prepared: PreparedData,
    mode: str,
    random_seed: int,
    model_dir: Path,
    save_models: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ensure_directory(model_dir)
    metrics_rows: list[dict[str, Any]] = []
    predictions: dict[str, Any] = {}

    for model_name, model in build_baseline_models(mode, random_seed).items():
        trained_model, training_time = measure_training_time(lambda model=model: model.fit(prepared.X_train, prepared.y_train))
        y_pred, inference_time = measure_inference_time(trained_model, prepared.X_test)

        metrics_rows.append(
            compute_classification_metrics(
                prepared.y_test,
                y_pred,
                model_name,
                mode,
                training_time,
                inference_time,
            )
        )
        predictions[model_name] = {"model": trained_model, "y_pred": y_pred}

        if save_models:
            joblib.dump(trained_model, model_dir / f"{mode}_{model_name}.joblib")
            joblib.dump(prepared.preprocessor, model_dir / f"{mode}_{model_name}_preprocessor.joblib")

    return metrics_rows, predictions

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score

from src.utils.paths import ensure_directory


def measure_training_time(train_function: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter()
    result = train_function()
    return result, time.perf_counter() - start


def measure_inference_time(model: Any, X_test: np.ndarray) -> tuple[np.ndarray, float]:
    start = time.perf_counter()
    predictions = model.predict(X_test)
    return predictions, time.perf_counter() - start


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str,
    mode: str,
    training_time_seconds: float,
    inference_time_seconds: float,
) -> dict[str, Any]:
    average = "binary" if mode == "binary" else "weighted"
    matrix = confusion_matrix(y_true, y_pred).tolist()
    return {
        "model": model_name,
        "mode": mode,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, average=average, zero_division=0),
        "recall": recall_score(y_true, y_pred, average=average, zero_division=0),
        "f1_score": f1_score(y_true, y_pred, average=average, zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "confusion_matrix": matrix,
        "training_time_seconds": training_time_seconds,
        "inference_time_seconds": inference_time_seconds,
    }


def generate_classification_report(y_true: np.ndarray, y_pred: np.ndarray, class_names: list[str]) -> pd.DataFrame:
    labels = list(range(len(class_names)))
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    return pd.DataFrame(report).transpose()


def save_metrics_csv(metrics: list[dict[str, Any]], output_path: Path) -> None:
    ensure_directory(output_path.parent)
    pd.DataFrame(metrics).to_csv(output_path, index=False)


def save_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, output_path: Path, class_names: list[str]) -> None:
    ensure_directory(output_path.parent)
    matrix = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))
    pd.DataFrame(matrix, index=class_names, columns=class_names).to_csv(output_path)

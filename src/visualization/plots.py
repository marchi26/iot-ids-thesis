from __future__ import annotations

import os
from pathlib import Path

_MPLCONFIGDIR = Path(__file__).resolve().parents[2] / "results" / "logs" / "matplotlib"
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix

from src.utils.paths import ensure_directory


def _save_plot(output_path: Path) -> None:
    ensure_directory(output_path.parent)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_metric_bar(metrics: pd.DataFrame, metric: str, title: str, output_path: Path) -> None:
    if metrics.empty:
        raise ValueError(f"Cannot plot '{title}' because the metrics table is empty.")
    if metric not in metrics.columns:
        raise ValueError(f"Cannot plot '{title}' because metric column '{metric}' is missing.")
    ordered = metrics.sort_values(metric, ascending=False)
    plt.figure(figsize=(8, 5))
    plt.bar(ordered["model"], ordered[metric])
    plt.ylabel(metric.replace("_", " ").title())
    plt.xlabel("Model")
    plt.title(title)
    plt.xticks(rotation=25, ha="right")
    plt.ylim(0, 1)
    _save_plot(output_path)


def plot_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, class_names: list[str], title: str, output_path: Path) -> None:
    if not class_names:
        raise ValueError("Cannot plot confusion matrix without class names.")
    matrix = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))
    display = ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=class_names)
    fig_width = max(6, len(class_names) * 0.8)
    _, axis = plt.subplots(figsize=(fig_width, fig_width))
    display.plot(ax=axis, cmap="Blues", values_format="d", xticks_rotation=45)
    axis.set_title(title)
    _save_plot(output_path)


def plot_class_distribution(distribution: pd.Series, title: str, output_path: Path, class_names: list[str] | None = None) -> None:
    if distribution.empty:
        raise ValueError(f"Cannot plot '{title}' because the class distribution is empty.")
    labels = [class_names[index] if class_names and index < len(class_names) else str(index) for index in distribution.index]
    plt.figure(figsize=(8, 5))
    plt.bar(labels, distribution.values)
    plt.ylabel("Samples")
    plt.xlabel("Class")
    plt.title(title)
    plt.xticks(rotation=25, ha="right")
    _save_plot(output_path)


def plot_comparison(metrics: pd.DataFrame, value_column: str, group_column: str, title: str, output_path: Path) -> None:
    if metrics.empty:
        raise ValueError(f"Cannot plot '{title}' because the metrics table is empty.")
    missing_columns = [column for column in [value_column, group_column, "model"] if column not in metrics.columns]
    if missing_columns:
        raise ValueError(f"Cannot plot '{title}' because columns are missing: {missing_columns}.")
    pivot = metrics.pivot(index="model", columns=group_column, values=value_column)
    pivot.plot(kind="bar", figsize=(9, 5))
    plt.ylabel(value_column.replace("_", " ").title())
    plt.xlabel("Model")
    plt.title(title)
    plt.xticks(rotation=25, ha="right")
    plt.ylim(0, 1)
    _save_plot(output_path)

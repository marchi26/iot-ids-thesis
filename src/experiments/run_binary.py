from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.data.load_data import DatasetNotFoundError, DatasetValidationError
from src.data.preprocess import prepare_dataset
from src.models.evaluate import generate_classification_report, save_confusion_matrix, save_metrics_csv
from src.models.train_baseline import train_and_evaluate_baseline
from src.utils.logger import get_logger
from src.utils.paths import load_config, resolve_project_path


def run() -> pd.DataFrame:
    config = load_config()
    prepared = prepare_dataset(config, mode="binary", apply_smote=False)

    log_path = resolve_project_path(config["outputs"]["logs_dir"]) / "binary_baseline.log"
    logger = get_logger("binary_baseline", log_path)
    logger.info("Starting binary baseline experiment")

    metrics, predictions = train_and_evaluate_baseline(
        prepared,
        mode="binary",
        random_seed=int(config["experiment"]["random_seed"]),
        model_dir=resolve_project_path(config["outputs"]["models_dir"]),
        save_models=bool(config["outputs"].get("save_models", False)),
    )

    metrics_path = resolve_project_path(config["outputs"]["metrics_dir"]) / "binary_baseline_metrics.csv"
    save_metrics_csv(metrics, metrics_path)
    metrics_df = pd.DataFrame(metrics)

    from src.visualization.plots import plot_class_distribution, plot_confusion_matrix, plot_metric_bar

    plots_dir = resolve_project_path(config["outputs"]["plots_dir"])
    plot_metric_bar(metrics_df, "accuracy", "Binary Baseline Accuracy", plots_dir / "binary_baseline_accuracy.png")
    plot_metric_bar(metrics_df, "f1_score", "Binary Baseline F1-score", plots_dir / "binary_baseline_f1_score.png")
    plot_metric_bar(metrics_df, "macro_f1", "Binary Baseline Macro F1", plots_dir / "binary_baseline_macro_f1.png")
    plot_class_distribution(prepared.class_distribution_before, "Binary Class Distribution", plots_dir / "binary_class_distribution_before.png", prepared.class_names)
    plot_class_distribution(prepared.class_distribution_after, "Binary Training Distribution", plots_dir / "binary_class_distribution_after.png", prepared.class_names)

    for model_name, payload in predictions.items():
        save_confusion_matrix(
            prepared.y_test,
            payload["y_pred"],
            resolve_project_path(config["outputs"]["metrics_dir"]) / f"binary_{model_name}_confusion_matrix.csv",
            prepared.class_names,
        )
        report = generate_classification_report(prepared.y_test, payload["y_pred"], prepared.class_names)
        report.to_csv(resolve_project_path(config["outputs"]["metrics_dir"]) / f"binary_{model_name}_classification_report.csv")
        plot_confusion_matrix(
            prepared.y_test,
            payload["y_pred"],
            prepared.class_names,
            f"Binary Confusion Matrix - {model_name}",
            plots_dir / f"binary_{model_name}_confusion_matrix.png",
        )

    logger.info("Binary baseline completed. Metrics saved to %s", metrics_path)
    return metrics_df


if __name__ == "__main__":
    try:
        run()
    except (DatasetNotFoundError, DatasetValidationError) as exc:
        print(exc)
        raise SystemExit(1)

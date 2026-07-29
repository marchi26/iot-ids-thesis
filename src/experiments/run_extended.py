from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.data.load_data import DatasetNotFoundError, DatasetValidationError
from src.data.preprocess import prepare_dataset
from src.models.train_extended import train_additional_models, train_smote_comparison, tune_models
from src.utils.logger import get_logger
from src.utils.paths import ensure_directory, load_config, resolve_project_path


def run() -> dict[str, pd.DataFrame]:
    config = load_config()
    metrics_dir = resolve_project_path(config["outputs"]["metrics_dir"])
    plots_dir = resolve_project_path(config["outputs"]["plots_dir"])
    ensure_directory(metrics_dir)
    ensure_directory(plots_dir)
    random_seed = int(config["experiment"]["random_seed"])
    extended_config = config.get("extended", {})
    max_train_samples = extended_config.get("max_train_samples")
    tuning_max_train_samples = extended_config.get("tuning_max_train_samples")
    tuning_n_iter = int(extended_config.get("tuning_n_iter", 2))
    tuning_cv_folds = int(extended_config.get("tuning_cv_folds", 2))

    outputs: dict[str, pd.DataFrame] = {}
    for mode in ["binary", "multiclass"]:
        original = prepare_dataset(config, mode=mode, apply_smote=False)
        balanced = prepare_dataset(config, mode=mode, apply_smote=True)

        if "logger" not in locals():
            logger = get_logger("extended_experiments", resolve_project_path(config["outputs"]["logs_dir"]) / "extended.log")
            from src.visualization.plots import plot_comparison, plot_metric_bar

        logger.info("Starting extended experiments for %s classification", mode)

        smote_df = train_smote_comparison(
            original,
            balanced,
            mode,
            random_seed,
            max_train_samples=max_train_samples,
        )
        if mode == "binary":
            smote_df.to_csv(metrics_dir / "smote_comparison.csv", index=False)
            plot_comparison(smote_df, "macro_f1", "balancing", "SMOTE Macro F1 Comparison", plots_dir / "smote_macro_f1_comparison.png")

        tuning_df = tune_models(
            original,
            mode,
            random_seed,
            max_train_samples=tuning_max_train_samples,
            n_iter=tuning_n_iter,
            cv_folds=tuning_cv_folds,
        )
        if mode == "binary":
            tuning_df.to_csv(metrics_dir / "hyperparameter_tuning_results.csv", index=False)
            plot_metric_bar(tuning_df, "macro_f1", "Binary Tuned Models Macro F1", plots_dir / "binary_tuning_macro_f1.png")

        additional_df = train_additional_models(
            original,
            mode,
            random_seed,
            max_train_samples=max_train_samples,
        )
        extended_df = pd.concat(
            [
                smote_df.assign(extension="smote_comparison"),
                tuning_df.assign(extension="hyperparameter_tuning"),
                additional_df.assign(extension="additional_model"),
            ],
            ignore_index=True,
        )
        output_path = metrics_dir / f"{mode}_extended_metrics.csv"
        extended_df.to_csv(output_path, index=False)
        plot_metric_bar(extended_df, "macro_f1", f"{mode.title()} Extended Macro F1", plots_dir / f"{mode}_extended_macro_f1.png")
        outputs[mode] = extended_df
        logger.info("%s extended metrics saved to %s", mode.title(), output_path)

    return outputs


if __name__ == "__main__":
    try:
        run()
    except (DatasetNotFoundError, DatasetValidationError) as exc:
        print(exc)
        raise SystemExit(1)

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.utils.paths import ensure_directory, load_config, resolve_project_path


EXCLUDED_REPORT_ROWS = {"accuracy", "macro avg", "weighted avg"}


def collect_per_class_reports(metrics_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(metrics_dir.glob("*_classification_report.csv")):
        name = path.stem.removesuffix("_classification_report")
        mode = "binary" if name.startswith("binary_") else "multiclass"
        model = name.removeprefix("binary_").removeprefix("multiclass_")
        report = pd.read_csv(path, index_col=0)
        for class_name, values in report.iterrows():
            if str(class_name) in EXCLUDED_REPORT_ROWS:
                continue
            rows.append(
                {
                    "mode": mode,
                    "model": model,
                    "class": class_name,
                    "precision": values.get("precision"),
                    "recall": values.get("recall"),
                    "f1_score": values.get("f1-score"),
                    "support": values.get("support"),
                }
            )
    return pd.DataFrame(rows)


def collect_latency_summaries(metrics_dir: Path) -> pd.DataFrame:
    metric_files = [
        "binary_baseline_metrics.csv",
        "multiclass_baseline_metrics.csv",
        "binary_extended_metrics.csv",
        "multiclass_extended_metrics.csv",
        "smote_comparison.csv",
        "hyperparameter_tuning_results.csv",
        "deployment_analysis.csv",
        "embedded_logistic_regression_metrics.csv",
    ]
    rows: list[pd.DataFrame] = []
    for filename in metric_files:
        path = metrics_dir / filename
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        if "inference_time_seconds" not in frame.columns:
            continue
        frame = frame.copy()
        frame["source_file"] = filename
        frame["inference_time_ms"] = frame["inference_time_seconds"] * 1000
        rows.append(frame)
    if not rows:
        return pd.DataFrame()
    columns = [
        "source_file",
        "mode",
        "model",
        "accuracy",
        "macro_f1",
        "weighted_f1",
        "training_time_seconds",
        "inference_time_seconds",
        "inference_time_ms",
    ]
    combined = pd.concat(rows, ignore_index=True)
    return combined[[column for column in columns if column in combined.columns]]


def collect_tuning_results(metrics_dir: Path) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for filename in ["binary_extended_metrics.csv", "multiclass_extended_metrics.csv"]:
        path = metrics_dir / filename
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        if "extension" not in frame.columns:
            continue
        tuning = frame[frame["extension"] == "hyperparameter_tuning"].copy()
        if not tuning.empty:
            tuning["source_file"] = filename
            rows.append(tuning)
    if not rows:
        existing = metrics_dir / "hyperparameter_tuning_results.csv"
        return pd.read_csv(existing) if existing.exists() else pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def write_experiment_summary(metrics_dir: Path, outputs: dict[str, Path]) -> Path:
    summary_path = metrics_dir / "experiment_summary.txt"
    metric_files = sorted(path for path in metrics_dir.glob("*.csv") if path.name != ".gitkeep")
    plot_dir = metrics_dir.parent / "plots"
    plot_files = sorted(plot_dir.glob("*.png")) if plot_dir.exists() else []
    with summary_path.open("w", encoding="utf-8") as stream:
        stream.write("Executed experiments and generated outputs\n")
        stream.write(f"Metric CSV files: {len(metric_files)}\n")
        stream.write(f"Plot PNG files: {len(plot_files)}\n")
        stream.write("Generated summaries:\n")
        for name, path in outputs.items():
            stream.write(f"- {name}: {path.name}\n")
    return summary_path


def run() -> dict[str, Path]:
    config = load_config()
    metrics_dir = resolve_project_path(config["outputs"]["metrics_dir"])
    ensure_directory(metrics_dir)

    outputs: dict[str, Path] = {}
    per_class = collect_per_class_reports(metrics_dir)
    if not per_class.empty:
        output_path = metrics_dir / "per_class_summary.csv"
        per_class.to_csv(output_path, index=False)
        outputs["per_class_summary"] = output_path

    latency = collect_latency_summaries(metrics_dir)
    if not latency.empty:
        output_path = metrics_dir / "latency_summary.csv"
        latency.to_csv(output_path, index=False)
        outputs["latency_summary"] = output_path

    tuning = collect_tuning_results(metrics_dir)
    if not tuning.empty:
        output_path = metrics_dir / "hyperparameter_tuning_results.csv"
        tuning.to_csv(output_path, index=False)
        outputs["hyperparameter_tuning_results"] = output_path

    if not outputs:
        raise RuntimeError("No existing metric files were found. Run the experiments before generating summaries.")
    outputs["experiment_summary"] = write_experiment_summary(metrics_dir, outputs)
    return outputs


if __name__ == "__main__":
    created = run()
    for name, path in created.items():
        print(f"{name}: {path}")

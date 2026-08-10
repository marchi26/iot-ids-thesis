from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.data.load_data import DatasetNotFoundError, DatasetValidationError
from src.data.preprocess import PreparedData, prepare_dataset
from src.models.evaluate import compute_classification_metrics, measure_inference_time, measure_training_time
from src.models.train_baseline import build_baseline_models
from src.models.train_extended import stratified_sample_arrays
from src.utils.paths import ensure_directory, load_config, resolve_project_path


def select_best_baseline_model(metrics_dir: Path, mode: str) -> str:
    path = metrics_dir / f"{mode}_baseline_metrics.csv"
    if not path.exists():
        return "lightgbm"
    metrics = pd.read_csv(path)
    if metrics.empty or "macro_f1" not in metrics.columns:
        return "lightgbm"
    return str(metrics.sort_values("macro_f1", ascending=False).iloc[0]["model"])


def dump_and_measure(payload: Any, output_path: Path, compress: int | tuple[str, int] = 0) -> tuple[float, float]:
    ensure_directory(output_path.parent)
    start = time.perf_counter()
    joblib.dump(payload, output_path, compress=compress)
    elapsed = time.perf_counter() - start
    size_mb = output_path.stat().st_size / (1024 * 1024)
    return size_mb, elapsed


def train_selected_model(prepared: PreparedData, mode: str, model_name: str, random_seed: int, max_train_samples: int | None) -> tuple[Any, float]:
    models = build_baseline_models(mode, random_seed)
    if model_name not in models:
        model_name = "lightgbm"
    X_train, y_train = stratified_sample_arrays(prepared.X_train, prepared.y_train, max_train_samples, random_seed)
    return measure_training_time(lambda: models[model_name].fit(X_train, y_train))


def analyze_mode(config: dict[str, Any], mode: str) -> dict[str, Any]:
    random_seed = int(config["experiment"]["random_seed"])
    metrics_dir = resolve_project_path(config["outputs"]["metrics_dir"])
    models_dir = resolve_project_path(config["outputs"]["models_dir"])
    deployment_config = config.get("deployment", {})
    max_train_samples = deployment_config.get("max_train_samples")
    compression_level = int(deployment_config.get("compression_level", 3))

    prepared = prepare_dataset(config, mode=mode, apply_smote=False)
    model_name = select_best_baseline_model(metrics_dir, mode)
    model, training_time = train_selected_model(prepared, mode, model_name, random_seed, max_train_samples)
    y_pred, inference_time = measure_inference_time(model, prepared.X_test)

    payload = {
        "mode": mode,
        "model_name": model_name,
        "model": model,
        "preprocessor": prepared.preprocessor,
        "feature_names": prepared.feature_names,
        "class_names": prepared.class_names,
    }
    base_path = models_dir / f"{mode}_{model_name}_deployment.joblib"
    compressed_path = models_dir / f"{mode}_{model_name}_deployment_compressed.joblib"
    model_size_mb, dump_time = dump_and_measure(payload, base_path, compress=0)
    compressed_size_mb, compressed_dump_time = dump_and_measure(payload, compressed_path, compress=compression_level)

    loaded_model_start = time.perf_counter()
    loaded_payload = joblib.load(compressed_path)
    load_time = time.perf_counter() - loaded_model_start
    _, compressed_inference_time = measure_inference_time(loaded_payload["model"], prepared.X_test)

    row = compute_classification_metrics(prepared.y_test, y_pred, model_name, mode, training_time, inference_time)
    row.update(
        {
            "artifact_path": base_path.as_posix(),
            "compressed_artifact_path": compressed_path.as_posix(),
            "model_size_mb": model_size_mb,
            "compressed_model_size_mb": compressed_size_mb,
            "compression_ratio": compressed_size_mb / model_size_mb if model_size_mb else None,
            "dump_time_seconds": dump_time,
            "compressed_dump_time_seconds": compressed_dump_time,
            "compressed_load_time_seconds": load_time,
            "compressed_inference_time_seconds": compressed_inference_time,
            "test_samples": len(prepared.y_test),
            "inference_ms_per_1000_samples": (inference_time / len(prepared.y_test)) * 1000 * 1000,
            "compressed_inference_ms_per_1000_samples": (compressed_inference_time / len(prepared.y_test)) * 1000 * 1000,
        }
    )
    return row


def run() -> pd.DataFrame:
    config = load_config()
    metrics_dir = ensure_directory(resolve_project_path(config["outputs"]["metrics_dir"]))
    rows = [analyze_mode(config, mode) for mode in ["binary", "multiclass"]]
    output = pd.DataFrame(rows)
    output_path = metrics_dir / "deployment_analysis.csv"
    output.to_csv(output_path, index=False)
    print(f"Deployment analysis saved to {output_path}")
    return output


if __name__ == "__main__":
    try:
        run()
    except (DatasetNotFoundError, DatasetValidationError) as exc:
        print(exc)
        raise SystemExit(1)

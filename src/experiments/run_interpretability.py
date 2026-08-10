from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_MPLCONFIGDIR = Path(__file__).resolve().parents[2] / "results" / "logs" / "matplotlib"
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.data.load_data import DatasetNotFoundError, DatasetValidationError
from src.data.preprocess import PreparedData, prepare_dataset
from src.models.train_baseline import build_baseline_models
from src.models.train_extended import stratified_sample_arrays
from src.utils.paths import ensure_directory, load_config, resolve_project_path


SUPPORTED_TREE_MODELS = {"random_forest", "lightgbm", "xgboost"}


def select_best_tree_model(metrics_dir: Path, mode: str) -> str:
    path = metrics_dir / f"{mode}_baseline_metrics.csv"
    if not path.exists():
        return "lightgbm"
    metrics = pd.read_csv(path)
    metrics = metrics[metrics["model"].isin(SUPPORTED_TREE_MODELS)]
    if metrics.empty:
        return "lightgbm"
    return str(metrics.sort_values("macro_f1", ascending=False).iloc[0]["model"])


def sample_rows(X: np.ndarray, max_rows: int, random_seed: int) -> np.ndarray:
    if len(X) <= max_rows:
        return X
    rng = np.random.default_rng(random_seed)
    indices = rng.choice(np.arange(len(X)), size=max_rows, replace=False)
    return X[np.sort(indices)]


def mean_abs_shap_values(shap_values: Any) -> np.ndarray:
    values = shap_values.values if hasattr(shap_values, "values") else shap_values
    if isinstance(values, list):
        arrays = [np.asarray(value) for value in values]
        if len(arrays) == 2:
            return np.mean(np.abs(arrays[1]), axis=0)
        return np.mean(np.mean(np.abs(np.stack(arrays, axis=0)), axis=0), axis=0)
    array = np.asarray(values)
    if array.ndim == 3:
        return np.mean(np.abs(array), axis=(0, 2))
    if array.ndim == 2:
        return np.mean(np.abs(array), axis=0)
    raise ValueError(f"Unsupported SHAP value shape: {array.shape}")


def plot_top_features(frame: pd.DataFrame, title: str, output_path: Path) -> None:
    ensure_directory(output_path.parent)
    ordered = frame.sort_values("mean_abs_shap", ascending=True)
    plt.figure(figsize=(9, 7))
    plt.barh(ordered["feature"], ordered["mean_abs_shap"])
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close()


def tree_feature_importance(model: Any) -> np.ndarray:
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
        total = values.sum()
        return values / total if total else values
    raise RuntimeError("The selected model does not expose tree feature importances.")


def explain_mode(config: dict[str, Any], mode: str) -> pd.DataFrame:
    random_seed = int(config["experiment"]["random_seed"])
    interpretation_config = config.get("interpretability", {})
    max_train_samples = interpretation_config.get("max_train_samples")
    shap_sample_size = int(interpretation_config.get("shap_sample_size", 1000))
    top_features = int(interpretation_config.get("top_features", 25))

    metrics_dir = resolve_project_path(config["outputs"]["metrics_dir"])
    plots_dir = resolve_project_path(config["outputs"]["plots_dir"])
    prepared: PreparedData = prepare_dataset(config, mode=mode, apply_smote=False)
    model_name = select_best_tree_model(metrics_dir, mode)
    model = build_baseline_models(mode, random_seed)[model_name]
    X_train, y_train = stratified_sample_arrays(prepared.X_train, prepared.y_train, max_train_samples, random_seed)
    model.fit(X_train, y_train)

    X_explain = sample_rows(prepared.X_test, shap_sample_size, random_seed)
    try:
        import shap

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_explain)
        importance = mean_abs_shap_values(shap_values)
        importance_metric = "mean_abs_shap"
        method = "shap"
    except ImportError:
        importance = tree_feature_importance(model)
        importance_metric = "normalized_feature_importance"
        method = "model_feature_importance"

    frame = pd.DataFrame({"feature": prepared.feature_names, importance_metric: importance})
    frame["interpretability_method"] = method
    if importance_metric != "mean_abs_shap":
        frame["mean_abs_shap"] = np.nan
    if importance_metric != "normalized_feature_importance":
        frame["normalized_feature_importance"] = np.nan
    frame = frame.sort_values("mean_abs_shap", ascending=False).head(top_features)
    if method != "shap":
        frame = frame.sort_values("normalized_feature_importance", ascending=False).head(top_features)
    frame.insert(0, "mode", mode)
    frame.insert(1, "model", model_name)

    output_path = metrics_dir / f"{mode}_interpretability_feature_importance.csv"
    ensure_directory(output_path.parent)
    frame.to_csv(output_path, index=False)
    plot_column = "mean_abs_shap" if method == "shap" else "normalized_feature_importance"
    plot_frame = frame[["feature", plot_column]].rename(columns={plot_column: "mean_abs_shap"})
    plot_top_features(
        plot_frame,
        f"{mode.title()} Feature Importance - {model_name}",
        plots_dir / f"{mode}_interpretability_feature_importance.png",
    )
    return frame


def run() -> pd.DataFrame:
    config = load_config()
    frames = [explain_mode(config, mode) for mode in ["binary", "multiclass"]]
    combined = pd.concat(frames, ignore_index=True)
    output_path = resolve_project_path(config["outputs"]["metrics_dir"]) / "interpretability_feature_importance.csv"
    combined.to_csv(output_path, index=False)
    print(f"Interpretability feature importance saved to {output_path}")
    return combined


if __name__ == "__main__":
    try:
        run()
    except (DatasetNotFoundError, DatasetValidationError, RuntimeError) as exc:
        print(exc)
        raise SystemExit(1)

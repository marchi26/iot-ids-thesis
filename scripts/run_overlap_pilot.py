"""Run only the approved 28-fit fixed-test SPLIT-02 pilot; no tuning."""
from __future__ import annotations

import argparse
import contextlib
import gc
import hashlib
import io
import json
import os
import platform
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_info, threadpool_limits

from audit_ton_iot_split import INITIAL, ROOT, git, load_inputs, require, sha256
from build_overlap_partitions import exact_groups, save_csv
from verify_overlap_partitions import verify

PARTITIONS = ROOT / "research/ton_iot_overlap_impact/results"
OUTPUT = ROOT / "research/ton_iot_overlap_impact/pilot/results"
CONFIGURATIONS = ["fixed_A", "fixed_B"] + [f"fixed_C_{seed}" for seed in (601, 701, 809, 907, 1009)]
MODEL_NAMES = ["logistic_regression", "random_forest"]
MODEL_SEED = 1103
PHASES = ["diagnostic", "refit"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n",
                         encoding="utf-8", newline="\n")
    temporary.replace(path)


def build_model(name):
    if name == "logistic_regression":
        return LogisticRegression(C=1, solver="lbfgs", max_iter=3000, random_state=MODEL_SEED)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=200, max_depth=None, min_samples_leaf=1,
                                      n_jobs=1, random_state=MODEL_SEED)
    raise ValueError(f"Model outside the approved pilot: {name}")


def make_preprocessor(numeric, categorical):
    return ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")),
                          ("scaler", StandardScaler())]), numeric),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), categorical),
    ], remainder="drop")


def fit_plan():
    return [(phase, configuration, model) for phase in PHASES
            for configuration in CONFIGURATIONS for model in MODEL_NAMES]


def rows_for_fit(indices, configuration, phase):
    require(configuration in CONFIGURATIONS and phase in PHASES, "Fit outside approved scope")
    block = indices[indices.configuration == configuration]
    parts = {name: values.sort_values("position").row_id.to_numpy(dtype=np.int64)
             for name, values in block.groupby("partition")}
    train = parts["train"] if phase == "diagnostic" else np.concatenate([parts["train"], parts["validation"]])
    evaluation = parts["validation"] if phase == "diagnostic" else parts["test"]
    require(not set(train) & set(evaluation), "Fit/evaluation row overlap")
    return train, evaluation


def metrics_from_matrix(matrix, normal_index):
    """Fixed-label macro F1; balanced accuracy averages only supported classes."""
    matrix = np.asarray(matrix, dtype=float)
    support, predicted = matrix.sum(axis=1), matrix.sum(axis=0)
    tp = np.diag(matrix)
    recall = np.divide(tp, support, out=np.zeros_like(tp), where=support != 0)
    precision = np.divide(tp, predicted, out=np.zeros_like(tp), where=predicted != 0)
    f1 = np.divide(2 * tp, support + predicted, out=np.zeros_like(tp), where=(support + predicted) != 0)
    total = support.sum()
    normal = support[normal_index]
    attacks = total - normal
    metrics = {
        "accuracy": tp.sum() / total if total else np.nan,
        "macro_f1": f1.mean(),
        "weighted_f1": np.dot(f1, support) / total if total else np.nan,
        "balanced_accuracy": recall[support > 0].mean() if total else np.nan,
        "macro_precision": precision.mean(),
        "fpr": (normal - tp[normal_index]) / normal if normal else np.nan,
        "fnr": (predicted[normal_index] - tp[normal_index]) / attacks if attacks else np.nan,
    }
    return metrics, precision, recall, f1, support


def evaluation_tables(predictions, classes, metadata):
    mapping = {name: i for i, name in enumerate(classes)}
    require(set(predictions.y_true) <= set(classes) and set(predictions.y_pred) <= set(classes), "Unknown prediction label")
    masks = {"all": np.ones(len(predictions), dtype=bool)}
    if metadata["phase"] == "refit":
        exposed = predictions.exposed_to_A.to_numpy(dtype=bool)
        masks.update({"exposed": exposed, "non_exposed": ~exposed})
    overall, per_class, matrices = [], [], []
    for subgroup, mask in masks.items():
        selected = predictions.loc[mask]
        matrix = confusion_matrix(selected.y_true, selected.y_pred, labels=classes)
        metrics, precision, recall, f1, support = metrics_from_matrix(matrix, mapping["normal"])
        info = {**metadata, "subgroup": subgroup}
        overall.append({**info, "rows": len(selected), "groups": selected.group_id.nunique(), **metrics})
        for i, label in enumerate(classes):
            per_class.append({**info, "class": label, "precision": precision[i], "recall": recall[i],
                              "f1": f1[i], "support": int(support[i]), "predicted_support": int(matrix[:, i].sum())})
            for j, prediction in enumerate(classes):
                matrices.append({**info, "true_class": label, "predicted_class": prediction, "count": int(matrix[i, j])})
    return overall, per_class, matrices


def summarize(output, classes):
    overall, per_class, matrices, timings, warning_rows = [], [], [], [], []
    for phase, configuration, model in fit_plan():
        directory = output / "fits" / f"{phase}__{configuration}__{model}"
        if not (directory / "fit.json").exists():
            continue
        fit = json.loads((directory / "fit.json").read_text())
        prediction_path = directory / "predictions.csv.gz"
        require(sha256(prediction_path) == fit["predictions_sha256"], "Saved predictions changed")
        predictions = pd.read_csv(prediction_path)
        metadata = {"phase": phase, "configuration": configuration, "model": model}
        a, b, c = evaluation_tables(predictions, classes, metadata)
        overall.extend(a)
        per_class.extend(b)
        matrices.extend(c)
        timings.append({**metadata, **fit["timings"], "train_rows": fit["train_rows"],
                        "evaluation_rows": fit["evaluation_rows"], "encoded_features": fit["encoded_features"],
                        "convergence_warning": fit["convergence_warning"], "iterations": max(fit["iterations"], default=0)})
        warning_rows.extend({**metadata, **item} for item in fit["warnings"])
    for name, values in (("metrics.csv", overall), ("per_class_metrics.csv", per_class),
                         ("confusion_matrices.csv", matrices), ("timings.csv", timings)):
        if values:
            save_csv(pd.DataFrame(values), output / name)
    save_csv(pd.DataFrame(warning_rows, columns=["phase", "configuration", "model", "category", "message"]), output / "warnings.csv")


def run(output):
    require(not output.exists(), f"Output already exists; refusing to overwrite: {output}")
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        preflight = verify(PARTITIONS)
    frame, initial, tasks = load_inputs(ROOT / "data/raw/train_test_network.csv", INITIAL)
    membership = pd.read_csv(PARTITIONS / "row_groups.csv.gz")
    indices = pd.read_csv(PARTITIONS / "partition_indices.csv.gz")
    labels = tasks["multiclass"]["labels"]
    classes = initial["tasks"]["multiclass"]["class_names"]
    columns = pd.read_csv(PARTITIONS / "feature_columns.csv")["column"].tolist()
    roles = pd.read_csv(INITIAL / "feature_columns.csv")
    roles = roles[roles.task == "multiclass"]
    numeric = roles[roles.branch == "numeric"].sort_values("position")["column"].tolist()
    categorical = roles[roles.branch == "categorical"].sort_values("position")["column"].tolist()
    require(columns == tasks["multiclass"]["paths"]["B_baseline"] and len(columns) == 32, "Feature contract changed")
    require(set(numeric) | set(categorical) == set(columns), "Frozen feature roles mismatch")
    require(np.array_equal(membership.row_id, np.arange(len(frame))) and np.array_equal(membership["class"], labels),
            "Membership does not match frozen input")
    require(np.array_equal(exact_groups(frame[columns]), membership.group_id), "Feature group assignments changed")
    exposure = pd.read_csv(PARTITIONS / "fixed_test_subgroups.csv.gz")
    fixed_test = tasks["multiclass"]["positions"]["test"]
    require(np.array_equal(exposure.row_id, fixed_test), "Exposure/test order changed")
    original_pool = tasks["multiclass"]["positions"]["train"]
    expected_exposure = membership.loc[fixed_test, "group_id"].isin(membership.loc[original_pool, "group_id"])
    require(np.array_equal(exposure.exposed_to_A, expected_exposure), "Exposure labels changed")
    for configuration in CONFIGURATIONS:
        _, test = rows_for_fit(indices, configuration, "refit")
        require(np.array_equal(test, fixed_test), "Fixed test is not identical")
    a_pool, _ = rows_for_fit(indices, "fixed_A", "refit")
    require(np.array_equal(np.sort(a_pool), np.sort(original_pool)), "Original pool changed")
    X = frame[columns]
    mapping = {name: index for index, name in enumerate(classes)}
    y = np.array([mapping[label] for label in labels], dtype=np.int64)
    status_at_start = git("status", "--porcelain=v1", "--untracked-files=all")
    output.mkdir(parents=True)
    sources = [Path(__file__), ROOT / "scripts/test_overlap_pilot.py", ROOT / "scripts/build_overlap_partitions.py",
               ROOT / "scripts/verify_overlap_partitions.py", ROOT / "scripts/audit_ton_iot_split.py",
               ROOT / "src/data/preprocess.py", ROOT / "src/utils/paths.py", ROOT / "config/config.yaml"]
    manifest = {"stage": "SPLIT-02 approved fixed-test pilot", "status": "running", "started_at_utc": utc_now(),
                "execution_commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
                "working_tree_status_at_start": status_at_start, "dataset": initial["dataset"],
                "python": platform.python_version(), "platform": platform.platform(), "logical_cpus": os.cpu_count(),
                "packages": initial["packages"], "classes": classes,
                "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
                "partition_manifest_sha256": sha256(PARTITIONS / "manifest.json"),
                "protocol_sha256": sha256(ROOT / "research/ton_iot_overlap_impact/protocol.md"),
                "feature_roles": {"numeric": numeric, "categorical": categorical, "source_unique": columns},
                "models": {name: build_model(name).get_params() for name in MODEL_NAMES},
                "native_threads": 1, "planned_fits": 28, "completed_fits": 0,
                "configurations": CONFIGURATIONS, "phases": PHASES,
                "approval_scope": "Fixed-test A/B/five C controls only; no random/group fits, tuning or SMOTE",
                "warning_policy": "Record convergence warnings; continue unchanged. Stop on exceptions; no automatic retries."}
    write_json(output / "manifest.json", manifest)
    write_json(output / "preflight.json", preflight)

    def event(kind, **values):
        record = {"time_utc": utc_now(), "event": kind, **values}
        with (output / "events.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=True) + "\n")
        print(json.dumps(record), flush=True)

    try:
        with threadpool_limits(limits=1):
            manifest["threadpools"] = threadpool_info()
            for phase, configuration, name in fit_plan():
                train, evaluation = rows_for_fit(indices, configuration, phase)
                require(set(y[train]) == set(range(len(classes))), "Training class missing; stop for review")
                event("fit_started", phase=phase, configuration=configuration, model=name,
                      train_rows=len(train), evaluation_rows=len(evaluation))
                directory = output / "fits" / f"{phase}__{configuration}__{name}"
                directory.mkdir(parents=True)
                model = build_model(name)
                preprocessor = make_preprocessor(numeric, categorical)
                timing = {}
                total_start = time.perf_counter()
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    tick = time.perf_counter()
                    encoded = preprocessor.fit_transform(X.iloc[train])
                    timing["preprocessing_fit_seconds"] = time.perf_counter() - tick
                    require(np.isfinite(encoded).all(), "Non-finite training features")
                    tick = time.perf_counter()
                    model.fit(encoded, y[train])
                    timing["model_fit_seconds"] = time.perf_counter() - tick
                    feature_count = encoded.shape[1]
                    del encoded
                    tick = time.perf_counter()
                    evaluation_encoded = preprocessor.transform(X.iloc[evaluation])
                    timing["evaluation_transform_seconds"] = time.perf_counter() - tick
                    require(np.isfinite(evaluation_encoded).all(), "Non-finite evaluation features")
                    tick = time.perf_counter()
                    probabilities = model.predict_proba(evaluation_encoded)
                    predicted = model.classes_[np.argmax(probabilities, axis=1)]
                    timing["inference_seconds"] = time.perf_counter() - tick
                    del evaluation_encoded
                require(np.array_equal(model.classes_, np.arange(len(classes))), "Unexpected model class order")
                warning_records = [{"category": item.category.__name__, "message": str(item.message)} for item in caught]
                convergence = any(issubclass(item.category, ConvergenceWarning) for item in caught)
                predictions = pd.DataFrame({"row_id": evaluation, "group_id": membership.loc[evaluation, "group_id"].to_numpy(),
                                            "y_true": labels[evaluation], "y_pred": np.asarray(classes)[predicted]})
                if phase == "refit":
                    predictions["exposed_to_A"] = exposure.exposed_to_A.to_numpy()
                for index, label in enumerate(classes):
                    predictions[f"probability_{label}"] = probabilities[:, index]
                save_csv(predictions, directory / "predictions.csv.gz")
                numeric_pipeline = preprocessor.named_transformers_["num"]
                categorical_pipeline = preprocessor.named_transformers_["cat"]
                write_json(directory / "preprocessing.json", {
                    "fit_row_ids_sha256": hashlib.sha256(train.astype("<i8").tobytes()).hexdigest(),
                    "numeric_imputation": numeric_pipeline["imputer"].statistics_.tolist(),
                    "numeric_mean": numeric_pipeline["scaler"].mean_.tolist(),
                    "numeric_scale": numeric_pipeline["scaler"].scale_.tolist(),
                    "categorical_imputation": [str(v) for v in categorical_pipeline["imputer"].statistics_],
                    "categories": [[str(v) for v in values] for values in categorical_pipeline["onehot"].categories_],
                    "encoded_feature_names": preprocessor.get_feature_names_out().tolist()})
                timing["fit_total_seconds"] = time.perf_counter() - total_start
                fit = {"phase": phase, "configuration": configuration, "model": name, "params": model.get_params(),
                       "train_rows": len(train), "evaluation_rows": len(evaluation), "encoded_features": feature_count,
                       "timings": timing, "warnings": warning_records, "convergence_warning": convergence,
                       "iterations": getattr(model, "n_iter_", np.array([], dtype=int)).tolist(),
                       "preprocessing_sha256": sha256(directory / "preprocessing.json"),
                       "predictions_sha256": sha256(directory / "predictions.csv.gz")}
                write_json(directory / "fit.json", fit)
                manifest["completed_fits"] += 1
                write_json(output / "manifest.json", manifest)
                event("fit_completed", phase=phase, configuration=configuration, model=name,
                      completed_fits=manifest["completed_fits"], convergence_warning=convergence,
                      model_fit_seconds=timing["model_fit_seconds"], warnings=warning_records)
                del model, preprocessor, probabilities, predictions
                gc.collect()
        summarize(output, classes)
        require(manifest["completed_fits"] == 28, "Incomplete pilot")
        manifest["status"] = "completed"
        manifest["fits_with_convergence_warning"] = int(pd.read_csv(output / "timings.csv").convergence_warning.sum())
        if manifest["fits_with_convergence_warning"]:
            manifest["status"] = "completed_with_convergence_warnings"
        event("pilot_completed", status=manifest["status"])
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(error).__name__}: {error}"
        event("pilot_failed", error=manifest["error"], traceback=traceback.format_exc())
        summarize(output, classes)
        raise
    finally:
        manifest["finished_at_utc"] = utc_now()
        manifest["elapsed_seconds_including_preflight"] = time.perf_counter() - started
        manifest["artifacts_sha256"] = {p.relative_to(output).as_posix(): sha256(p) for p in sorted(output.rglob("*"))
                                         if p.is_file() and p.name != "manifest.json"}
        write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.output.resolve())

"""Independently recompute pilot metrics from saved predictions, without fitting."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, precision_recall_fscore_support, precision_score)

from audit_ton_iot_split import ROOT, require, sha256
from run_overlap_pilot import CONFIGURATIONS, MODEL_NAMES, OUTPUT, PARTITIONS, fit_plan, rows_for_fit, utc_now, write_json
from verify_overlap_partitions import verify_source


def independent_metrics(truth, predicted, classes, weights=None):
    truth, predicted = np.asarray(truth), np.asarray(predicted)
    weights = np.ones(len(truth)) if weights is None else weights
    normal = truth == "normal"
    normal_count, attack_count = weights[normal].sum(), weights[~normal].sum()
    return {
        "accuracy": accuracy_score(truth, predicted, sample_weight=weights),
        "macro_f1": f1_score(truth, predicted, labels=classes, average="macro", sample_weight=weights, zero_division=0),
        "weighted_f1": f1_score(truth, predicted, labels=classes, average="weighted", sample_weight=weights, zero_division=0),
        "balanced_accuracy": balanced_accuracy_score(truth, predicted, sample_weight=weights),
        "macro_precision": precision_score(truth, predicted, labels=classes, average="macro", sample_weight=weights, zero_division=0),
        "fpr": weights[normal & (predicted != "normal")].sum() / normal_count if normal_count else np.nan,
        "fnr": weights[(~normal) & (predicted == "normal")].sum() / attack_count if attack_count else np.nan,
    }


def close(actual, expected, description):
    require(np.allclose(actual, expected, rtol=1e-9, atol=1e-12, equal_nan=True), description)


def verify_analysis(directory, frames, classes, pilot_hash):
    output = directory / "analysis"
    manifest = json.loads((output / "manifest.json").read_text())
    require(manifest["pilot_manifest_sha256"] == pilot_hash, "Analysis uses a different pilot")
    require(manifest["replicates"] == 2000 and manifest["seed"] == 1301, "Bootstrap settings changed")
    require(sha256(ROOT / "scripts/analyze_overlap_pilot.py") == manifest["source_sha256"], "Analysis source changed")
    for name, expected in manifest["artifacts_sha256"].items():
        require(sha256(output / name) == expected, f"Analysis artifact changed: {name}")
    draws = pd.read_csv(output / "bootstrap_replicates.csv.gz")
    intervals = pd.read_csv(output / "metric_intervals.csv")
    contrasts = pd.read_csv(output / "paired_comparisons.csv")
    controls = pd.read_csv(output / "control_summary.csv")
    coverage = pd.read_csv(output / "bootstrap_coverage.csv")
    require(len(draws) == 2000 * 14 * 3 and len(intervals) == 14 * 3 * 4
            and len(contrasts) == 2 * 3 * 12 * 4 and len(controls) == 2 * 3 * 4 and len(coverage) == 3,
            "Unexpected analysis table size")
    reference = frames[("logistic_regression", "fixed_A")]
    rng = np.random.default_rng(1301)
    metrics = ["macro_f1", "balanced_accuracy", "fpr", "fnr"]
    checked_samples = 0
    for subgroup in ("all", "exposed", "non_exposed"):
        mask = np.ones(len(reference), dtype=bool) if subgroup == "all" else reference.exposed_to_A.to_numpy(dtype=bool)
        if subgroup == "non_exposed":
            mask = ~mask
        selected = reference.loc[mask]
        groups, inverse = np.unique(selected.group_id, return_inverse=True)
        expected_classes = set(selected.y_true)
        saved = {}
        points = {}
        for key, frame in frames.items():
            block = draws[(draws.subgroup == subgroup) & (draws.model == key[0]) & (draws.configuration == key[1])].sort_values("replicate")
            require(np.array_equal(block.replicate, np.arange(2000)), "Missing/duplicate bootstrap replicate")
            saved[key] = block.reset_index(drop=True)
            points[key] = independent_metrics(frame.loc[mask, "y_true"], frame.loc[mask, "y_pred"], classes)
        missing = np.empty(2000, dtype=int)
        for replicate in range(2000):
            weights = np.bincount(rng.integers(0, len(groups), size=len(groups)), minlength=len(groups))[inverse]
            missing[replicate] = len(expected_classes - set(selected.y_true.to_numpy()[weights > 0]))
            if replicate in (0, 1, 1999):
                for key, frame in frames.items():
                    result = independent_metrics(frame.loc[mask, "y_true"], frame.loc[mask, "y_pred"], classes, weights)
                    close(saved[key].loc[replicate, metrics].to_numpy(dtype=float), [result[m] for m in metrics],
                          f"Bootstrap recomputation mismatch: {subgroup}/{key}/{replicate}")
                    checked_samples += 1
        for block in saved.values():
            require(np.array_equal(block.missing_class_count, missing), "Bootstrap class coverage changed")
        row = coverage[coverage.subgroup == subgroup]
        require(len(row) == 1 and int(row.iloc[0].replicates_missing_class) == int((missing > 0).sum()), "Invalid coverage summary")

        def check_interval(row, estimate, samples):
            require(len(row) == 1, "Missing or duplicate interval")
            row = row.iloc[0]
            valid = samples[(missing == 0) & np.isfinite(samples)]
            expected = np.quantile(valid, [.025, .975]) if len(valid) else [np.nan, np.nan]
            close([row.estimate, row.ci_low, row.ci_high], [estimate, *expected], "Incorrect percentile interval")
            require(row.valid_replicates == len(valid), "Invalid interval denominator")

        for key, block in saved.items():
            for metric in metrics:
                row = intervals[(intervals.subgroup == subgroup) & (intervals.model == key[0])
                                & (intervals.configuration == key[1]) & (intervals.metric == metric)]
                check_interval(row, points[key][metric], block[metric].to_numpy())
        for model in MODEL_NAMES:
            for metric in metrics:
                a, b = (model, "fixed_A"), (model, "fixed_B")
                cs = [(model, name) for name in CONFIGURATIONS[2:]]
                c_points = np.array([points[key][metric] for key in cs])
                c_samples = np.stack([saved[key][metric] for key in cs])
                checks = [("B_minus_A", points[b][metric] - points[a][metric], saved[b][metric] - saved[a][metric]),
                          ("B_minus_mean_C", points[b][metric] - c_points.mean(), saved[b][metric] - c_samples.mean(axis=0))]
                for key in cs:
                    checks.extend([(f"{key[1]}_minus_A", points[key][metric] - points[a][metric], saved[key][metric] - saved[a][metric]),
                                   (f"B_minus_{key[1]}", points[b][metric] - points[key][metric], saved[b][metric] - saved[key][metric])])
                for contrast, estimate, samples in checks:
                    row = contrasts[(contrasts.subgroup == subgroup) & (contrasts.model == model)
                                    & (contrasts.metric == metric) & (contrasts.contrast == contrast)]
                    check_interval(row, estimate, np.asarray(samples))
                row = controls[(controls.subgroup == subgroup) & (controls.model == model) & (controls.metric == metric)]
                require(len(row) == 1 and row.iloc[0].controls == 5, "Invalid C summary")
                close([row.iloc[0]["mean"], row.iloc[0].standard_deviation], [c_points.mean(), c_points.std(ddof=1)], "C summary mismatch")
    return {"status": "PASS", "bootstrap_model_replicates_recomputed": checked_samples,
            "coverage_draws_recomputed": 6000, "all_intervals_and_contrasts_recomputed": True,
            "analysis_manifest_sha256": sha256(output / "manifest.json")}


def verify_pilot(directory, include_analysis=True):
    manifest = json.loads((directory / "manifest.json").read_text())
    pilot_hash = sha256(directory / "manifest.json")
    require(manifest["status"].startswith("completed") and manifest["completed_fits"] == 28, "Incomplete pilot")
    require(manifest["configurations"] == CONFIGURATIONS and manifest["planned_fits"] == 28, "Pilot scope changed")
    require(manifest["partition_manifest_sha256"] == sha256(PARTITIONS / "manifest.json"), "Partition manifest changed")
    for name, expected in manifest["artifacts_sha256"].items():
        require(sha256(directory / name) == expected, f"Pilot artifact changed: {name}")
    source_checks = {name: verify_source(ROOT / name, expected) for name, expected in manifest["source_sha256"].items()}
    classes = manifest["classes"]
    membership = pd.read_csv(PARTITIONS / "row_groups.csv.gz").set_index("row_id")
    indices = pd.read_csv(PARTITIONS / "partition_indices.csv.gz")
    exposure = pd.read_csv(PARTITIONS / "fixed_test_subgroups.csv.gz").set_index("row_id")
    overall = pd.read_csv(directory / "metrics.csv")
    per_class = pd.read_csv(directory / "per_class_metrics.csv")
    matrices = pd.read_csv(directory / "confusion_matrices.csv")
    timings = pd.read_csv(directory / "timings.csv")
    require(len(overall) == 56 and len(per_class) == 560 and len(matrices) == 5600 and len(timings) == 28,
            "Unexpected metric table size")
    fit_records, refits, warning_records = [], {}, []
    require(len(list((directory / "fits").glob("*/fit.json"))) == 28, "Unexpected fit records")
    for phase, configuration, model in fit_plan():
        folder = directory / "fits" / f"{phase}__{configuration}__{model}"
        fit = json.loads((folder / "fit.json").read_text())
        require((fit["phase"], fit["configuration"], fit["model"]) == (phase, configuration, model), "Fit identity changed")
        require(fit["convergence_warning"] == any(item["category"] == "ConvergenceWarning" for item in fit["warnings"]),
                "Convergence flag does not match warning records")
        warning_records.extend({"phase": phase, "configuration": configuration, "model": model, **item} for item in fit["warnings"])
        train, evaluation = rows_for_fit(indices, configuration, phase)
        predictions = pd.read_csv(folder / "predictions.csv.gz")
        preprocessing = json.loads((folder / "preprocessing.json").read_text())
        require(sha256(folder / "predictions.csv.gz") == fit["predictions_sha256"]
                and sha256(folder / "preprocessing.json") == fit["preprocessing_sha256"], "Fit artifact changed")
        require(preprocessing["fit_row_ids_sha256"] == hashlib.sha256(train.astype("<i8").tobytes()).hexdigest(), "Fit rows changed")
        require(fit["train_rows"] == len(train) and fit["evaluation_rows"] == len(evaluation), "Fit counts changed")
        require(np.array_equal(predictions.row_id, evaluation), "Prediction row order changed")
        require(np.array_equal(predictions.group_id, membership.loc[evaluation].group_id), "Prediction groups changed")
        require(np.array_equal(predictions.y_true, membership.loc[evaluation, "class"]), "Ground truth changed")
        require(fit["params"] == manifest["models"][model] and fit["params"]["random_state"] == 1103
                and fit["params"]["class_weight"] is None, "Model parameters changed")
        if model == "logistic_regression":
            require((fit["params"]["C"], fit["params"]["solver"], fit["params"]["max_iter"]) == (1, "lbfgs", 3000), "LR settings changed")
        else:
            require((fit["params"]["n_estimators"], fit["params"]["n_jobs"], fit["params"]["min_samples_leaf"],
                     fit["params"]["max_depth"]) == (200, 1, 1, None), "RF settings changed")
        probabilities = predictions[[f"probability_{label}" for label in classes]].to_numpy()
        require(np.isfinite(probabilities).all() and (probabilities >= 0).all() and (probabilities <= 1).all(), "Invalid probabilities")
        close(probabilities.sum(axis=1), 1., "Probabilities do not sum to one")
        require(np.array_equal(predictions.y_pred, np.asarray(classes)[probabilities.argmax(axis=1)]), "Probability/prediction mismatch")
        masks = {"all": np.ones(len(predictions), dtype=bool)}
        if phase == "refit":
            require(np.array_equal(predictions.exposed_to_A, exposure.loc[evaluation].exposed_to_A), "Exposure changed")
            masks.update({"exposed": predictions.exposed_to_A.to_numpy(dtype=bool),
                          "non_exposed": ~predictions.exposed_to_A.to_numpy(dtype=bool)})
            refits[(model, configuration)] = predictions
        for subgroup, mask in masks.items():
            selected = predictions.loc[mask]
            metrics = independent_metrics(selected.y_true, selected.y_pred, classes)
            selector = lambda table: table[(table.phase == phase) & (table.configuration == configuration)
                                           & (table.model == model) & (table.subgroup == subgroup)]
            saved = selector(overall)
            require(len(saved) == 1 and saved.iloc[0].rows == len(selected)
                    and saved.iloc[0].groups == selected.group_id.nunique(), "Metric coverage mismatch")
            close(saved.iloc[0][list(metrics)].to_numpy(dtype=float), list(metrics.values()), "Overall metrics mismatch")
            precision, recall, f1, support = precision_recall_fscore_support(selected.y_true, selected.y_pred, labels=classes, zero_division=0)
            saved = selector(per_class).set_index("class").loc[classes]
            close(saved[["precision", "recall", "f1", "support"]].to_numpy(), np.stack([precision, recall, f1, support], axis=1), "Class metrics mismatch")
            matrix = confusion_matrix(selected.y_true, selected.y_pred, labels=classes)
            saved = selector(matrices).pivot(index="true_class", columns="predicted_class", values="count").loc[classes, classes]
            require(np.array_equal(matrix, saved.to_numpy()), "Confusion matrix mismatch")
        require(all(np.isfinite(value) and value >= 0 for value in fit["timings"].values()), "Invalid runtime")
        timing = timings[(timings.phase == phase) & (timings.configuration == configuration) & (timings.model == model)]
        require(len(timing) == 1, "Timing record missing")
        require(bool(timing.iloc[0].convergence_warning) == fit["convergence_warning"], "Timing warning flag changed")
        close(timing.iloc[0][list(fit["timings"])].to_numpy(dtype=float), list(fit["timings"].values()), "Timing summary mismatch")
        fit_records.append({"phase": phase, "configuration": configuration, "model": model, "status": "PASS"})
    saved_warnings = pd.read_csv(directory / "warnings.csv").to_dict("records")
    require(saved_warnings == warning_records, "Warning summary differs from fit records")
    require(int(timings.convergence_warning.sum()) == manifest["fits_with_convergence_warning"], "Warning count changed")
    report = {"status": "PASS", "pilot_manifest_sha256": pilot_hash,
              "verifier_sha256": sha256(Path(__file__)), "source_checks": source_checks,
              "fits_checked": fit_records, "metric_sets_recomputed": len(overall), "training_executed": False}
    if include_analysis:
        report["analysis"] = verify_analysis(directory, refits, classes, pilot_hash)
    report["synthetic_tests"] = []
    for name in ("test_overlap_partitions.py", "test_overlap_pilot.py", "test_overlap_analysis.py"):
        script = ROOT / "scripts" / name
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        require(result.returncode == 0, f"Synthetic tests failed: {name}: {result.stderr}")
        report["synthetic_tests"].append({"script": name, "source_sha256": sha256(script),
                                           "exit_code": result.returncode, "output": result.stdout + result.stderr})
    report["finished_at_utc"] = utc_now()
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=OUTPUT)
    parser.add_argument("--skip-analysis", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    destination = args.directory / "pilot_validation.json"
    require(not args.save or not destination.exists(), "Validation already exists; will not overwrite")
    result = verify_pilot(args.directory.resolve(), not args.skip_analysis)
    if args.save:
        write_json(destination, result)

# Fixed-test LR/RF pilot

The supervisor approved checkpoint `af97421` and authorized only the fixed-test multiclass A/B/C pilot: seven configurations, two models, one diagnostic fit and one refit per combination (28 fits). The random/group-disjoint model comparison remains deferred. Historical partition manifests and thesis results are not modified.

## Execution

Use the pinned Python 3.11.9 environment and packages from `research/ton_iot_audit/requirements.txt`, from the repository root:

```sh
python scripts/test_overlap_pilot.py
python scripts/run_overlap_pilot.py
python scripts/test_overlap_analysis.py
python scripts/analyze_overlap_pilot.py
python scripts/verify_overlap_pilot.py --save
```

The runner validates the saved partitions and original dataset before training. It refuses to overwrite its output directory. For a separate reproduction, pass `--output` pointing to a new directory. No trained models or raw features are saved. Predictions retain row/group identifiers, labels and class probabilities. All fits use their own training-only preprocessor with frozen feature roles. Native numerical libraries use one thread; Random Forest retains `n_jobs=1`. Full estimator parameters and environment details are recorded.

Diagnostic fits evaluate validation only. Refit models train on the union of the saved training and validation rows, in that order, and evaluate the unchanged test. No hyperparameters or decisions are selected using validation/test scores. Convergence warnings are saved and reported, without retries or parameter changes; execution stops on exceptions. Each completed fit is saved before proceeding, and incomplete runs are explicitly marked as such.

## Analysis conventions

Macro F1 uses all ten frozen labels, with zero for undefined class F1. Balanced accuracy averages recall over classes supported in the evaluated subset. FPR is the fraction of normal rows classified as any attack; FNR is the fraction of attack rows classified as normal. Undefined rates are left empty, not replaced with zero. Class metrics and confusion matrices retain all labels.

Test exposure is defined once relative to A, for all models and configurations. The planned paired group bootstrap uses 2,000 replicates and seed 1301, separately for all/exposed/non-exposed rows in that order. Within each subset and replicate, all models use the same sampled groups, including every row in each sampled group. Replicates missing a class that was present in the original subset are counted and excluded from intervals, without replacement draws. Intervals are 2.5/97.5 percentiles. Classwise point estimates remain available; the main bootstrap contrasts cover Macro F1, balanced accuracy, FPR and FNR.

Contrasts are B minus A, each C minus A, B minus each C, and B minus the mean of the five C controls. The C standard deviation describes variation across the fixed removal seeds, not a confidence interval. Bootstrap intervals are conditional on the fitted models and this test; they do not estimate training variability. No causal or deployment claim follows automatically from these comparisons.

## Outputs and verification

`results/manifest.json` identifies the actual execution, source hashes, uncommitted state and complete parameters. `results/fits/` retains a prediction archive, preprocessing statistics and a fit record for each completed fit. `metrics.csv`, `per_class_metrics.csv`, `confusion_matrices.csv`, `timings.csv` and `warnings.csv` separate diagnostic validation from refit test results. `events.jsonl` records starts, completions and any failures.

The analysis produces `results/analysis/`, including paired contrasts, percentile intervals, C variability, bootstrap coverage, all 2,000 draws per subgroup/model/configuration, and an Italian `report.md` generated from the actual CSVs. It refuses to overwrite earlier analysis. For a separate reproduction, pass the new pilot path with `--directory`; an optional `--output` selects a new analysis destination.

The verifier checks all 28 fits against frozen row/group identities, labels, parameters and probabilities. It independently recomputes all 56 metric sets using scikit-learn, all class metrics and confusion matrices, all intervals/contrasts, all 6,000 bootstrap coverage checks and the first two and last bootstrap replicates for every model/configuration/subgroup. It does not retrain the classifiers. `--save` writes a new `pilot_validation.json` and refuses to overwrite it. Omit `--save` for subsequent checks. For the training-only check before analysis use `--skip-analysis` without `--save`.

## Completed local run: 27 October 2026

All 28 fits completed without warnings or parameter changes. The measured execution time including preflight was 1,396.40 seconds. The independent verification passed, as did the 15 partition tests, eight pilot tests and five bootstrap tests. The [Italian report](results/analysis/report.md) and [verification record](results/pilot_validation.json) accompany the CSV tables and predictions. The working tree was not committed for this execution; the recorded parent commit and source hashes identify its provenance.

The overall Macro F1 contrasts do not show a uniform decrease: their B-minus-A and B-minus-mean-C bootstrap intervals include zero for both models. For LR, FPR increased from 0.0814 in A to 0.1493 in B, while FNR decreased from 0.0199944 to 0.0045329. RF's exposed-subgroup Macro F1 decreased by 17.0242 percentage points relative to A, but that subgroup contains only two `mitm`, five `ddos` and ten `injection` rows. This makes classwise interpretation essential. Of 2,000 exposed-subgroup bootstrap draws, 302 lacked at least one class and were excluded as specified; the corresponding intervals use 1,698 draws and are conditional on class presence. Neither these subgroup findings nor the small overall contrasts justify a general claim about deployment performance.

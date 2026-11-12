# Additional classwise error analysis

This descriptive follow-up was requested after validation of pilot commit `c4f9f32`. It is separate from the planned bootstrap analysis. It reads the existing refit predictions only and never trains models or modifies the pilot directory. The random/group-disjoint comparison remains deferred.

The [Italian report](results/report.md) summarizes exposed RF classes, all five C controls, error destinations and the LR false-alarm/missed-attack tradeoff. The CSVs cover both models, all ten classes and all three test subgroups.

## Reproduce

Use the existing pinned environment from `research/ton_iot_audit/requirements.txt`, at the repository root:

```sh
python scripts/test_overlap_errors.py
python scripts/explain_overlap_errors.py --output research/ton_iot_overlap_impact/error_analysis/results
```

The script refuses an existing output directory and any destination inside the pilot directory. For a new reproduction, use a fresh `--output` directory. `--directory` optionally selects another verified pilot's `results` directory. No raw dataset is needed for this additional analysis.

## Tables and checks

- `class_changes.csv`: true-class row/group supports; precision, recall, F1 and one-vs-rest TP/FP/FN in A and each target (B or one of five C); paired changes and each class's contribution to the Macro-F1 difference in percentage points.
- `error_transitions.csv`: correct-to-correct, correct-to-wrong, wrong-to-correct, same wrong prediction and changed wrong prediction, including zero-count categories. Each cell records rows and distinct groups.
- `prediction_transitions.csv`: full true-class/prediction-A/prediction-target breakdown, retaining nonzero cells.
- `manifest.json`: input hashes, script hash (raw and LF-normalized), environment and checks. The execution commit is the actual parent, not a future delivery commit.

Metrics are recomputed from predictions and checked against the original per-class tables. Row/group identities, labels and exposure must match across all 14 refits. Transition counts must reconcile with supports and changes in errors; class contributions must sum to the Macro-F1 change. All pilot files are hashed before and after processing and must remain byte-identical.

Groups are distinct within each cell, not independent observations or additive across classes/cells when labels conflict. C means/ranges describe the five fixed controls, not confidence intervals or a new ensemble. No new statistical significance claims are made.

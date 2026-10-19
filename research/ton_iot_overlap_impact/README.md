# TON-IoT overlap impact: SPLIT-02 checkpoint

This checkpoint prepares and checks data partitions; the scripts do not train models. Historical thesis and audit outputs remain unchanged.

## Reproduce

Run from the repository root with the existing Python 3.11.9 environment and the pinned packages in `research/ton_iot_audit/requirements.txt`. The original dataset and initial audit artifacts must be present; the loader verifies their hashes and schema.

```powershell
.\.venv\Scripts\python.exe scripts/test_overlap_partitions.py
.\.venv\Scripts\python.exe scripts/build_overlap_partitions.py
.\.venv\Scripts\python.exe scripts/verify_overlap_partitions.py --save
```

The builder refuses to overwrite an existing output directory. For another execution use `--output` with a fresh directory outside the repository. Group-stratified splitting can take several minutes. Exit code 2 means a class is absent from at least one required partition: inspect the manifest and stop for protocol review, not seed selection.

## Contents

- `protocol.md`: proposed experiment design, restrictions, fit budget and metrics.
- `checkpoint.md`: measured feasibility results and remaining review requirements.
- `literature_matrix.md`: comparison based on six full texts, including the SSRN preprint, covering split design, repetitions, code availability and differences from this protocol.
- `results/manifest.json`: input/source hashes, environment, execution HEAD and actual dirty working-tree state, seeds and coverage checks.
- `results/partition_indices.csv.gz`: all ordered partitions, including excluded rows.
- `results/row_groups.csv.gz`: group membership and labels, without raw feature vectors.
- `results/feasibility.csv`, `results/class_counts.csv`: measured partition counts and overlaps, not classifier metrics.
- `results/feature_columns.csv`, `results/label_conflicts.csv`, `results/fixed_test_subgroups.csv.gz`: frozen feature order, preserved conflicts and diagnostic test subgroups.

The execution HEAD is the parent commit, not a claim that uncommitted new scripts existed in that commit. Source hashes and the captured working-tree status identify the actual execution. No historical SHA is replaced. Group identifiers use the frozen input row order and are not portable across different datasets.

`validation.json` is a separate verification record linked to the manifest hash. It verifies saved row coverage, per-class counts, overlap counts and matched removals without rerunning the splitter. It is not evidence of a second full dataset execution.

Review and approval of the protocol are required before implementing/running the model pilot. The available partition statistics do not establish an effect on accuracy or F1.

## Source hashes across Windows and Linux

The historical manifest records byte-level hashes from the execution environment. Git can check out `src/data/preprocess.py` with CRLF on Windows and LF on Linux. The verifier first checks the unchanged historical hash against the current bytes. If it differs, it tries only LF and CRLF variants in memory; one must reproduce that same historical hash. It does not strip whitespace, decode/re-encode the file or replace the reference hash. Other changes fail verification. An unknown historical mixed-newline layout is not reconstructed and also fails unless the bytes match exactly.

The printed report includes `source_checks`, with the historical hash, checkout hash and matching variant (`exact`, `lf` or `crlf`). Dataset-derived artifacts still require exact byte matches. The committed `manifest.json` and `validation.json` remain unchanged; the latter records the original verifier and its eight tests, not this correction.

To check the existing delivery without rebuilding partitions or overwriting historical records, run:

```sh
python scripts/test_overlap_partitions.py
python scripts/verify_overlap_partitions.py
```

Use the pinned environment described above. Do not use `--save` for the existing results directory, which already contains the historical validation record. These checks do not train models.

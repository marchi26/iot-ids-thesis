"""Paired group bootstrap of saved fixed-test predictions; never train models."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix

from audit_ton_iot_split import ROOT, require, sha256
from build_overlap_partitions import save_csv
from run_overlap_pilot import CONFIGURATIONS, MODEL_NAMES, OUTPUT, utc_now, write_json

REPLICATES = 2000
SEED = 1301
METRICS = ["macro_f1", "balanced_accuracy", "fpr", "fnr"]


def scores(matrices, normal_index):
    """Vectorized confusion-matrix metrics with fixed labels and explicit NaN."""
    support, predicted = matrices.sum(axis=-1), matrices.sum(axis=-2)
    tp = np.diagonal(matrices, axis1=-2, axis2=-1)
    recall = np.divide(tp, support, out=np.zeros_like(tp, dtype=float), where=support != 0)
    f1 = np.divide(2 * tp, support + predicted, out=np.zeros_like(tp, dtype=float), where=(support + predicted) != 0)
    normal, attacks = support[..., normal_index], support.sum(axis=-1) - support[..., normal_index]
    balanced = np.divide(recall.sum(axis=-1), (support > 0).sum(axis=-1),
                         out=np.full(normal.shape, np.nan), where=(support > 0).any(axis=-1))
    fpr = np.divide(normal - tp[..., normal_index], normal, out=np.full(normal.shape, np.nan), where=normal > 0)
    fnr = np.divide(predicted[..., normal_index] - tp[..., normal_index], attacks,
                    out=np.full(normal.shape, np.nan), where=attacks > 0)
    return np.stack([f1.mean(axis=-1), balanced, fpr, fnr], axis=-1)


def group_confusions(group_ids, truth, predictions, class_count):
    """One sparse row per group, one block of confusion cells per model."""
    groups, inverse = np.unique(group_ids, return_inverse=True)
    columns = np.concatenate([index * class_count ** 2 + truth * class_count + prediction
                              for index, prediction in enumerate(predictions)])
    rows = np.tile(inverse, len(predictions))
    matrix = coo_matrix((np.ones(len(rows), dtype=np.int64), (rows, columns)),
                        shape=(len(groups), len(predictions) * class_count ** 2)).tocsr()
    return matrix, groups


def bootstrap(group_matrix, class_count, model_count, normal_index, rng, replicates=REPLICATES):
    point_matrix = np.asarray(group_matrix.sum(axis=0)).reshape(model_count, class_count, class_count)
    expected_classes = point_matrix[0].sum(axis=1) > 0
    samples = np.empty((replicates, model_count, len(METRICS)))
    missing = np.zeros(replicates, dtype=int)
    transposed = group_matrix.T.tocsr()
    for index in range(replicates):
        selected = rng.integers(0, group_matrix.shape[0], size=group_matrix.shape[0])
        counts = np.bincount(selected, minlength=group_matrix.shape[0])
        matrices = np.asarray(transposed @ counts).reshape(model_count, class_count, class_count)
        missing[index] = int((expected_classes & (matrices[0].sum(axis=1) == 0)).sum())
        samples[index] = scores(matrices, normal_index)
    return scores(point_matrix, normal_index), samples, missing


def percentile_interval(samples, valid):
    selected = samples[valid & np.isfinite(samples)]
    if len(selected) == 0:
        return np.nan, np.nan, 0
    low, high = np.quantile(selected, [.025, .975])
    return float(low), float(high), len(selected)


def markdown_table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
                     + ["| " + " | ".join(str(value) for value in row) + " |" for row in rows])


def write_report(directory, output, manifest):
    metrics = pd.read_csv(directory / "metrics.csv")
    metrics = metrics[(metrics.phase == "refit") & (metrics.subgroup == "all")]
    per_class = pd.read_csv(directory / "per_class_metrics.csv")
    per_class = per_class[(per_class.phase == "refit") & (per_class.subgroup == "all")]
    comparisons = pd.read_csv(output / "paired_comparisons.csv")
    coverage = pd.read_csv(output / "bootstrap_coverage.csv")
    timings = pd.read_csv(directory / "timings.csv")
    names = {"logistic_regression": "LR", "random_forest": "RF"}
    number = lambda value: "n.d." if pd.isna(value) else f"{value:.4f}"
    baseline_rows = [[names[row.model], row.configuration.removeprefix("fixed_"),
                      *[number(getattr(row, metric)) for metric in METRICS]] for row in metrics.itertuples()]
    selected = comparisons[(comparisons.metric == "macro_f1")
                           & comparisons.contrast.isin(["B_minus_A", "B_minus_mean_C"])]
    delta_rows = [[names[row.model], row.subgroup, row.contrast,
                   number(100 * row.estimate), f"[{number(100 * row.ci_low)}, {number(100 * row.ci_high)}]",
                   row.valid_replicates] for row in selected.itertuples()]
    recall_rows = []
    for label in manifest["classes"]:
        values = [label]
        for model in MODEL_NAMES:
            block = per_class[(per_class.model == model) & (per_class["class"] == label)].set_index("configuration")
            values.extend([number(block.loc["fixed_A", "recall"]), number(block.loc["fixed_B", "recall"]),
                           number(block.loc[CONFIGURATIONS[2:], "recall"].mean())])
        values.append(int(block.loc["fixed_A", "support"]))
        recall_rows.append(values)
    time_rows = []
    for model in MODEL_NAMES:
        subset = timings[timings.model == model]
        time_rows.append([names[model], len(subset), f"{subset.model_fit_seconds.sum():.2f}",
                          f"{subset.preprocessing_fit_seconds.sum():.2f}", f"{subset.inference_seconds.sum():.2f}"])
    warning_count = int(timings.convergence_warning.sum())
    convergence = ("Non sono stati registrati avvisi di convergenza."
                   if warning_count == 0 else f"Sono stati registrati avvisi di convergenza in {warning_count} fit; parametri e limiti non sono stati modificati.")
    observations = []
    for model in MODEL_NAMES:
        block = comparisons[(comparisons.model == model) & (comparisons.subgroup == "all") & (comparisons.metric == "macro_f1")].set_index("contrast")
        delta, controlled = block.loc["B_minus_A"], block.loc["B_minus_mean_C"]
        observations.append(f"Per {names[model]}, la differenza di Macro F1 B meno A è {100 * delta.estimate:+.4f} punti percentuali; "
                            f"B meno la media dei cinque C è {100 * controlled.estimate:+.4f} punti. "
                            "Il secondo contrasto confronta pool con uguale numerosità per classe, ma non con uguale distribuzione delle feature.")
    text = f"""# SPLIT-02: risultati del pilota multiclasse a test fisso

## Ambito ed esecuzione

Sono stati eseguiti i 28 fit autorizzati: 14 diagnostici sul training interno, valutati sulla validazione, e 14 refit sull'intero pool, valutati sul test. Le sette configurazioni sono A, B e i cinque controlli C. Il confronto casuale/a gruppi non è stato avviato. Nessuna scelta di parametri è stata effettuata usando i risultati di validazione o test.

Inizio registrato: `{manifest['started_at_utc']}`; fine: `{manifest['finished_at_utc']}`. Il tempo complessivo, inclusi i controlli preliminari, è {manifest['elapsed_seconds_including_preflight']:.2f} secondi. Il commit di base è `{manifest['execution_commit']}`; i nuovi script non erano committati e sono identificati dagli hash del manifest.

Il CSV congelato contiene 211.043 righe. Il test è lo stesso in tutti i confronti: 42.209 righe, di cui 6.963 esposte al pool A e 35.246 non esposte. A contiene 168.834 righe nel pool; B e ciascun C ne contengono 152.502. I cinque C rimuovono lo stesso numero di righe di B per ciascuna classe, usando i semi 601, 701, 809, 907 e 1009.

LR usa `C=1`, `solver=lbfgs`, `max_iter=3000`; RF usa 200 alberi, profondità non limitata, `min_samples_leaf=1` e `n_jobs=1`. Entrambi usano seme 1103 e nessuna ponderazione delle classi. Non sono applicati SMOTE o tuning. Le 32 feature e i ruoli numerici/categorici sono quelli congelati; ogni fit apprende imputazione, scala e categorie soltanto dal proprio training. Le librerie numeriche operano con un thread.

## Risultati sul test

I valori sono proporzioni, non percentuali. Macro F1 considera tutte le dieci classi; balanced accuracy è la media dei recall delle classi presenti. FPR indica i normali classificati come attacco, FNR gli attacchi classificati come normali. Le tabelle riguardano i refit; i risultati diagnostici restano separati nei CSV.

{markdown_table(['Modello', 'Configurazione', 'Macro F1', 'Balanced accuracy', 'FPR', 'FNR'], baseline_rows)}

## Confronti appaiati e sottogruppi

Differenze di Macro F1 in punti percentuali, con intervalli percentili al 95% ottenuti da 2.000 ricampionamenti per gruppo, seme 1301. Ogni replica usa gli stessi gruppi per tutti i modelli confrontati. I sottogruppi restano definiti rispetto ad A anche quando si valuta B o C. Gli intervalli sono condizionati ai modelli addestrati e al test disponibile, non descrivono la variabilità di nuovi training. Non è applicata una correzione per confronti multipli; gli intervalli hanno funzione descrittiva.

{markdown_table(['Modello', 'Sottogruppo', 'Contrasto', 'Differenza (pp)', 'IC 95% (pp)', 'Repliche valide'], delta_rows)}

Le repliche prive di una classe presente nel sottogruppo originale sono conteggiate ed escluse dagli intervalli, senza estrazioni sostitutive. I conteggi di tali repliche sono: {', '.join(f'{row.subgroup}: {row.replicates_missing_class}' for row in coverage.itertuples())}. Gli intervalli risultano quindi condizionati anche alla presenza delle classi; una quota elevata di esclusioni ne limita l'interpretazione, soprattutto per le classi rare. Eventuali tassi senza denominatore restano non definiti. I confronti con ogni singolo C, le altre metriche e la deviazione standard fra i cinque controlli sono conservati nei CSV; quest'ultima non è un intervallo di confidenza.

{' '.join(observations)}

## Recall per classe

La colonna C riporta la media dei cinque controlli. Supporti e osservazioni del test non cambiano fra configurazioni. Precision, F1 e matrici di confusione complete, anche per i sottogruppi, sono disponibili nei file allegati.

{markdown_table(['Classe', 'LR A', 'LR B', 'LR media C', 'RF A', 'RF B', 'RF media C', 'Supporto'], recall_rows)}

## Tempi e problemi osservati

{markdown_table(['Modello', 'Fit', 'Training totale (s)', 'Preprocessing fit (s)', 'Inferenza (s)'], time_rows)}

L'inferenza comprende il calcolo delle probabilità e la scelta della classe; la trasformazione delle feature di valutazione è registrata separatamente in `timings.csv`. I tempi dipendono dalla macchina e dal carico durante l'esecuzione. {convergence} Gli avvisi completi sono conservati in `warnings.csv`; non sono stati effettuati tentativi automatici con parametri alternativi.

## Limiti e materiali

B usa le feature del test per definire un intervento diagnostico: non rappresenta una stima cieca del deployment. C controlla quantità e distribuzione delle etichette, non le caratteristiche dei flussi rimossi. Gli effetti osservati riguardano questo campione, queste definizioni di gruppo e questi due modelli; non autorizzano a correggere retroattivamente le metriche della tesi né a dedurre una validità generale per altri dataset. I gruppi con etichette discordanti sono mantenuti.

Le predizioni con `row_id`, `group_id`, etichetta e probabilità sono in `../fits/`. I risultati completi sono in `../metrics.csv`, `../per_class_metrics.csv`, `../confusion_matrices.csv` e `../timings.csv`. In questa cartella si trovano confronti appaiati, intervalli, riepilogo dei controlli e repliche del bootstrap. Il verificatore `scripts/verify_overlap_pilot.py` ricalcola le metriche dalle predizioni e controlla i confronti senza nuovi fit; il suo esito, quando eseguito con `--save`, è salvato separatamente in `../pilot_validation.json`.
"""
    (output / "report.md").write_text(text, encoding="utf-8", newline="\n")


def analyze(directory, output):
    require(not output.exists(), f"Analysis already exists: {output}")
    started = time.perf_counter()
    manifest = json.loads((directory / "manifest.json").read_text())
    require(manifest["status"].startswith("completed") and manifest["completed_fits"] == 28, "Pilot not complete")
    for name, expected in manifest["artifacts_sha256"].items():
        require(sha256(directory / name) == expected, f"Pilot artifact changed: {name}")
    classes = manifest["classes"]
    mapping = {label: index for index, label in enumerate(classes)}
    keys = [(model, configuration) for model in MODEL_NAMES for configuration in CONFIGURATIONS]
    frames = []
    for model, configuration in keys:
        frames.append(pd.read_csv(directory / "fits" / f"refit__{configuration}__{model}" / "predictions.csv.gz"))
    reference = frames[0]
    for frame in frames[1:]:
        require(frame[["row_id", "group_id", "y_true", "exposed_to_A"]].equals(
            reference[["row_id", "group_id", "y_true", "exposed_to_A"]]), "Predictions are not paired")
    require(reference.groupby("group_id").exposed_to_A.nunique().max() == 1, "Exposure splits a group")
    truth = reference.y_true.map(mapping).to_numpy()
    predictions = np.stack([frame.y_pred.map(mapping).to_numpy() for frame in frames])
    output.mkdir(parents=True)
    rng = np.random.default_rng(SEED)
    comparison_rows, interval_rows, sample_frames, c_rows, coverage_rows = [], [], [], [], []
    masks = {"all": np.ones(len(reference), dtype=bool), "exposed": reference.exposed_to_A.to_numpy(dtype=bool),
             "non_exposed": ~reference.exposed_to_A.to_numpy(dtype=bool)}
    for subgroup, mask in masks.items():
        print(f"Bootstrap {subgroup}: {int(mask.sum())} rows, {REPLICATES} replicates", flush=True)
        require(mask.any(), "Empty test subgroup")
        group_matrix, groups = group_confusions(reference.group_id.to_numpy()[mask], truth[mask], predictions[:, mask], len(classes))
        point, samples, missing = bootstrap(group_matrix, len(classes), len(keys), mapping["normal"], rng)
        valid = missing == 0
        expected_labels = sorted(reference.loc[mask, "y_true"].unique().tolist())
        coverage_rows.append({"subgroup": subgroup, "rows": int(mask.sum()), "groups": len(groups),
                              "classes_present": ";".join(expected_labels), "replicates": REPLICATES,
                              "replicates_missing_class": int((~valid).sum()), "complete_class_replicates": int(valid.sum())})
        for index, (model, configuration) in enumerate(keys):
            data = {"subgroup": subgroup, "model": model, "configuration": configuration,
                    "replicate": np.arange(REPLICATES), "missing_class_count": missing}
            data.update({metric: samples[:, index, j] for j, metric in enumerate(METRICS)})
            sample_frames.append(pd.DataFrame(data))
            for j, metric in enumerate(METRICS):
                low, high, count = percentile_interval(samples[:, index, j], valid)
                interval_rows.append({"subgroup": subgroup, "model": model, "configuration": configuration,
                                      "metric": metric, "estimate": point[index, j], "ci_low": low,
                                      "ci_high": high, "valid_replicates": count})
        for model in MODEL_NAMES:
            a, b = keys.index((model, "fixed_A")), keys.index((model, "fixed_B"))
            controls = [keys.index((model, c)) for c in CONFIGURATIONS[2:]]
            comparisons = [("B_minus_A", point[b] - point[a], samples[:, b] - samples[:, a]),
                           ("B_minus_mean_C", point[b] - point[controls].mean(axis=0),
                            samples[:, b] - samples[:, controls].mean(axis=1))]
            for c, index in zip(CONFIGURATIONS[2:], controls):
                comparisons.extend([(f"{c}_minus_A", point[index] - point[a], samples[:, index] - samples[:, a]),
                                    (f"B_minus_{c}", point[b] - point[index], samples[:, b] - samples[:, index])])
            for name, estimate, draws in comparisons:
                for j, metric in enumerate(METRICS):
                    low, high, count = percentile_interval(draws[:, j], valid)
                    comparison_rows.append({"subgroup": subgroup, "model": model, "contrast": name,
                                            "metric": metric, "estimate": estimate[j], "ci_low": low,
                                            "ci_high": high, "valid_replicates": count})
            for j, metric in enumerate(METRICS):
                c_rows.append({"subgroup": subgroup, "model": model, "metric": metric,
                               "controls": len(controls), "mean": point[controls, j].mean(),
                               "standard_deviation": point[controls, j].std(ddof=1)})
    for name, rows in (("paired_comparisons.csv", comparison_rows), ("metric_intervals.csv", interval_rows),
                       ("control_summary.csv", c_rows), ("bootstrap_coverage.csv", coverage_rows)):
        save_csv(pd.DataFrame(rows), output / name)
    save_csv(pd.concat(sample_frames, ignore_index=True), output / "bootstrap_replicates.csv.gz")
    write_report(directory, output, manifest)
    write_json(output / "manifest.json", {
        "status": "completed", "finished_at_utc": utc_now(), "elapsed_seconds": time.perf_counter() - started,
        "pilot_manifest_sha256": sha256(directory / "manifest.json"), "source_sha256": sha256(Path(__file__)),
        "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scipy")},
        "rng": type(rng.bit_generator).__name__, "model_order": keys,
        "replicates": REPLICATES, "seed": SEED, "subgroup_order": list(masks), "metrics": METRICS,
        "unit": "group_id; all rows retained per sampled group; shared draws across 14 refit predictions",
        "interval": "paired percentile 95%; missing-class draws excluded and counted, not replaced",
        "artifacts_sha256": {p.name: sha256(p) for p in sorted(output.iterdir())}})
    print("Analysis completed; no additional fits.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=OUTPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    analyze(args.directory.resolve(), (args.output or args.directory / "analysis").resolve())

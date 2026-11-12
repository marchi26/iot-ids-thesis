"""Describe saved pilot errors by class and group, without fitting models."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from audit_ton_iot_split import ROOT, git, require, sha256
from run_overlap_pilot import CONFIGURATIONS, MODEL_NAMES, OUTPUT, utc_now, write_json

DESTINATION = OUTPUT.parent.parent / "error_analysis/results"
IDENTITY = ["row_id", "group_id", "y_true", "exposed_to_A"]
TRANSITIONS = ["correct_to_correct", "correct_to_wrong", "wrong_to_correct",
               "wrong_to_same_wrong", "wrong_to_other_wrong"]


def snapshot(directory):
    return {p.relative_to(directory).as_posix(): sha256(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def validate_pair(reference, candidate, classes):
    for frame in (reference, candidate):
        require(set(IDENTITY + ["y_pred"]) <= set(frame.columns), "Missing prediction columns")
        require(not frame[IDENTITY + ["y_pred"]].isna().any().any(), "Missing prediction values")
        require(frame.row_id.is_unique, "Duplicate row_id")
        require(set(frame.y_true) <= set(classes) and set(frame.y_pred) <= set(classes), "Unknown label")
        require(frame.exposed_to_A.dtype == bool, "Exposure must be boolean")
        require(frame.groupby("group_id").exposed_to_A.nunique().max() == 1, "Exposure splits a group")
    require(reference[IDENTITY].equals(candidate[IDENTITY]), "Prediction identities/order differ")


def class_metrics(frame, classes):
    precision, recall, f1, support = precision_recall_fscore_support(
        frame.y_true, frame.y_pred, labels=classes, zero_division=0)
    rows = []
    for index, label in enumerate(classes):
        truth, predicted = frame.y_true.eq(label), frame.y_pred.eq(label)
        tp = int((truth & predicted).sum())
        rows.append({"class": label, "rows": int(support[index]),
                     "groups": int(frame.loc[truth, "group_id"].nunique()),
                     "tp": tp, "fp": int((~truth & predicted).sum()),
                     "fn": int((truth & ~predicted).sum()),
                     "precision": precision[index], "recall": recall[index], "f1": f1[index]})
    return pd.DataFrame(rows).set_index("class")


def paired_transitions(reference, candidate):
    correct_a = reference.y_pred.eq(reference.y_true).to_numpy()
    correct_target = candidate.y_pred.eq(candidate.y_true).to_numpy()
    same = reference.y_pred.to_numpy() == candidate.y_pred.to_numpy()
    conditions = [correct_a & correct_target, correct_a & ~correct_target,
                  ~correct_a & correct_target, ~correct_a & ~correct_target & same,
                  ~correct_a & ~correct_target & ~same]
    require(np.all(np.stack(conditions).sum(axis=0) == 1), "Incomplete transition partition")
    result = reference[["row_id", "group_id", "y_true"]].copy()
    result["prediction_A"] = reference.y_pred.to_numpy()
    result["prediction_target"] = candidate.y_pred.to_numpy()
    result["transition"] = np.select(conditions, TRANSITIONS, default="invalid")
    return result


def compare(reference, candidate, classes, metadata):
    before, after = class_metrics(reference, classes), class_metrics(candidate, classes)
    transitions = paired_transitions(reference, candidate)
    changes, totals = [], []
    for label in classes:
        a, b = before.loc[label], after.loc[label]
        change = {**metadata, "class": label, "rows": int(a.rows), "groups": int(a.groups)}
        for metric in ("tp", "fp", "fn", "precision", "recall", "f1"):
            change[f"{metric}_A"] = a[metric]
            change[f"{metric}_target"] = b[metric]
            change[f"delta_{metric}"] = b[metric] - a[metric]
        change["macro_f1_contribution_pp"] = 100 * change["delta_f1"] / len(classes)
        changes.append(change)
        selected = transitions[transitions.y_true == label]
        counts = {}
        for name in TRANSITIONS:
            part = selected[selected.transition == name]
            counts[name] = len(part)
            totals.append({**metadata, "class": label, "transition": name,
                           "rows": len(part), "groups": int(part.group_id.nunique())})
        require(sum(counts.values()) == int(a.rows), "Transition support mismatch")
        require(counts["correct_to_wrong"] - counts["wrong_to_correct"] == b.fn - a.fn,
                "Transition/error delta mismatch")
    destinations = transitions.groupby(
        ["y_true", "prediction_A", "prediction_target", "transition"], sort=True).agg(
            rows=("row_id", "size"), groups=("group_id", "nunique")).reset_index()
    destinations = destinations.rename(columns={"y_true": "class"})
    for key, value in metadata.items():
        destinations[key] = value
    require(destinations.rows.sum() == len(reference), "Destination support mismatch")
    np.testing.assert_allclose(sum(item["macro_f1_contribution_pp"] for item in changes),
                               100 * (after.f1.mean() - before.f1.mean()), atol=1e-12)
    return changes, totals, destinations


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
                     + ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def write_report(output, changes, transitions, destinations, pilot_commit):
    rf = changes[(changes.model == "random_forest") & (changes.subgroup == "exposed")]
    b = rf[rf.configuration == "fixed_B"].set_index("class")
    controls = rf[rf.configuration != "fixed_B"]
    rare = ["injection", "ddos", "mitm"]
    total_delta = b.macro_f1_contribution_pp.sum()
    rare_delta = b.loc[rare, "macro_f1_contribution_pp"].sum()
    share = f"{100 * rare_delta / total_delta:.2f}%" if total_delta != 0 else "non definita"
    class_rows = []
    for label, row in b.iterrows():
        c = controls[controls["class"] == label].f1_target
        class_rows.append([label, int(row.rows), int(row.groups), f"{row.f1_A:.4f}",
                           f"{row.f1_target:.4f}", f"{c.mean():.4f} [{c.min():.4f}; {c.max():.4f}]",
                           f"{100 * row.delta_f1:+.2f}", f"{100 * (row.f1_target - c.mean()):+.2f}"])
    transition_rows = []
    selected = transitions[(transitions.model == "random_forest") & (transitions.subgroup == "exposed")]
    for label in rare:
        for configuration in CONFIGURATIONS[1:]:
            block = selected[(selected["class"] == label) & (selected.configuration == configuration)].set_index("transition")
            transition_rows.append([label, configuration.removeprefix("fixed_"),
                                    *[f"{int(block.loc[name, 'rows'])}/{int(block.loc[name, 'groups'])}"
                                      for name in TRANSITIONS]])
    details = destinations[(destinations.model == "random_forest") & (destinations.subgroup == "exposed")
                           & (destinations.configuration == "fixed_B") & destinations["class"].isin(rare)
                           & (destinations.transition != "correct_to_correct")]
    detail_rows = [
        [row["class"], row["prediction_A"], row["prediction_target"], row["rows"], row["groups"]]
        for row in details.to_dict("records")]
    lr = changes[(changes.model == "logistic_regression") & (changes.subgroup == "all")
                 & (changes["class"] == "normal")].set_index("configuration")
    # For normal-vs-attack detection, normal-class FN are false alarms and FP are missed attacks.
    target = lr.loc["fixed_B"]
    c = lr.loc[CONFIGURATIONS[2:]]
    text = f"""# SPLIT-02: approfondimento degli errori del pilota

## Ambito

Questa lettura descrittiva aggiuntiva risponde alla richiesta del relatore successiva alla validazione del pilota `{pilot_commit[:7]}`. Non fa parte dell'analisi bootstrap inizialmente prevista. Utilizza soltanto le predizioni dei 14 refit sul test fisso; nessun nuovo addestramento, ricampionamento o selezione di parametri. Gli artefatti del pilota e la relazione precedente rimangono invariati.

Le tabelle complete coprono LR e RF, tutte le dieci classi e i sottogruppi complessivo, esposto e non esposto. L'esposizione resta quella definita rispetto ad A. Ogni confronto usa le stesse righe, nello stesso ordine, con identici `row_id`, `group_id` ed etichette. I cinque C sono mantenuti distinti nei CSV; le medie riassumono cinque modelli, non un classificatore ottenuto combinandone le predizioni.

## RF: classi nel sottogruppo esposto

F1 assume valori tra 0 e 1; le differenze sono in punti percentuali (pp). Per C sono riportate media e intervallo minimo-massimo dei cinque controlli, non un intervallo di confidenza. I supporti si riferiscono alla classe vera. Precision e F1 includono anche i falsi positivi provenienti dalle altre classi dello stesso sottogruppo.

{table(['Classe', 'Righe', 'Gruppi', 'F1 A', 'F1 B', 'F1 C: media [min; max]', 'B-A (pp)', 'B-media C (pp)'], class_rows)}

La differenza di Macro-F1 B-A nel sottogruppo esposto di RF è {total_delta:+.4f} pp. Il contributo di ciascuna classe è la sua differenza di F1 divisa per dieci, poiché la Macro-F1 assegna lo stesso peso a tutte le classi. `injection`, `ddos` e `mitm` contribuiscono insieme per {rare_delta:+.4f} pp, pari al {share} della diminuzione netta. Si tratta di una scomposizione aritmetica, non di una stima causale: il peso elevato non implica un numero elevato di errori.

## Transizioni appaiate rispetto ad A

Ogni cella riporta **righe/gruppi distinti**. Le colonne distinguono corretti rimasti corretti, corretti diventati errati, errori corretti, errori rimasti sulla stessa classe sbagliata ed errori passati a un'altra classe sbagliata. Sono inclusi tutti i controlli C, non soltanto la loro media.

{table(['Classe vera', 'Destinazione', 'Corretto-corretto', 'Corretto-errato', 'Errato-corretto', 'Stesso errore', 'Errore diverso'], transition_rows)}

Per A-B, le destinazioni degli errori nelle tre classi sono:

{table(['Classe vera', 'Predizione A', 'Predizione B', 'Righe', 'Gruppi'], detail_rows)}

I conteggi delle righe nelle cinque categorie sono disgiunti e sommano al supporto della classe. I gruppi sono conteggiati distintamente in ogni cella: in presenza di etichette discordanti, lo stesso gruppo può comparire in più classi o categorie, quindi i conteggi dei gruppi non devono essere sommati come se fossero indipendenti. Un gruppo corrisponde alla definizione congelata basata sulle feature, non necessariamente a un dispositivo o a una sessione.

## Compromesso fra falsi allarmi e attacchi mancati

Sul test complessivo, per LR i normali classificati come attacco passano da {int(target.fn_A)} in A a {int(target.fn_target)} in B; nei cinque C variano da {int(c.fn_target.min())} a {int(c.fn_target.max())}. Gli attacchi classificati come normali passano da {int(target.fp_A)} a {int(target.fp_target)}; nei C variano da {int(c.fp_target.min())} a {int(c.fp_target.max())}. Questi conteggi riguardano la distinzione normale/attacco, non tutti gli errori fra tipi di attacco. Nei CSV `fp` e `fn` adottano invece la convenzione uno-contro-tutti per ciascuna classe: per la classe `normal` i ruoli sono quindi invertiti rispetto alla rilevazione degli attacchi.

## Limiti e verifica

I piccoli supporti delle classi rare rendono rilevante anche il cambiamento di poche predizioni. La Macro-F1 complessiva e quella del sottogruppo esposto non sono intercambiabili. I controlli C pareggiano la numerosità per classe del pool B, ma non la distribuzione delle feature; non isolano ogni possibile spiegazione delle differenze osservate. Questa analisi non aggiunge test di significatività né modifica gli intervalli già pubblicati. Il confronto random/group-disjoint resta rinviato.

`class_changes.csv` conserva supporti, precision, recall, F1, TP/FP/FN e contributi alla differenza di Macro-F1 per A-B e A-ciascun C. `error_transitions.csv` conserva le cinque categorie appaiate, comprese quelle con conteggio zero. `prediction_transitions.csv` dettaglia le classi predette in A e nella configurazione confrontata. Le metriche sono ricalcolate dalle predizioni e confrontate con i CSV originali; i conteggi delle transizioni sono verificati rispetto ai supporti e alle variazioni degli errori. `manifest.json` identifica input, script, ambiente e controlli eseguiti.
"""
    (output / "report.md").write_text(text, encoding="utf-8", newline="\n")


def analyze(directory, output):
    require(not output.exists(), f"Output already exists: {output}")
    require(not output.is_relative_to(directory.parent), "Keep additional analysis outside the pilot directory")
    started = utc_now()
    preserved = snapshot(directory.parent)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["status"] == "completed" and manifest["completed_fits"] == 28, "Pilot not complete")
    for name, expected in manifest["artifacts_sha256"].items():
        require(sha256(directory / name) == expected, f"Pilot artifact changed: {name}")
    classes = manifest["classes"]
    saved = pd.read_csv(directory / "per_class_metrics.csv")
    changes, totals, destinations = [], [], []
    reference = None
    metric_checks = 0
    for model in MODEL_NAMES:
        frames = {}
        for configuration in CONFIGURATIONS:
            frame = pd.read_csv(directory / "fits" / f"refit__{configuration}__{model}" / "predictions.csv.gz")
            reference = frame if reference is None else reference
            validate_pair(reference, frame, classes)
            frames[configuration] = frame
        masks = {"all": np.ones(len(reference), dtype=bool),
                 "exposed": reference.exposed_to_A.to_numpy(), "non_exposed": ~reference.exposed_to_A.to_numpy()}
        for subgroup, mask in masks.items():
            for configuration, frame in frames.items():
                recomputed = class_metrics(frame.loc[mask], classes)
                original = saved[(saved.phase == "refit") & (saved.model == model)
                                 & (saved.configuration == configuration) & (saved.subgroup == subgroup)].set_index("class").loc[classes]
                np.testing.assert_allclose(recomputed[["precision", "recall", "f1", "rows"]],
                                           original[["precision", "recall", "f1", "support"]], atol=1e-12, rtol=1e-12)
                metric_checks += 1
            for configuration in CONFIGURATIONS[1:]:
                metadata = {"model": model, "subgroup": subgroup, "configuration": configuration}
                rows, counts, detail = compare(frames["fixed_A"].loc[mask], frames[configuration].loc[mask], classes, metadata)
                changes.extend(rows)
                totals.extend(counts)
                destinations.append(detail)
    require(snapshot(directory.parent) == preserved, "Pilot files changed during analysis")
    output.mkdir(parents=True)
    changes, totals, destinations = pd.DataFrame(changes), pd.DataFrame(totals), pd.concat(destinations, ignore_index=True)
    for name, frame in [("class_changes.csv", changes), ("error_transitions.csv", totals),
                        ("prediction_transitions.csv", destinations)]:
        frame.to_csv(output / name, index=False, lineterminator="\n")
    pilot_commit = git("log", "-1", "--format=%H", "--", str(directory / "manifest.json"))
    write_report(output, changes, totals, destinations, pilot_commit)
    require(snapshot(directory.parent) == preserved, "Pilot files changed during output generation")
    source = Path(__file__)
    write_json(output / "manifest.json", {
        "stage": "SPLIT-02 additional descriptive error analysis after pilot validation",
        "status": "completed", "started_at_utc": started, "finished_at_utc": utc_now(),
        "execution_commit": git("rev-parse", "HEAD"), "pilot_delivery_commit": pilot_commit,
        "working_tree_status": git("status", "--short"), "training_executed": False,
        "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scikit-learn")},
        "source": source.relative_to(ROOT).as_posix(), "source_sha256": sha256(source),
        "source_sha256_lf": hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "pilot_manifest_sha256": sha256(directory / "manifest.json"),
        "pilot_files_sha256": preserved, "pilot_files_unchanged": True,
        "checks": {"paired_prediction_files": 14, "class_metric_sets_recomputed": metric_checks,
                   "comparison_sets": 36, "class_change_rows": len(changes),
                   "transition_rows": len(totals), "destination_rows": len(destinations),
                   "transition_counts_and_macro_f1_decomposition": "PASS"},
        "artifacts_sha256": snapshot(output)})
    print(f"PASS: {metric_checks} class metric sets; {len(changes)} class comparisons. Pilot unchanged. Output: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=OUTPUT)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    analyze(args.directory.resolve(), args.output.resolve())

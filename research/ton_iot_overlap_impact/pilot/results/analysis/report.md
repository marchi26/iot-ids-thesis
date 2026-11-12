# SPLIT-02: risultati del pilota multiclasse a test fisso

## Ambito ed esecuzione

Sono stati eseguiti i 28 fit autorizzati: 14 diagnostici sul training interno, valutati sulla validazione, e 14 refit sull'intero pool, valutati sul test. Le sette configurazioni sono A, B e i cinque controlli C. Il confronto casuale/a gruppi non è stato avviato. Nessuna scelta di parametri è stata effettuata usando i risultati di validazione o test.

Inizio registrato: `2026-10-27T14:55:53.521918+00:00`; fine: `2026-10-27T15:18:41.254799+00:00`. Il tempo complessivo, inclusi i controlli preliminari, è 1396.40 secondi. Il commit di base è `af97421af53f0418e9c51c2435aad6eddef54ef0`; i nuovi script non erano committati e sono identificati dagli hash del manifest.

Il CSV congelato contiene 211.043 righe. Il test è lo stesso in tutti i confronti: 42.209 righe, di cui 6.963 esposte al pool A e 35.246 non esposte. A contiene 168.834 righe nel pool; B e ciascun C ne contengono 152.502. I cinque C rimuovono lo stesso numero di righe di B per ciascuna classe, usando i semi 601, 701, 809, 907 e 1009.

LR usa `C=1`, `solver=lbfgs`, `max_iter=3000`; RF usa 200 alberi, profondità non limitata, `min_samples_leaf=1` e `n_jobs=1`. Entrambi usano seme 1103 e nessuna ponderazione delle classi. Non sono applicati SMOTE o tuning. Le 32 feature e i ruoli numerici/categorici sono quelli congelati; ogni fit apprende imputazione, scala e categorie soltanto dal proprio training. Le librerie numeriche operano con un thread.

## Risultati sul test

I valori sono proporzioni, non percentuali. Macro F1 considera tutte le dieci classi; balanced accuracy è la media dei recall delle classi presenti. FPR indica i normali classificati come attacco, FNR gli attacchi classificati come normali. Le tabelle riguardano i refit; i risultati diagnostici restano separati nei CSV.

| Modello | Configurazione | Macro F1 | Balanced accuracy | FPR | FNR |
|---|---|---|---|---|---|
| LR | A | 0.7766 | 0.7708 | 0.0814 | 0.0200 |
| RF | A | 0.9628 | 0.9685 | 0.0024 | 0.0010 |
| LR | B | 0.7754 | 0.7764 | 0.1493 | 0.0045 |
| RF | B | 0.9633 | 0.9681 | 0.0029 | 0.0022 |
| LR | C_601 | 0.7733 | 0.7678 | 0.0811 | 0.0210 |
| RF | C_601 | 0.9640 | 0.9711 | 0.0026 | 0.0009 |
| LR | C_701 | 0.7719 | 0.7665 | 0.0810 | 0.0207 |
| RF | C_701 | 0.9635 | 0.9707 | 0.0024 | 0.0011 |
| LR | C_809 | 0.7721 | 0.7667 | 0.0810 | 0.0207 |
| RF | C_809 | 0.9641 | 0.9712 | 0.0028 | 0.0011 |
| LR | C_907 | 0.7750 | 0.7694 | 0.0811 | 0.0207 |
| RF | C_907 | 0.9653 | 0.9731 | 0.0025 | 0.0011 |
| LR | C_1009 | 0.7731 | 0.7676 | 0.0813 | 0.0209 |
| RF | C_1009 | 0.9635 | 0.9702 | 0.0030 | 0.0009 |

## Confronti appaiati e sottogruppi

Differenze di Macro F1 in punti percentuali, con intervalli percentili al 95% ottenuti da 2.000 ricampionamenti per gruppo, seme 1301. Ogni replica usa gli stessi gruppi per tutti i modelli confrontati. I sottogruppi restano definiti rispetto ad A anche quando si valuta B o C. Gli intervalli sono condizionati ai modelli addestrati e al test disponibile, non descrivono la variabilità di nuovi training. Non è applicata una correzione per confronti multipli; gli intervalli hanno funzione descrittiva.

| Modello | Sottogruppo | Contrasto | Differenza (pp) | IC 95% (pp) | Repliche valide |
|---|---|---|---|---|---|
| LR | all | B_minus_A | -0.1186 | [-2.1570, 1.1561] | 2000 |
| LR | all | B_minus_mean_C | 0.2368 | [-1.8063, 1.5684] | 2000 |
| RF | all | B_minus_A | 0.0446 | [-0.2058, 0.2873] | 2000 |
| RF | all | B_minus_mean_C | -0.0777 | [-0.2735, 0.0935] | 2000 |
| LR | exposed | B_minus_A | -2.9890 | [-9.0454, 6.5900] | 1698 |
| LR | exposed | B_minus_mean_C | -2.8026 | [-8.8448, 6.7058] | 1698 |
| RF | exposed | B_minus_A | -17.0242 | [-26.4506, -10.8351] | 1698 |
| RF | exposed | B_minus_mean_C | -16.4513 | [-25.9257, -10.0083] | 1698 |
| LR | non_exposed | B_minus_A | 0.3079 | [0.0595, 0.5607] | 2000 |
| LR | non_exposed | B_minus_mean_C | 0.6906 | [0.3519, 1.0509] | 2000 |
| RF | non_exposed | B_minus_A | 0.1879 | [-0.0218, 0.4133] | 2000 |
| RF | non_exposed | B_minus_mean_C | 0.0648 | [-0.0847, 0.2168] | 2000 |

Le repliche prive di una classe presente nel sottogruppo originale sono conteggiate ed escluse dagli intervalli, senza estrazioni sostitutive. I conteggi di tali repliche sono: all: 0, exposed: 302, non_exposed: 0. Gli intervalli risultano quindi condizionati anche alla presenza delle classi; una quota elevata di esclusioni ne limita l'interpretazione, soprattutto per le classi rare. Eventuali tassi senza denominatore restano non definiti. I confronti con ogni singolo C, le altre metriche e la deviazione standard fra i cinque controlli sono conservati nei CSV; quest'ultima non è un intervallo di confidenza.

Per LR, la differenza di Macro F1 B meno A è -0.1186 punti percentuali; B meno la media dei cinque C è +0.2368 punti. Il secondo contrasto confronta pool con uguale numerosità per classe, ma non con uguale distribuzione delle feature. Per RF, la differenza di Macro F1 B meno A è +0.0446 punti percentuali; B meno la media dei cinque C è -0.0777 punti. Il secondo contrasto confronta pool con uguale numerosità per classe, ma non con uguale distribuzione delle feature.

## Recall per classe

La colonna C riporta la media dei cinque controlli. Supporti e osservazioni del test non cambiano fra configurazioni. Precision, F1 e matrici di confusione complete, anche per i sottogruppi, sono disponibili nei file allegati.

| Classe | LR A | LR B | LR media C | RF A | RF B | RF media C | Supporto |
|---|---|---|---|---|---|---|---|
| backdoor | 0.9985 | 0.9985 | 0.9985 | 0.9992 | 0.9992 | 0.9994 | 4000 |
| ddos | 0.9038 | 0.9040 | 0.9038 | 0.9800 | 0.9802 | 0.9811 | 4000 |
| dos | 0.9445 | 0.9443 | 0.9439 | 0.9800 | 0.9802 | 0.9780 | 4000 |
| injection | 0.7110 | 0.6963 | 0.7068 | 0.9715 | 0.9683 | 0.9719 | 4000 |
| mitm | 0.2679 | 0.2679 | 0.2679 | 0.7943 | 0.8038 | 0.8239 | 209 |
| normal | 0.9186 | 0.8507 | 0.9189 | 0.9976 | 0.9971 | 0.9973 | 10000 |
| password | 0.5610 | 0.5583 | 0.5565 | 0.9925 | 0.9925 | 0.9926 | 4000 |
| ransomware | 0.7748 | 0.9293 | 0.7497 | 0.9990 | 0.9892 | 0.9990 | 4000 |
| scanning | 0.7630 | 0.7455 | 0.7700 | 0.9885 | 0.9898 | 0.9900 | 4000 |
| xss | 0.8650 | 0.8698 | 0.8601 | 0.9822 | 0.9810 | 0.9796 | 4000 |

## Tempi e problemi osservati

| Modello | Fit | Training totale (s) | Preprocessing fit (s) | Inferenza (s) |
|---|---|---|---|---|
| LR | 14 | 774.12 | 25.34 | 0.26 |
| RF | 14 | 464.99 | 27.47 | 12.10 |

L'inferenza comprende il calcolo delle probabilità e la scelta della classe; la trasformazione delle feature di valutazione è registrata separatamente in `timings.csv`. I tempi dipendono dalla macchina e dal carico durante l'esecuzione. Non sono stati registrati avvisi di convergenza. Gli avvisi completi sono conservati in `warnings.csv`; non sono stati effettuati tentativi automatici con parametri alternativi.

## Limiti e materiali

B usa le feature del test per definire un intervento diagnostico: non rappresenta una stima cieca del deployment. C controlla quantità e distribuzione delle etichette, non le caratteristiche dei flussi rimossi. Gli effetti osservati riguardano questo campione, queste definizioni di gruppo e questi due modelli; non autorizzano a correggere retroattivamente le metriche della tesi né a dedurre una validità generale per altri dataset. I gruppi con etichette discordanti sono mantenuti.

Le predizioni con `row_id`, `group_id`, etichetta e probabilità sono in `../fits/`. I risultati completi sono in `../metrics.csv`, `../per_class_metrics.csv`, `../confusion_matrices.csv` e `../timings.csv`. In questa cartella si trovano confronti appaiati, intervalli, riepilogo dei controlli e repliche del bootstrap. Il verificatore `scripts/verify_overlap_pilot.py` ricalcola le metriche dalle predizioni e controlla i confronti senza nuovi fit; il suo esito, quando eseguito con `--save`, è salvato separatamente in `../pilot_validation.json`.

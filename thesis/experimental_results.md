# Risultati sperimentali

Gli esperimenti sono stati eseguiti sul dataset TON_IoT Network Dataset scaricato da Kaggle e collocato in `data/raw/train_test_network.csv`. I valori riportati in questo documento derivano dai file CSV generati nella directory `results/metrics/`; non sono stati inseriti risultati manuali o stimati.

## Baseline per classificazione binaria

| Modello | Accuracy | F1-score | Macro F1 | Tempo addestramento (s) | Tempo inferenza (s) |
|---|---:|---:|---:|---:|---:|
| Random Forest | 0.9988 | 0.9992 | 0.9983 | 24.43 | 0.283 |
| LightGBM | 0.9992 | 0.9995 | 0.9989 | 3.50 | 0.215 |
| XGBoost | 0.9988 | 0.9992 | 0.9983 | 5.46 | 0.066 |
| Logistic Regression | 0.9576 | 0.9722 | 0.9414 | 5.72 | 0.008 |

Nella classificazione binaria, LightGBM ha ottenuto la migliore accuracy e il migliore F1-score tra i modelli baseline. Random Forest e XGBoost hanno mostrato prestazioni molto vicine. Logistic Regression ha ottenuto metriche inferiori, pur mantenendo un tempo di inferenza molto contenuto.

## Baseline per classificazione multiclasse

| Modello | Accuracy | F1-score weighted | Macro F1 | Tempo addestramento (s) | Tempo inferenza (s) |
|---|---:|---:|---:|---:|---:|
| Random Forest | 0.9883 | 0.9884 | 0.9654 | 23.63 | 0.539 |
| LightGBM | 0.9897 | 0.9898 | 0.9678 | 26.82 | 2.422 |
| XGBoost | 0.9891 | 0.9893 | 0.9655 | 58.96 | 0.557 |
| Logistic Regression | 0.8263 | 0.8330 | 0.7686 | 211.00 | 0.022 |

Anche nella classificazione multiclasse, LightGBM ha ottenuto la migliore accuracy e il valore più elevato di Macro F1 tra i modelli baseline. XGBoost e Random Forest hanno avuto prestazioni simili, mentre Logistic Regression è risultata meno efficace sul problema multiclasse.

## Bilanciamento con SMOTE

Gli esperimenti con SMOTE sono stati applicati esclusivamente al training set. Nel caso binario, Random Forest senza SMOTE ha ottenuto Macro F1 pari a 0.9974, mentre Random Forest con SMOTE ha ottenuto Macro F1 pari a 0.9969. Per Logistic Regression il Macro F1 è passato da 0.9408 senza SMOTE a 0.9410 con SMOTE, con una variazione molto limitata.

Nel caso multiclasse, LightGBM con SMOTE ha ottenuto Macro F1 pari a 0.9528, mentre LightGBM senza SMOTE ha ottenuto Macro F1 pari a 0.9524. La differenza è ridotta e non consente di affermare un miglioramento sistematico dovuto al bilanciamento. I risultati indicano che l'effetto di SMOTE dipende dal modello e dalla modalità di classificazione.

## Tuning iperparametrico

Il tuning è stato rieseguito con 6 iterazioni e 3 fold di cross-validation, utilizzando un campione stratificato del training set per contenere il tempo computazionale. Nel caso binario, LightGBM ha ottenuto Macro F1 pari a 0.9979, Random Forest 0.9974 e XGBoost 0.9972. Nel caso multiclasse, Random Forest ha ottenuto Macro F1 pari a 0.9528, LightGBM 0.9523 e XGBoost 0.9482.

Questi risultati non mostrano un miglioramento netto rispetto alla baseline completa. Il confronto deve essere interpretato con cautela, perché la baseline è addestrata sull'intero training set, mentre il tuning utilizza un campione stratificato per ragioni computazionali. Il risultato è comunque utile per documentare il protocollo di ricerca degli iperparametri e i limiti della sperimentazione locale.

## Modelli aggiuntivi

MLPClassifier ha ottenuto Macro F1 pari a 0.9899 nella classificazione binaria e 0.8851 nella classificazione multiclasse. Durante l'esecuzione multiclasse è stato prodotto un warning di convergenza, perché l'ottimizzatore ha raggiunto il numero massimo di iterazioni configurato. Il risultato va quindi considerato preliminare.

Isolation Forest è stato valutato solo nella classificazione binaria, come modello non supervisionato di anomaly detection. Ha ottenuto Macro F1 pari a 0.3625, sensibilmente inferiore rispetto ai modelli supervisionati. Questo risultato è coerente con la diversa impostazione metodologica: il modello è addestrato sui soli campioni normali e non utilizza direttamente le etichette di attacco durante l'addestramento.

## Interpretabilità, latenza e compressione

È stata aggiunta un'analisi di interpretabilità del modello ensemble selezionato. In questo ambiente SHAP non è stato installato in tempi accettabili; il runner `run_interpretability.py` è comunque predisposto per usare SHAP quando disponibile e, in assenza della libreria, produce un'analisi basata sulle feature importance del modello. Nel caso binario, le feature con maggiore importanza normalizzata per LightGBM includono `src_port`, `src_ip_bytes`, `duration`, `src_bytes` e `src_pkts`.

È stata inoltre generata una prima analisi di deployment tramite serializzazione e compressione Joblib del modello LightGBM selezionato. Nel caso binario, l'artefatto è passato da 2.09 MB a 0.85 MB, con rapporto di compressione pari a 0.41. Nel caso multiclasse, l'artefatto è passato da 17.20 MB a 7.34 MB, con rapporto di compressione pari a 0.43. Questi dati non equivalgono a una quantizzazione per microcontrollori, ma forniscono una prima misura utile per discutere dimensione del modello e latenza.

## Dimostratore embedded per Wokwi

È stato aggiunto un exporter dedicato al deployment embedded, `src/experiments/export_embedded_model.py`. Lo script addestra una Logistic Regression binaria compatta su dieci feature numeriche e genera il file C++ `wokwi/ids_esp32/include/embedded_model.h`, contenente coefficienti quantizzati, parametri di normalizzazione e campioni di test.

Il modello embedded ha ottenuto accuracy pari a 0.8180, F1-score pari a 0.8888 e Macro F1 pari a 0.6933. Questi valori sono inferiori rispetto alla baseline LightGBM, ma il confronto non deve essere interpretato come competizione diretta: il modello embedded è progettato per dimostrare il passaggio verso firmware ESP32/Wokwi con risorse ridotte.

Il progetto Wokwi è stato predisposto in `wokwi/ids_esp32/`, con firmware Arduino/PlatformIO, circuito `diagram.json` e due LED per indicare classificazioni normali o di attacco. In questo ambiente non sono stati installati PlatformIO e Wokwi CLI in tempi accettabili; pertanto la compilazione firmware e la registrazione della simulazione Wokwi restano da eseguire localmente con gli strumenti dedicati.

La variante browser è disponibile come progetto Wokwi all'indirizzo `https://wokwi.com/projects/472799587810026497` ed è stata esportata nella directory `wokwi/browser_esp32/`. La registrazione video della simulazione è stata prodotta esternamente e non viene inclusa nel repository per evitare di versionare file multimediali pesanti.

## File generati

I principali output sperimentali sono:

- `results/metrics/binary_baseline_metrics.csv`;
- `results/metrics/multiclass_baseline_metrics.csv`;
- `results/metrics/binary_extended_metrics.csv`;
- `results/metrics/multiclass_extended_metrics.csv`;
- `results/metrics/smote_comparison.csv`;
- `results/metrics/hyperparameter_tuning_results.csv`;
- `results/metrics/per_class_summary.csv`;
- `results/metrics/latency_summary.csv`;
- `results/metrics/deployment_analysis.csv`;
- `results/metrics/embedded_logistic_regression_metrics.csv`;
- `results/metrics/interpretability_feature_importance.csv`;
- grafici PNG nella directory `results/plots/`.

Le matrici di confusione e i report di classificazione per singolo modello sono stati salvati nella directory `results/metrics/`.

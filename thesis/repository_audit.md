# Audit del repository di riferimento

## Scopo del repository originale

Il repository originale `KuznetsovKarazin/iot-audit` implementa una pipeline di machine learning per sistemi di Intrusion Detection applicati a traffico IoT e IIoT. Il progetto supporta sia la classificazione binaria, finalizzata a distinguere traffico normale e traffico malevolo, sia la classificazione multiclasse, finalizzata a riconoscere differenti tipologie di attacco.

## Dataset utilizzato

Il repository fa riferimento al dataset TON_IoT Network Dataset, prodotto nell'ambito delle risorse UNSW. La pipeline si aspetta un file CSV denominato `train_test_network.csv`, collocato nel percorso `data/train_test_network.csv` nel progetto originale. Le colonne target principali sono `label`, usata per la classificazione binaria, e `type`, usata per la classificazione multiclasse.

## Modelli implementati

Il codice originale include script separati per l'addestramento dei seguenti modelli:

- Random Forest;
- LightGBM;
- XGBoost;
- Logistic Regression.

Sono presenti varianti per la classificazione binaria e per la classificazione multiclasse. Il repository contiene inoltre componenti sperimentali orientati alla distribuzione embedded e TinyML.

## Modalità di classificazione

La classificazione binaria utilizza la colonna `label`, normalizzando valori come `normal`, `benign`, `attack` e valori numerici. La classificazione multiclasse utilizza la colonna `type`, trasformando le etichette testuali in indici numerici.

## Metriche prodotte

Il repository originale produce metriche quali accuratezza, F1-score, ROC-AUC, PR-AUC, matrice di confusione e report per classe. Per la classificazione multiclasse sono presenti metriche macro e weighted, oltre a curve e report specifici per classe quando le probabilità predette sono disponibili.

## Struttura del codice

La struttura originale è organizzata in:

- `src/iot_audit/`, con moduli di preprocessing e metriche;
- `scripts/`, con script separati per ciascun modello e modalità sperimentale;
- `reports/` e `reports_mc/`, contenenti artefatti e risultati già generati;
- `ids_hw/`, con componenti per deployment su hardware embedded.

## Logica di preprocessing

Il preprocessing originale rimuove alcune colonne testuali ad alta cardinalità, gestisce valori mancanti con imputazione, codifica variabili categoriche tramite one-hot encoding e applica una suddivisione stratificata train/test. Il codice presta attenzione ad alcune colonne potenzialmente soggette a leakage, ad esempio evitando di usare `type` nella classificazione binaria.

## Limiti individuati

La pipeline originale è funzionale, ma presenta alcuni limiti per un lavoro di tesi riproducibile:

- gli esperimenti sono distribuiti in molti script separati;
- la configurazione non è centralizzata in un unico file;
- i percorsi sono in parte specificati tramite argomenti script e convenzioni locali;
- i risultati già presenti nel repository possono essere confusi con risultati rigenerati localmente;
- non è presente una separazione esplicita tra documentazione di tesi, codice sorgente, dataset e artefatti sperimentali;
- le estensioni sperimentali richieste per questa tesi non sono raccolte in un unico flusso.

## Problemi di riproducibilità

Il principale problema di riproducibilità riguarda la disponibilità del dataset. Il dataset non è incluso nel repository e deve essere scaricato manualmente. Inoltre, la presenza di report già generati rende necessario distinguere chiaramente tra risultati storici del repository originale e risultati prodotti da una nuova esecuzione.

## Modifiche introdotte nel nuovo repository

Nel repository personale sono state introdotte le seguenti modifiche:

- struttura modulare con cartelle `config/`, `data/`, `src/`, `results/`, `thesis/` e `scripts/`;
- configurazione centralizzata in `config/config.yaml`;
- validazione esplicita della presenza del dataset;
- messaggi di errore chiari quando il dataset manca;
- preprocessing con fit degli encoder e degli scaler solo sul training set;
- supporto a SMOTE applicato esclusivamente al training set;
- runner unificati per esperimenti binari, multiclasse, estesi e completi;
- salvataggio coerente di metriche CSV e grafici PNG in `results/`;
- documentazione di tesi in italiano;
- simulazione IoT leggera basata su MQTT e Docker Compose.

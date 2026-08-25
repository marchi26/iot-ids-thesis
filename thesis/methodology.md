# Metodologia sperimentale

Il lavoro sperimentale utilizza il dataset TON_IoT Network Dataset, associato a scenari IoT e IIoT. La pipeline si concentra sul file `train_test_network.csv`, che deve essere collocato nella directory `data/raw/`. La colonna `label` è impiegata per la classificazione binaria, mentre la colonna `type` è impiegata per la classificazione multiclasse.

L'obiettivo sperimentale è valutare modelli di machine learning per il rilevamento di intrusioni in traffico IoT, confrontando prestazioni, tempi di addestramento e tempi di inferenza. La pipeline comprende una baseline e alcune estensioni sperimentali.

La strategia di preprocessing include imputazione dei valori mancanti, rimozione di colonne testuali ad alta cardinalità, codifica one-hot delle variabili categoriche e scaling delle variabili numeriche. Per evitare leakage, encoder e scaler sono addestrati esclusivamente sul training set e successivamente applicati al test set.

La suddivisione train/test è stratificata, con dimensione del test set pari al 20% e seed casuale fissato a 42. Questa scelta consente di mantenere la distribuzione delle classi in entrambe le partizioni e migliora la riproducibilità dell'esperimento.

La classificazione binaria distingue traffico normale e traffico di attacco. La classificazione multiclasse distingue le diverse categorie di traffico definite dalla colonna `type`. I modelli baseline sono Random Forest, LightGBM, XGBoost e Logistic Regression.

Le metriche di valutazione includono accuracy, precision, recall, F1-score, macro F1, weighted F1, matrice di confusione, tempo di addestramento e tempo di inferenza. Le estensioni sperimentali includono bilanciamento tramite SMOTE, tuning iperparametrico e modelli aggiuntivi come MLPClassifier e Isolation Forest. Le baseline principali sono addestrate sull'intero training set di 168.836 record e valutate su 42.209 record. Per contenere il costo computazionale, SMOTE, tuning e MLPClassifier utilizzano un campione stratificato di 30.000 record del rispettivo training set; il test set resta invariato e separato. Isolation Forest è addestrato soltanto sui 7.108 record normali presenti nel campione binario. Il tuning usa 6 configurazioni casuali e 3 fold. Le numerosità effettive sono registrate nelle colonne `training_samples` e `test_samples` dei CSV estesi.

Lo script `run_all.py` esegue le baseline binaria e multiclasse, gli esperimenti estesi e la generazione dei riepiloghi tabulari. Non esegue l'analisi SHAP, l'analisi di deployment/compressione, l'export del modello embedded o la simulazione MQTT/Wokwi, che dispongono di runner separati.

Per discutere il deployment su dispositivi IoT è stato introdotto un exporter embedded. Tale componente addestra un modello Logistic Regression binario compatto su dieci feature numeriche, quantizza coefficienti e intercetta in `int16` e genera un header C++ per ESP32/Wokwi. L'exporter valuta separatamente il modello Python in virgola mobile e un'emulazione Python della formula quantizzata sull'intero test set, rendendo esplicito l'impatto della quantizzazione. Questa fase è distinta dalla valutazione principale dei modelli baseline e ha finalità dimostrativa rispetto ai vincoli di memoria, latenza e portabilità.

I risultati sperimentali sono prodotti tramite esecuzione degli script. In assenza del dataset, la pipeline segnala chiaramente l'impossibilità di eseguire gli esperimenti.

# Metodologia sperimentale

Il lavoro sperimentale utilizza il dataset TON_IoT Network Dataset, associato a scenari IoT e IIoT. La pipeline si concentra sul file `train_test_network.csv`, che deve essere collocato nella directory `data/raw/`. La colonna `label` è impiegata per la classificazione binaria, mentre la colonna `type` è impiegata per la classificazione multiclasse.

L'obiettivo sperimentale è valutare modelli di machine learning per il rilevamento di intrusioni in traffico IoT, confrontando prestazioni, tempi di addestramento e tempi di inferenza. La pipeline comprende una baseline e alcune estensioni sperimentali.

La strategia di preprocessing include imputazione dei valori mancanti, rimozione di colonne testuali ad alta cardinalità, codifica one-hot delle variabili categoriche e scaling delle variabili numeriche. Per evitare leakage, encoder e scaler sono addestrati esclusivamente sul training set e successivamente applicati al test set.

La suddivisione train/test è stratificata, con dimensione del test set pari al 20% e seed casuale fissato a 42. Questa scelta consente di mantenere la distribuzione delle classi in entrambe le partizioni e migliora la riproducibilità dell'esperimento.

La classificazione binaria distingue traffico normale e traffico di attacco. La classificazione multiclasse distingue le diverse categorie di traffico definite dalla colonna `type`. I modelli baseline sono Random Forest, LightGBM, XGBoost e Logistic Regression.

Le metriche di valutazione includono accuracy, precision, recall, F1-score, macro F1, weighted F1, matrice di confusione, tempo di addestramento e tempo di inferenza. Le estensioni sperimentali includono bilanciamento tramite SMOTE, tuning iperparametrico e modelli aggiuntivi come MLPClassifier e Isolation Forest. Per contenere il tempo computazionale su una macchina locale, gli esperimenti estesi possono utilizzare un campione stratificato del training set, configurato in `config/config.yaml`; la valutazione finale resta eseguita sul test set mantenuto separato. Le baseline principali, invece, sono addestrate sull'intero training set.

Per discutere il deployment su dispositivi IoT è stato introdotto un exporter embedded. Tale componente addestra un modello Logistic Regression binario compatto su un sottoinsieme numerico di feature, quantizza i coefficienti e genera un header C++ per un progetto ESP32/Wokwi. Questa fase è distinta dalla valutazione principale dei modelli baseline e ha finalità dimostrativa rispetto ai vincoli di memoria, latenza e portabilità.

I risultati sperimentali sono prodotti tramite esecuzione degli script. In assenza del dataset, la pipeline segnala chiaramente l'impossibilità di eseguire gli esperimenti.

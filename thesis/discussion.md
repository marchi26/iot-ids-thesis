# Discussione e strategie di mitigazione

## Discussione metodologica

I risultati ottenuti indicano che i modelli supervisionati sono adatti al rilevamento di intrusioni nel dataset TON_IoT. La classificazione binaria ha raggiunto valori molto elevati con i modelli ensemble, mentre la classificazione multiclasse ha mostrato una maggiore complessità, soprattutto per i modelli lineari.

Le baseline sono state addestrate sull'intero training set. Gli esperimenti estesi, invece, sono stati configurati con un campione stratificato del training set per contenere il tempo computazionale su macchina locale. Questa scelta non modifica il test set, ma deve essere considerata nell'interpretazione dei risultati, soprattutto quando si confrontano baseline complete e tuning iperparametrico.

## Interpretazione dei risultati

Nella classificazione binaria, LightGBM ha ottenuto la migliore accuracy tra i modelli baseline, pari a 0.9992, e un F1-score pari a 0.9995. Random Forest e XGBoost hanno ottenuto risultati molto simili, entrambi con accuracy pari a 0.9988. Logistic Regression è risultata meno performante, con accuracy pari a 0.9576, ma ha mostrato un tempo di inferenza particolarmente basso.

Nella classificazione multiclasse, LightGBM ha ottenuto la migliore accuracy baseline, pari a 0.9897, e il valore più elevato di Macro F1, pari a 0.9678. XGBoost e Random Forest hanno ottenuto prestazioni vicine. Logistic Regression ha mostrato limiti più evidenti nel caso multiclasse, con Macro F1 pari a 0.7686.

Il confronto con SMOTE non mostra un miglioramento generalizzato. Nel caso binario, Random Forest senza SMOTE ha ottenuto Macro F1 pari a 0.9974, superiore al valore con SMOTE pari a 0.9969. Nel caso multiclasse, LightGBM con SMOTE ha mostrato un leggero incremento di Macro F1 rispetto alla versione senza SMOTE, ma la differenza è contenuta. Pertanto, non è possibile concludere che SMOTE migliori sistematicamente le prestazioni in questo scenario.

Il tuning iperparametrico, eseguito con 6 iterazioni e 3 fold, non ha prodotto un vantaggio netto rispetto alla baseline completa. Questo non dimostra l'inutilità del tuning, ma segnala che lo spazio di ricerca adottato è ancora limitato e che il campionamento del training set riduce la comparabilità diretta con la baseline. Una ricerca più ampia, eventualmente con Optuna, potrebbe essere valutata in una fase successiva.

MLPClassifier ha prodotto risultati inferiori rispetto ai migliori modelli ensemble, soprattutto nella classificazione multiclasse. Isolation Forest, essendo un metodo non supervisionato di anomaly detection, ha ottenuto prestazioni sensibilmente inferiori ai classificatori supervisionati nel caso binario.

## Interpretabilità e prestazioni

I modelli ensemble, in particolare LightGBM, Random Forest e XGBoost, offrono prestazioni elevate ma sono meno immediatamente interpretabili rispetto a Logistic Regression. In un contesto IoT reale, questo compromesso è rilevante: un IDS deve essere accurato, ma anche verificabile, manutenibile e compatibile con i vincoli operativi dell'infrastruttura.

È stata aggiunta una prima analisi di interpretabilità basata sulle importanze delle feature del modello LightGBM. Il runner è predisposto per SHAP quando la libreria è disponibile, mentre in questa esecuzione locale è stata usata l'importanza normalizzata esposta dal modello. Nel caso binario emergono feature legate a porte, durata della connessione e volume di byte/pacchetti; questa indicazione è utile per orientare un'analisi successiva, ma non sostituisce una spiegazione causale del traffico malevolo.

Logistic Regression è più interpretabile e veloce in inferenza, ma i risultati sperimentali mostrano una riduzione significativa delle prestazioni, soprattutto nel caso multiclasse. La scelta del modello deve quindi considerare il bilanciamento tra accuratezza, latenza, risorse disponibili e necessità di spiegabilità.

## Latenza, dimensione del modello e deployment

L'analisi di deployment basata su Joblib mostra che la compressione riduce in modo significativo la dimensione degli artefatti LightGBM: da 2.09 MB a 0.85 MB nel caso binario e da 17.20 MB a 7.34 MB nel caso multiclasse. Questa analisi è utile come primo passo verso una discussione sul deployment, ma non equivale a una quantizzazione per microcontrollori.

Per una valutazione più vicina a un ambiente embedded sarebbe necessario esportare il modello in un formato compatibile con il target, misurare memoria occupata, tempo di inferenza e consumo su un ambiente simulato o reale. L'eventuale uso di Wokwi o di dispositivi del laboratorio potrebbe estendere questa parte della tesi.

È stato predisposto un dimostratore Wokwi basato su ESP32 e su un modello Logistic Regression quantizzato. Questa scelta riduce la complessità rispetto ai modelli ensemble e consente di incorporare direttamente i coefficienti nel firmware. Le prestazioni sono inferiori rispetto alla baseline LightGBM, ma il risultato è utile per discutere il compromesso tra accuratezza, semplicità del modello e portabilità su dispositivi IoT.

La simulazione Wokwi deve essere considerata un passaggio intermedio: consente di verificare il comportamento del firmware e della logica di inferenza, ma non misura automaticamente consumo energetico, affidabilità in rete reale o prestazioni su hardware fisico.

## Limiti sperimentali

Il dataset TON_IoT rappresenta una base utile per la valutazione, ma rimane un dataset statico. In ambienti reali, il traffico IoT cambia nel tempo a causa di aggiornamenti firmware, modifiche di configurazione, nuovi dispositivi e variazioni nel comportamento degli utenti. Questo fenomeno può causare concept drift e ridurre l'efficacia di modelli addestrati su dati storici.

La simulazione MQTT inclusa nel repository ha finalità dimostrativa e non sostituisce il dataset reale. Essa consente di illustrare il processo di generazione e raccolta di messaggi IoT, ma non riproduce l'intera complessità del traffico di rete reale.

## Strategie di mitigazione

Le misure tecniche per migliorare la sicurezza degli ambienti IoT includono segmentazione della rete, principio del privilegio minimo, aggiornamenti firmware regolari, autenticazione forte, inventario dei dispositivi, monitoraggio del traffico, anomaly detection, logging centralizzato, alerting, principi zero trust e baseline di configurazione sicura.

Un IDS basato su machine learning dovrebbe essere integrato in un processo più ampio di gestione della sicurezza. Il modello deve essere periodicamente rivalutato, monitorato rispetto al drift dei dati e aggiornato quando cambiano dispositivi, protocolli o profili di traffico.

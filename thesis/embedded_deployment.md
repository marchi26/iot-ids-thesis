# Deployment embedded e simulazione Wokwi

Questa sezione documenta l'estensione orientata al deployment embedded del sistema IDS. L'obiettivo non è sostituire la pipeline sperimentale principale basata su TON_IoT e modelli ensemble, ma mostrare come un modello più compatto possa essere esportato e utilizzato in un contesto simulato di dispositivo IoT.

## Modello esportato

È stato introdotto lo script `src/experiments/export_embedded_model.py`, che addestra un modello Logistic Regression binario su un sottoinsieme numerico di feature del dataset TON_IoT. Il modello utilizza dieci feature: `src_port`, `dst_port`, `duration`, `src_bytes`, `dst_bytes`, `missed_bytes`, `src_pkts`, `src_ip_bytes`, `dst_pkts` e `dst_ip_bytes`.

La scelta di un modello lineare compatto è motivata dai vincoli tipici dei dispositivi embedded: memoria limitata, necessità di inferenza veloce e semplicità di implementazione in firmware. Il modello non ha le stesse finalità prestazionali della baseline LightGBM, ma rappresenta un dimostratore di deployment.

## Quantizzazione

I coefficienti del modello Logistic Regression sono esportati in formato `int16`, insieme ai valori di media e scala necessari per normalizzare le feature. Il file generato `wokwi/ids_esp32/include/embedded_model.h` contiene:

- nomi delle feature;
- medie e scale del preprocessing;
- coefficienti quantizzati;
- intercetta quantizzata;
- campioni di test derivati dal dataset;
- metriche del modello originale e dell'emulazione quantizzata ottenute durante l'esportazione.

Questa procedura è una quantizzazione semplice dei coefficienti del modello lineare. Non equivale a una conversione completa TinyML di un modello ensemble, ma consente di discutere in modo concreto il passaggio da pipeline Python a firmware embedded.

Le metriche vengono calcolate sull'intero test set di 42.209 record in due varianti. La prima usa direttamente la pipeline Python con coefficienti in virgola mobile; la seconda ricostruisce in Python la stessa operazione eseguita dal firmware, dequantizzando coefficienti e intercetta `int16`. Entrambe ottengono accuracy 0,8180, F1-score 0,8888 e Macro F1 0,6933. L'accordo tra le predizioni è pari al 100% e le differenze di accuracy e Macro F1 sono entrambe nulle. Il risultato indica che, alla scala adottata, l'arrotondamento dei coefficienti non modifica le classi predette sul test set; non costituisce tuttavia una misura delle prestazioni temporali o energetiche su hardware fisico.

## Simulazione Wokwi

Il progetto `wokwi/ids_esp32/` contiene una simulazione ESP32 con due LED:

- LED verde: classificazione come traffico normale;
- LED rosso: classificazione come traffico di attacco.

Il firmware legge campioni di test incorporati nell'header generato, calcola la probabilità di attacco e stampa su seriale etichetta attesa, etichetta predetta e probabilità stimata. La simulazione può essere eseguita con PlatformIO e Wokwi CLI oppure con l'estensione Wokwi per Visual Studio Code.

È stato inoltre predisposto un progetto Wokwi eseguibile da browser, disponibile all'indirizzo `https://wokwi.com/projects/472799587810026497`. La directory `wokwi/browser_esp32/` contiene i file del progetto online: `sketch.ino`, `embedded_model.h`, `diagram.json` e `wokwi-project.txt`. Il diagramma include il collegamento virtuale tra `esp:TX`, `esp:RX` e `$serialMonitor`, necessario per visualizzare correttamente l'output seriale nel browser.

## Limiti

La simulazione Wokwi non dimostra automaticamente che il modello sia pronto per un deployment reale. Mancano misure su hardware fisico, consumo energetico, memoria effettivamente occupata e robustezza rispetto a traffico reale in streaming. Inoltre, il modello embedded utilizza un sottoinsieme di feature numeriche e non include tutte le trasformazioni della pipeline completa.

Il valore della simulazione è metodologico: mostrare un percorso riproducibile dalla sperimentazione Python a un prototipo firmware, utile per discutere i vincoli di deployment degli IDS in ambienti IoT.

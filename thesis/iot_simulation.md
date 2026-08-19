# Ambiente IoT simulato

L'ambiente simulato è progettato per rappresentare in forma leggera un sistema IoT basato su messaggistica MQTT. Esso non sostituisce il dataset TON_IoT, ma consente di illustrare come dati di traffico possano essere generati, raccolti e successivamente analizzati in una pipeline IDS.

L'architettura include un broker MQTT Eclipse Mosquitto, un simulatore di dispositivi IoT, un collector del traffico e un simulatore di comportamenti anomali. I componenti sono orchestrati tramite Docker Compose.

Il broker MQTT svolge il ruolo di intermediario tra publisher e subscriber. I dispositivi simulati pubblicano messaggi sul topic `iot/sensors`, mentre il collector si sottoscrive allo stesso topic e salva i messaggi in formato CSV.

Il comportamento normale consiste nella generazione periodica di misure plausibili, come temperatura, umidità e tensione del dispositivo. I messaggi includono identificativo del dispositivo, timestamp e tipo di messaggio.

Il comportamento anomalo o malevolo è rappresentato da burst di messaggi, identificativi sospetti e valori fuori intervallo. Questi pattern simulano in modo semplificato anomalie che potrebbero indicare spoofing, compromissione del dispositivo o abuso del canale di comunicazione.

I dati generati possono essere usati come esempio per discutere una pipeline IDS: raccolta, normalizzazione, estrazione di feature, classificazione e generazione di alert. Tuttavia, la simulazione non riproduce la complessità statistica e protocollare di un dataset reale.

La differenza principale rispetto al dataset TON_IoT è che il dataset reale deriva da traffico di rete catturato in scenari sperimentali più articolati, mentre la simulazione produce messaggi applicativi controllati. Pertanto, i risultati sperimentali principali della tesi devono basarsi sul dataset TON_IoT.

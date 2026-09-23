# Prima verifica: codice, dati e split TON_IoT

23 settembre 2026. Ambito: baseline binary e multiclass della pipeline
`852028abc5ff672bd8e75955cc2b52b23d86d94b`.

## Identificazione dei dati

Il CSV locale `train_test_network.csv` contiene 211.043 record e 44 colonne,
per 29.902.775 byte. Il conteggio con il lettore CSV standard concorda con quello
del parser PyArrow. SHA-256:

`26ddc513552de36de6428b2e578efaed2b57504c716dfba847cc0109a64e1974`.

Il manifest identifica ambiente, dipendenze, sorgenti e artefatti. Il comando
di riproduzione e riportato nel README. I dati grezzi restano esclusi da Git.

## Ricostruzione degli split

Sono state usate le funzioni originali di preparazione dei target e i parametri
di configurazione: test 20%, seed 42, stratificazione sul target del singolo task.
Gli indici sono ricostruiti separatamente per binary e multiclass, mantenendo
l'ordine interno delle partizioni. Per ciascun task, tutte le posizioni del CSV
compaiono esattamente una volta nell'unione di training e test.

| Task / classe | Training | Test |
|---|---:|---:|
| Binary: normal | 40.000 | 10.000 |
| Binary: attack | 128.834 | 32.209 |
| Multiclass: normal | 40.000 | 10.000 |
| Multiclass: mitm | 834 | 209 |
| Ciascuna delle altre otto classi multiclass | 16.000 | 4.000 |
| Totale per ciascun task | 168.834 | 42.209 |

Le altre classi sono backdoor, ddos, dos, injection, password, ransomware,
scanning e xss. Il dettaglio e in `results/class_distribution.csv`.
I conteggi delle classi di test coincidono con i supporti dei report Random Forest
baseline salvati nel repository.

## Feature e limiti

La selezione delle colonne e ricavata dal solo training attraverso la funzione
originale, senza adattare encoder o scaler. Per ciascun task la baseline utilizza
32 colonne sorgente distinte. `feature_columns.csv` riporta ordine e appartenenza
ai rami numerico e categorico; il manifest documenta anche le colonne scartate.
`dns_qtype`, `dns_rcode` e `http_status_code` compaiono in entrambi i rami della
pipeline originale: questa verifica ne registra il comportamento senza modificarlo.

Gli indici storici e un ambiente fissato all'epoca degli esperimenti non sono
disponibili. La coincidenza delle numerosita e dei supporti per classe non prova
l'identita delle singole righe rispetto agli split storici. Gli indici consegnati
sono quindi esplicitamente qualificati come ricostruiti.

La verifica corrente non misura duplicati o sovrapposizioni fra record e non
valuta conflitti di etichetta. Tali analisi appartengono alla successiva consegna.
Non sono stati eseguiti nuovi addestramenti o modificati i risultati della tesi.

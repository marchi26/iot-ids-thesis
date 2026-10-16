# SPLIT-02: protocollo proposto per la valutazione delle sovrapposizioni

## Obiettivo e stato

Questa prima verifica riguarda la letteratura e la preparazione delle partizioni. Non sono stati eseguiti nuovi addestramenti né modificati i risultati della tesi. L'obiettivo è distinguere l'effetto delle sovrapposizioni da quello della numerosità del training. La sola deduplicazione non costituisce una novità scientifica: si propone un confronto controllato sul campione disponibile. Il protocollo deve essere discusso con il relatore prima degli addestramenti.

## Dati e definizione dei gruppi

Si conserva il CSV dell'audit precedente: 211.043 righe, SHA-256 `26ddc513552de36de6428b2e578efaed2b57504c716dfba847cc0109a64e1974`. Il caricamento riusa `load_inputs` dello script di audit, verificando manifest, versioni, schema e artefatti iniziali. Le 32 colonne della baseline multiclasse, in ordine, sono pubblicate in `results/feature_columns.csv`. Non sono le dieci feature embedded. Target, indirizzi IP e indici tecnici non partecipano al raggruppamento.

Due righe appartengono allo stesso gruppo se i 32 valori parsati coincidono, considerando uguali i mancanti nella medesima colonna. Non si applicano arrotondamenti, normalizzazione o codifica prima del confronto. L'equivalenza di pandas è verificata indipendentemente mediante tuple complete: gli hash non definiscono l'uguaglianza. Gli identificatori dipendono dall'ordine del CSV congelato. I gruppi con etichette discordanti restano integri e non vengono corretti o eliminati.

Il ruolo delle colonne resta quello di `research/ton_iot_audit/results/feature_columns.csv`: `dns_qtype`, `dns_rcode` e `http_status_code` sono usate sia nel ramo numerico sia in quello categorico della baseline. Questa particolarità non viene corretta incidentalmente nel confronto; le colonne sorgente uniche rimangono 32. Nel preprocessing ispezionato la scelta delle colonne avviene già sul training, non sul test; per il pilota si propone comunque lo schema congelato, senza nuova selezione dipendente dal fold.

## Confronto a test fisso

Il test multiclasse ricostruito dell'audit mantiene esattamente 42.209 righe e relativo ordine. Non si afferma che siano indici storici salvati durante la tesi.

- A: training pool originale di 168.834 righe.
- B: rimozione di tutte le righe del pool il cui gruppo compare nel test.
- C: cinque rimozioni casuali dal pool A, con lo stesso numero di righe rimosse da B per ciascuna classe. Semi: 601, 701, 809, 907, 1009.

Ogni pool viene separato in training e validazione mediante il primo fold di `StratifiedGroupKFold(5, shuffle=True, random_state=1201)`. I gruppi interni non si dividono. La corrispondenza per classe fra B e C riguarda il pool complessivo, non necessariamente il training interno. Per mantenere tale controllo, le valutazioni finali proposte usano un nuovo fit sull'intero pool, dopo la sola diagnosi in validazione e senza selezione di parametri.

B utilizza le feature del test per un intervento diagnostico: non è una stima cieca del deployment. C controlla numerosità e distribuzione delle etichette, non la distribuzione delle feature. I sottogruppi di test esposto/non esposto sono definiti una volta rispetto ad A e conservati per tutti i confronti.

## Partizioni indipendenti e classi rare

Si confrontano inoltre split casuali stratificati e split a gruppi disgiunti, con semi esterni 101, 211, 307, 401, 503. Nel caso casuale: test 20%, poi validazione 25% del pool. Nel caso a gruppi: primo fold esterno su cinque, primo fold interno su quattro con seme 1201. Le proporzioni nominali sono 60/20/20; quelle effettive e i gruppi per classe sono riportati nelle tabelle. Non si sceglie il fold in base alla qualità della distribuzione.

I controlli richiedono copertura unica degli indici, assenza di gruppi condivisi dove prevista e presenza di tutte le classi in training, validazione e test, con attenzione a `mitm`. Una classe assente determina arresto prima del training e richiesta di revisione: nessun seme viene sostituito e nessuna classe accorpata. Cambiando test, il confronto casuale/a gruppi misura anche un cambiamento della distribuzione; non isola causalmente i duplicati.

## Pilota da approvare e costo

Sono proposti Logistic Regression (`C=1`, `solver=lbfgs`, `max_iter=3000`) e Random Forest (`n_estimators=200`, `max_depth=None`, `min_samples_leaf=1`, `n_jobs=1`), senza SMOTE, ricerca iperparametrica o selezione sul test. Il seme del modello è 1103, distinto da quelli di partizione e rimozione. Il preprocessing riprende imputer, scaler e one-hot della pipeline esistente, congelando il ruolo delle 32 colonne; ogni fit usa esclusivamente il proprio training, e il refit finale esclusivamente il pool. Gli encoder non apprendono categorie da validazione o test.

Le 17 configurazioni richiederebbero 34 fit diagnostici e 34 refit finali: massimo 68 fit, ciascuno con preprocessing proprio. Il CSV storico `results/metrics/multiclass_baseline_metrics.csv` riporta circa 23,63 secondi per RF e 211,00 per LR. La semplice proiezione `34 * (23,63 + 211,00)` equivale a circa 2,2 ore di solo training; non è una misurazione SPLIT-02 né una previsione affidabile, perché parametri, parallelismo e numerosità differiscono. Va aggiunto preprocessing, inferenza e bootstrap; il costo effettivo sarà registrato soltanto dopo autorizzazione. Errori di convergenza o vincoli di risorse saranno riportati senza cambiare automaticamente il protocollo.

## Analisi prevista

Si conserveranno Macro F1, balanced accuracy, recall/F1/supporto per classe, matrice di confusione, predizioni con identificatori di riga e gruppo, FPR (normali classificati come attacco) e FNR (attacchi classificati come normali). Per il test fisso si confronteranno differenze appaiate sul totale e sui due sottogruppi prefissati. Si propone bootstrap appaiato a livello di gruppo, 2.000 repliche, seme 1301, intervalli percentili al 95%; ogni replica riutilizza gli stessi gruppi per i modelli confrontati. Repliche prive di una classe saranno conteggiate e segnalate, senza sostituirle silenziosamente. La deviazione standard fra cinque semi descrive variabilità, non un intervallo di confidenza. Le righe duplicate non sono osservazioni indipendenti. Le conclusioni restano circoscritte al dataset e al protocollo verificati.

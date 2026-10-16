# Checkpoint SPLIT-02: fattibilità delle partizioni

Esecuzione locale del 14 ottobre 2026, senza addestramenti. Gli artefatti sono prodotti da `scripts/build_overlap_partitions.py`; il manifest registra input, sorgenti, ambiente, semi e stato del working tree. Il commit di base è `2de1f57196f98d2f23411d7ec0aa6db8c055a653`; i nuovi file non erano committati al momento dell'esecuzione. Non sono stati modificati la tesi o i risultati dell'audit precedente.

## Risultati misurati

Sul CSV congelato sono stati identificati 183.549 gruppi sulle 32 feature, inclusi 11 gruppi con etichette discordanti, mantenuti nel campione. Tutte le 17 configurazioni contengono tutte le classi in training, validazione e test.

| Configurazione | Training interno | Validazione | Test | Righe rimosse | Test esposto al pool |
|---|---:|---:|---:|---:|---:|
| A | 135.067 | 33.767 | 42.209 | 0 | 6.963 |
| B | 122.001 | 30.501 | 42.209 | 16.332 | 0 |
| C, seme 601 | 122.001 | 30.501 | 42.209 | 16.332 | 6.577 |
| C, seme 701 | 122.002 | 30.500 | 42.209 | 16.332 | 6.613 |
| C, seme 809 | 122.001 | 30.501 | 42.209 | 16.332 | 6.602 |
| C, seme 907 | 122.001 | 30.501 | 42.209 | 16.332 | 6.605 |
| C, seme 1009 | 122.001 | 30.501 | 42.209 | 16.332 | 6.614 |

Il pool è l'unione di training interno e validazione. Il test resta identico e ordinato in tutti i confronti A/B/C. Le rimozioni di B e di ogni C coincidono per classe: backdoor 459, ddos 5, dos 2.846, injection 27, mitm 3, normal 6.382, password 70, ransomware 3.605, scanning 481, xss 2.454. Le differenze tra i training interni non invalidano questo controllo sul pool; il protocollo distingue esplicitamente fit diagnostico e refit finale.

| Seme | Training a gruppi | Validazione a gruppi | Test a gruppi | Gruppi condivisi fra partizioni |
|---|---:|---:|---:|---:|
| 101 | 126.625 | 42.209 | 42.209 | 0 |
| 211 | 126.626 | 42.209 | 42.208 | 0 |
| 307 | 126.626 | 42.208 | 42.209 | 0 |
| 401 | 126.626 | 42.209 | 42.208 | 0 |
| 503 | 126.625 | 42.209 | 42.209 | 0 |

Tutti i cinque split casuali hanno 126.625/42.209/42.209 righe. Le proporzioni effettive dei nuovi split sono comprese fra 59,999621% e 60,000095% per il training e fra 19,999716% e 20,000190% per validazione/test. A usa 63,999754%/16,000057%/20,000190% del CSV. B usa 57,808598%/14,452505%/20,000190%, oltre alle righe rimosse; C differisce al massimo di una riga fra training e validazione.

La classe `mitm` è presente ovunque. Nei cinque split a gruppi ha 625–626 righe di training, 208–209 di validazione e 208–209 di test. Nel confronto fisso il test contiene sempre 209 righe `mitm`; B ne conserva 664 nel training interno e 167 in validazione. I conteggi completi, inclusi i gruppi distinti per classe, sono in `results/class_counts.csv`.

## Verifica e limiti

Il costruttore verifica l'equivalenza dei gruppi anche mediante tuple complete e controlla gli indici prima di salvare. Gli otto test sintetici coprono duplicati, mancanti, conflitti di etichetta, rimozioni, semi, disgiunzione e classi assenti. Il verificatore separato ricontrolla gli artefatti salvati, collegando il proprio esito al manifest tramite SHA-256 in `results/validation.json`. Non si tratta di una seconda esecuzione integrale del costruttore.

La costruzione ha richiesto 1.362,35 secondi nell'ambiente locale. Non sono state prodotte accuracy, F1, predizioni o misure di training SPLIT-02. L'azzeramento delle sovrapposizioni è una proprietà delle partizioni, non una prova di miglioramento o peggioramento dei modelli.

## Prima del pilota

Prima degli addestramenti occorre concordare con il relatore parametri, refit, numero di esecuzioni e analisi dell'incertezza. Il confronto bibliografico comprende sei testi integrali, incluso il preprint SSRN. La matrice riporta metodi, ripetizioni, disponibilità del codice e differenze rispetto a SPLIT-02; non costituisce una dimostrazione di originalità scientifica.

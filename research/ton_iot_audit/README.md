# TON_IoT: prima verifica di codice, dati e split

Consegna intermedia del 23 settembre 2026, relativa alla verifica prevista entro
il 24 settembre. Base della pipeline: `852028abc5ff672bd8e75955cc2b52b23d86d94b`.

Questa consegna identifica il CSV, documenta l'ambiente e le feature della baseline
e ricostruisce separatamente le partizioni binary e multiclass. Non comprende
l'analisi dei duplicati, delle sovrapposizioni tra record o dei conflitti di etichetta.
Non esegue training, fitting dei trasformatori o modifiche ai dati della tesi.

## Esecuzione

Python 3.11; dipendenze fissate in `requirements.txt`. Dalla radice del repository:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r research/ton_iot_audit/requirements.txt
.\.venv\Scripts\python.exe scripts/inspect_ton_iot_split.py --csv data/raw/train_test_network.csv
```

Il CSV deve essere disponibile localmente e non viene pubblicato.
`--output` consente una verifica in una directory separata.

## Materiale della prima consegna

- `initial_review.md`: riscontro su codice, dati e split, con limiti della ricostruzione.
- `results/manifest.json`: hash del CSV, commit di esecuzione, ambiente, parametri e hash dei sorgenti e degli artefatti.
- `results/split_indices.csv.gz`: indici ricostruiti e ordine interno alle partizioni.
- `results/class_distribution.csv`: numerosita per task, partizione e classe.
- `results/feature_columns.csv`: feature nei rami numerico e categorico, con ordine esplicito e lista sorgente senza ripetizioni.
- `results/schema.csv`: tipi e valori mancanti rilevati dal parser.

Gli indici sono posizioni a base zero nel CSV, esclusa l'intestazione, collegate
al suo SHA-256. Non sono indici storici recuperati. L'ambiente documentato e quello
della verifica corrente, non una certificazione dell'ambiente degli esperimenti originari.

La fase successiva prevista dalla scheda riguarda duplicati, sovrapposizioni,
conflitti di etichetta, controlli sintetici e rapporto conclusivo.

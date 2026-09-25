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

## Provenienza dell'esecuzione e della consegna

Il campo `execution_commit` del manifest conserva lo SHA storico
`8ca44fdbce2d0b7339f8950ef733fcf12aae2657`: era il commit indicato da `HEAD`
durante l'esecuzione del 23 settembre. Non identifica, da solo, tutti i file
eseguiti, poiche il working tree conteneva aggiunte non ancora committate:
lo script `scripts/inspect_ton_iot_split.py` e il materiale della prima verifica
in `research/ton_iot_audit/`. I file preesistenti della pipeline non erano stati
modificati. Gli hash in `source_sha256` identificano i byte locali dei sorgenti
utilizzati; quelli in `artifacts_sha256` identificano gli artefatti prodotti.

Il controllo Git immediatamente successivo alla prima esecuzione riportava
`?? research/` e `?? scripts/inspect_ton_iot_split.py`. Prima della seconda
esecuzione di verifica, i file della consegna erano stati aggiunti all'indice,
ma non ancora committati; `HEAD` era ancora `8ca44fd`. Le due esecuzioni hanno
prodotto manifest e hash degli artefatti identici. Non e stato acquisito uno
snapshot completo del working tree contestualmente all'avvio: queste informazioni
derivano dalla sequenza dei comandi e dai controlli Git effettuati durante il lavoro.

Il materiale e stato successivamente registrato nel commit `5cb4161`, quindi
riorganizzato nel commit di consegna
`f46365e8e46da9b8a1fdb7de85e9150dec5cee25`, direttamente successivo alla base
`852028a`. La riorganizzazione ha mantenuto identico l'albero dei file, verificato
tramite confronto Git. `f46365e` identifica dunque la consegna, non il valore
di `HEAD` al momento dell'esecuzione. Lo SHA storico nel manifest non viene
sostituito retroattivamente. Questa nota documentale non modifica gli artefatti
e non costituisce una nuova esecuzione.

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

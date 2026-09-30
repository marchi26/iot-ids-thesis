# TON_IoT: verifica degli split e audit dei duplicati

Consegna intermedia del 23 settembre 2026, relativa alla verifica prevista entro
il 24 settembre. Base della pipeline: `852028abc5ff672bd8e75955cc2b52b23d86d94b`.

La prima consegna identifica il CSV, documenta l'ambiente e le feature della baseline
e ricostruisce separatamente le partizioni binary e multiclass. L'estensione del
29 settembre esamina duplicati, sovrapposizioni e conflitti di etichetta usando
quegli stessi indici salvati. Non esegue training, fitting dei trasformatori
o modifiche ai dati della tesi. La consegna iniziale e conservata senza modifiche
in `results/`; i nuovi risultati sono separati in `results/full_audit/`.

## Esecuzione

Python 3.11.9; dipendenze fissate in `requirements.txt`. Dalla radice del repository:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r research/ton_iot_audit/requirements.txt
.\.venv\Scripts\python.exe scripts/audit_ton_iot_split.py --csv data/raw/train_test_network.csv
.\.venv\Scripts\python.exe scripts/check_ton_iot_audit.py --csv data/raw/train_test_network.csv
```

Il CSV deve essere disponibile localmente e non viene pubblicato.
`--output` consente una verifica in una directory separata. Il controllo completo
esegue test sintetici, conteggi indipendenti e una ripetizione in una directory
temporanea, usando lo stesso ambiente Python. La prima consegna non deve essere
rigenerata prima dell'audit. Per ripetere soltanto la verifica iniziale:

```powershell
.\.venv\Scripts\python.exe scripts/inspect_ton_iot_split.py --output results/logs/initial_recheck
```

L'audit rifiuta CSV o artefatti iniziali con hash diversi, versioni delle dipendenze
diverse da quelle registrate e modifiche ai sorgenti della pipeline di riferimento.
Il confronto dei sorgenti di riferimento tollera solo la conversione dei terminatori
di riga del checkout e gli spazi bianchi ai margini dell'intero file. Gli hash dei
sorgenti nel nuovo manifest identificano invece esattamente i byte locali eseguiti.

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

## Audit completo

- `scripts/audit_ton_iot_split.py`: riusa gli indici salvati; confronta righe complete
  (A), feature baseline senza target (B) e, separatamente, dieci feature embedded binary.
- `scripts/verify_ton_iot_audit.py`: ricalcola tutti i campi aggregati e per classe
  con tuple Python, insiemi e `Counter`, senza riusare il raggruppamento pandas.
- `scripts/test_audit_ton_iot_split.py`: esempi sintetici a risultato noto e controlli
  degli input; non richiede il dataset reale.
- `scripts/check_ton_iot_audit.py`: esegue i controlli e registra gli esiti.
- `results/full_audit/audit_summary.csv`: gruppi duplicati, righe coinvolte,
  eccedenze, gruppi condivisi, esposizione del test e conflitti sul target attivo.
- `results/full_audit/audit_by_class.csv`: dettaglio per classe.
- `results/full_audit/audit_columns.csv`: elenco e ordine delle colonne confrontate.
- `results/full_audit/manifest.json`: provenienza della nuova esecuzione, stato Git
  rilevato all'avvio, hash di input, sorgenti e risultati; collega il manifest iniziale.
- `results/full_audit/validation.json`: esiti dei test, verifica indipendente,
  ripetibilita dei CSV e controllo di integrita della prima consegna.
- `report.md` e `report.pdf`: rapporto conclusivo di due pagine.

Un gruppo duplicato contiene almeno due righe uguali nella partizione; le righe
coinvolte sono tutte le righe dei gruppi duplicati, le eccedenze sono la somma di
`n - 1`. Ogni riga di test esposta e contata una sola volta, anche in presenza di
piu corrispondenze nel training. Le percentuali complessive usano tutte le righe
del test del task; quelle per classe usano tutte le righe del test della classe.
I duplicati per classe sono calcolati all'interno della classe e partizione;
l'esposizione considera corrispondenze con qualunque classe del training.
I conflitti riguardano etichette del target attivo discordanti nello stesso gruppo
su tutto il CSV; `shared_conflicting_groups` restringe il conteggio ai gruppi
presenti in entrambe le partizioni.

L'uguaglianza riguarda valori interpretati dal parser prima del preprocessing,
non le righe CSV come sequenze di byte. I valori mancanti nella stessa colonna
sono considerati uguali. Non si applicano arrotondamenti, conversioni aggiuntive,
imputazione o rimozione di righe. Per il confronto B una colonna sorgente presente
in entrambi i rami del trasformatore viene confrontata una sola volta.
Il confronto embedded usa gli stessi indici binary e le feature definite
nell'esportatore; non analizza probabilita, quantizzazione o trasformazioni numeriche.
Restano esclusi fold di tuning, sottoinsiemi degli esperimenti estesi, SMOTE e
coincidenze dopo il preprocessing.

Il manifest completo registra un working tree con modifiche non committate:
il suo `execution_commit` indica la base Git corrente, mentre `source_sha256`
identifica il codice effettivamente eseguito. Un eventuale commit successivo di
consegna non deve sostituire questo SHA storico.

## Riproduzione del PDF

Le dipendenze tipografiche sono separate da quelle dell'audit:

```powershell
python -m pip install -r research/ton_iot_audit/requirements-report.txt
python scripts/build_ton_iot_audit_report.py
```

Il generatore impagina `report.md` e non esegue calcoli statistici. Le tabelle del
rapporto vanno confrontate con i CSV della medesima esecuzione prima della consegna.

# SPLIT-02: approfondimento degli errori del pilota

## Ambito

Questa lettura descrittiva aggiuntiva risponde alla richiesta del relatore successiva alla validazione del pilota `c4f9f32`. Non fa parte dell'analisi bootstrap inizialmente prevista. Utilizza soltanto le predizioni dei 14 refit sul test fisso; nessun nuovo addestramento, ricampionamento o selezione di parametri. Gli artefatti del pilota e la relazione precedente rimangono invariati.

Le tabelle complete coprono LR e RF, tutte le dieci classi e i sottogruppi complessivo, esposto e non esposto. L'esposizione resta quella definita rispetto ad A. Ogni confronto usa le stesse righe, nello stesso ordine, con identici `row_id`, `group_id` ed etichette. I cinque C sono mantenuti distinti nei CSV; le medie riassumono cinque modelli, non un classificatore ottenuto combinandone le predizioni.

## RF: classi nel sottogruppo esposto

F1 assume valori tra 0 e 1; le differenze sono in punti percentuali (pp). Per C sono riportate media e intervallo minimo-massimo dei cinque controlli, non un intervallo di confidenza. I supporti si riferiscono alla classe vera. Precision e F1 includono anche i falsi positivi provenienti dalle altre classi dello stesso sottogruppo.

| Classe | Righe | Gruppi | F1 A | F1 B | F1 C: media [min; max] | B-A (pp) | B-media C (pp) |
|---|---|---|---|---|---|---|---|
| backdoor | 435 | 428 | 1.0000 | 1.0000 | 1.0000 [1.0000; 1.0000] | +0.00 | +0.00 |
| ddos | 5 | 5 | 1.0000 | 0.5333 | 1.0000 [1.0000; 1.0000] | -46.67 | -46.67 |
| dos | 1380 | 1027 | 1.0000 | 1.0000 | 1.0000 [1.0000; 1.0000] | +0.00 | +0.00 |
| injection | 10 | 7 | 0.8696 | 0.0000 | 0.8126 [0.7619; 0.8696] | -86.96 | -81.26 |
| mitm | 2 | 2 | 1.0000 | 0.6667 | 1.0000 [1.0000; 1.0000] | -33.33 | -33.33 |
| normal | 1652 | 74 | 1.0000 | 0.9871 | 1.0000 [1.0000; 1.0000] | -1.29 | -1.29 |
| password | 49 | 42 | 1.0000 | 1.0000 | 1.0000 [1.0000; 1.0000] | +0.00 | +0.00 |
| ransomware | 1396 | 824 | 1.0000 | 0.9844 | 1.0000 [1.0000; 1.0000] | -1.56 | -1.56 |
| scanning | 440 | 419 | 1.0000 | 1.0000 | 1.0000 [1.0000; 1.0000] | +0.00 | +0.00 |
| xss | 1594 | 1331 | 0.9991 | 0.9947 | 0.9987 [0.9984; 0.9991] | -0.44 | -0.41 |

La differenza di Macro-F1 B-A nel sottogruppo esposto di RF è -17.0242 pp. Il contributo di ciascuna classe è la sua differenza di F1 divisa per dieci, poiché la Macro-F1 assegna lo stesso peso a tutte le classi. `injection`, `ddos` e `mitm` contribuiscono insieme per -16.6957 pp, pari al 98.07% della diminuzione netta. Si tratta di una scomposizione aritmetica, non di una stima causale: il peso elevato non implica un numero elevato di errori.

## Transizioni appaiate rispetto ad A

Ogni cella riporta **righe/gruppi distinti**. Le colonne distinguono corretti rimasti corretti, corretti diventati errati, errori corretti, errori rimasti sulla stessa classe sbagliata ed errori passati a un'altra classe sbagliata. Sono inclusi tutti i controlli C, non soltanto la loro media.

| Classe vera | Destinazione | Corretto-corretto | Corretto-errato | Errato-corretto | Stesso errore | Errore diverso |
|---|---|---|---|---|---|---|
| injection | B | 0/0 | 10/7 | 0/0 | 0/0 | 0/0 |
| injection | C_601 | 10/7 | 0/0 | 0/0 | 0/0 | 0/0 |
| injection | C_701 | 10/7 | 0/0 | 0/0 | 0/0 | 0/0 |
| injection | C_809 | 8/6 | 2/1 | 0/0 | 0/0 | 0/0 |
| injection | C_907 | 8/6 | 2/1 | 0/0 | 0/0 | 0/0 |
| injection | C_1009 | 8/6 | 2/1 | 0/0 | 0/0 | 0/0 |
| ddos | B | 4/4 | 1/1 | 0/0 | 0/0 | 0/0 |
| ddos | C_601 | 5/5 | 0/0 | 0/0 | 0/0 | 0/0 |
| ddos | C_701 | 5/5 | 0/0 | 0/0 | 0/0 | 0/0 |
| ddos | C_809 | 5/5 | 0/0 | 0/0 | 0/0 | 0/0 |
| ddos | C_907 | 5/5 | 0/0 | 0/0 | 0/0 | 0/0 |
| ddos | C_1009 | 5/5 | 0/0 | 0/0 | 0/0 | 0/0 |
| mitm | B | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 |
| mitm | C_601 | 2/2 | 0/0 | 0/0 | 0/0 | 0/0 |
| mitm | C_701 | 2/2 | 0/0 | 0/0 | 0/0 | 0/0 |
| mitm | C_809 | 2/2 | 0/0 | 0/0 | 0/0 | 0/0 |
| mitm | C_907 | 2/2 | 0/0 | 0/0 | 0/0 | 0/0 |
| mitm | C_1009 | 2/2 | 0/0 | 0/0 | 0/0 | 0/0 |

Per A-B, le destinazioni degli errori nelle tre classi sono:

| Classe vera | Predizione A | Predizione B | Righe | Gruppi |
|---|---|---|---|---|
| ddos | ddos | xss | 1 | 1 |
| injection | injection | xss | 10 | 7 |
| mitm | mitm | ddos | 1 | 1 |

I conteggi delle righe nelle cinque categorie sono disgiunti e sommano al supporto della classe. I gruppi sono conteggiati distintamente in ogni cella: in presenza di etichette discordanti, lo stesso gruppo può comparire in più classi o categorie, quindi i conteggi dei gruppi non devono essere sommati come se fossero indipendenti. Un gruppo corrisponde alla definizione congelata basata sulle feature, non necessariamente a un dispositivo o a una sessione.

## Compromesso fra falsi allarmi e attacchi mancati

Sul test complessivo, per LR i normali classificati come attacco passano da 814 in A a 1493 in B; nei cinque C variano da 810 a 813. Gli attacchi classificati come normali passano da 644 a 146; nei C variano da 666 a 677. Questi conteggi riguardano la distinzione normale/attacco, non tutti gli errori fra tipi di attacco. Nei CSV `fp` e `fn` adottano invece la convenzione uno-contro-tutti per ciascuna classe: per la classe `normal` i ruoli sono quindi invertiti rispetto alla rilevazione degli attacchi.

## Limiti e verifica

I piccoli supporti delle classi rare rendono rilevante anche il cambiamento di poche predizioni. La Macro-F1 complessiva e quella del sottogruppo esposto non sono intercambiabili. I controlli C pareggiano la numerosità per classe del pool B, ma non la distribuzione delle feature; non isolano ogni possibile spiegazione delle differenze osservate. Questa analisi non aggiunge test di significatività né modifica gli intervalli già pubblicati. Il confronto random/group-disjoint resta rinviato.

`class_changes.csv` conserva supporti, precision, recall, F1, TP/FP/FN e contributi alla differenza di Macro-F1 per A-B e A-ciascun C. `error_transitions.csv` conserva le cinque categorie appaiate, comprese quelle con conteggio zero. `prediction_transitions.csv` dettaglia le classi predette in A e nella configurazione confrontata. Le metriche sono ricalcolate dalle predizioni e confrontate con i CSV originali; i conteggi delle transizioni sono verificati rispetto ai supporti e alle variazioni degli errori. `manifest.json` identifica input, script, ambiente e controlli eseguiti.

# Diario

## 2026-10-19 — Fase 3, download in background

### Fatto
- Regola qualità spostata sul periodo medio (`period.field = "wave_period"`, min 6 s, buono 11 s), perché ce l'hanno sia Open-Meteo sia il dataset puntuale Copernicus. Tarata con una griglia di soglie sulle 5 zone di collaudo: scarto medio 3,4 punti di Good+ rispetto alla tabella approvata sul periodo di picco.

  | Good+ per mese | Gen | Feb | Mar | Apr | Mag | Giu | Lug | Ago | Set | Ott | Nov | Dic |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|
  | North Shore | 72 | 61 | 47 | 28 | 7 | 1 | 0 | 1 | 8 | 33 | 45 | 66 |
  | Jeffreys Bay* | 40 | 48 | 57 | 64 | 59 | 59 | 60 | 63 | 51 | 49 | 38 | 34 |
  | Hossegor | 54 | 55 | 50 | 32 | 16 | 9 | 6 | 9 | 23 | 43 | 49 | 53 |
  | Bali | 37 | 43 | 63 | 80 | 80 | 88 | 90 | 88 | 87 | 79 | 61 | 43 |
  | Mentawai | 34 | 35 | 46 | 68 | 83 | 90 | 89 | 84 | 74 | 62 | 39 | 29 |

- `fetch_waves.py`:
  - legge solo la coda congelata `data/raw/waves/_queue.json` (150 zone per numero di spot, con centro, esposizione e punto onde);
  - tiene il conto stimato delle chiamate (peso giorni/14 × variabili/10) e si ferma a 9.000 al giorno e 4.500 all'ora (giorno UTC), poi riparte da solo;
  - scrive `_progress.json` e ha `--stato`; con SIGTERM salva lo stato e si ferma.
- Download delle 145 zone mancanti lanciato il 19/10 alle 22:17 con `nohup` + `caffeinate`. Stima circa 5 giorni, circa 28 zone al giorno.
- `build_climate.py`: le zone senza dati restano in `climate.json` con `weeks: null`.
- Scheda: "Periodo medio".


## 2026-10-19 — Fase 3, onde ERA5 (collaudo e strategia dati)

### Fatto
- `scripts/fetch_waves.py` (Open-Meteo):
  - onde dal modello `era5_ocean` (altezza, periodo medio, periodo di picco, direzione dell'onda totale). Per il 2005-2024 Open-Meteo **non ha lo swell separato**: c'è solo dal 2022;
  - punto onde a 40 km dal centro verso l'esposizione; se è terra, spostamenti di 20 km;
  - vento ERA5 a 10 m nella cella di **mare** più vicina alla costa (`cell_selection=sea`). La cella di terra lo sottostimava: a Bali segnava "vento leggero" nel 47-64% delle ore;
  - pause, attesa automatica sui limiti, ripresa da dove si era fermato, `--rifai-vento`. Grezzi in `data/raw/waves/<id>.parquet` (fuori da git, ~1,5 MB a zona).
- `data/quality-rule.json`: tutte le soglie della regola oraria, più la scelta del campo periodo.
- `scripts/build_climate.py`:
  - ore diurne calcolate con la posizione del sole; giorno = classe migliore tenuta per 3 ore;
  - per settimana: classe prevalente, % giorni Good+, percentili 25/50/75 di altezza e periodo. Output `data/climate.json` (~1,6 KB a zona);
  - regge anche dati ogni 3 o 6 ore (le 3 ore diventano campioni);
  - `--verifica` stampa la tabella mese per mese.
- App: `getZoneWeeks` legge `climate.json`. La scheda mostra altezza 25-75% e giorni Good+ della settimana. Le zone senza dati non compaiono. Generatore finto e parametri `demo` eliminati.
- Marker del globo rimpiccioliti: punti di circa 5 px, la selezionata con un anello.
- Collaudo su 5 zone (20 anni orari, Open-Meteo):
  - prima regola troppo generosa: Hossegor Epic in inverno, Bali buona tutto l'anno, Jeffreys Bay piatta;
  - correzioni: vento in cella di mare; altezza massima 3,5 m con calo fino a 6 m; bonus cross-offshore; bonus vento leggero ridotto; ideale 2,5 m e periodo buono 14 s;
  - Mentawai era senza esposizione, con il punto onde nello stretto riparato: `esposizione_manuale` = 225 nel CSV e zona riscaricata.

  | Good+ per mese | Gen | Feb | Mar | Apr | Mag | Giu | Lug | Ago | Set | Ott | Nov | Dic |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|
  | North Shore | 70 | 60 | 50 | 30 | 10 | 2 | 0 | 1 | 10 | 35 | 45 | 64 |
  | Jeffreys Bay* | 37 | 44 | 52 | 59 | 56 | 55 | 56 | 59 | 47 | 43 | 35 | 31 |
  | Hossegor | 54 | 58 | 50 | 30 | 16 | 7 | 5 | 7 | 22 | 42 | 50 | 57 |
  | Bali (Medewi/Uluwatu) | 37 | 42 | 60 | 80 | 90 | 94 | 95 | 96 | 91 | 81 | 60 | 39 |
  | Mentawai | 42 | 39 | 50 | 68 | 83 | 89 | 91 | 90 | 83 | 71 | 54 | 42 |

  *zona "Doughnuts Backreef", 41 km da J-Bay.
- Consumo Open-Meteo misurato (gli header non lo riportano, nessun 429 ricevuto):
  - 18 richieste da 20 anni oggi, di cui 11 nella stessa ora: il peso medio è al massimo 454 chiamate, quindi la stima di ~520 a richiesta è troppo alta;
  - compatibile con `giorni/14 × variabili/10`: onde 209, vento 104, circa 313 a zona;
  - circa 2,7 minuti a zona.
- Copernicus CDS, misure senza account (endpoint pubblico di costing):
  - dataset puntuale `reanalysis-era5-single-levels-timeseries`: ha altezza significativa, periodo medio e direzione media dell'onda, più vento u/v a 10 m. Non ha periodo di picco né swell separato. 20 anni orari per un punto costano 180 su un limite di 760: una richiesta per punto;
  - griglia `reanalysis-era5-single-levels`, 7 variabili: 1 mese ogni 6 ore costa 5.208, 1 anno 61.488, 1 mese con 3 orari 3.906, 1 mese orario 31.248, su un limite di 121.000.
- Prove su dati già scaricati:
  - dati ogni 6 ore: Good+ mensile spostato di 0,4-4,9 punti;
  - 3 orari UTC fissi: fino a 22 punti su Bali (ore notturne), quindi non usabile sulla griglia globale;
  - formato intermedio Copernicus (u/v convertiti): climatologia identica.
- `scripts/era5_cds.py`: `costi`, `prova-puntuale`, `prova-griglia` (1 mese), `scarica` (dataset puntuale -> stesso parquet di Open-Meteo).
- Periodo medio / periodo di picco nelle 5 zone: da 0,77 a 0,85, quindi non è un fattore fisso.

### Aperti
- Prova reale Copernicus non fatta: serve l'account CDS di Mattia. Quindi tempi di coda e dimensioni della griglia sono stime, non misure, e anche il confronto Open-Meteo/CDS sulle stesse ore è da fare.
- Hossegor: l'inverno resta alto quanto l'autunno; da tarare con l'amico (es. `height.max`).
- Con il dataset puntuale CDS la regola va spostata su `period.field = wave_period` e ritarata sulle 5 zone.
- Sul sito ci sarebbero solo le 5 zone con dati finché il download non è completo: non pubblicare prima.

### Prossimi passi
- Mattia: account CDS, licenza ERA5, chiave in `~/.cdsapirc`.
- Lanciare `era5_cds.py prova-puntuale` e `prova-griglia`, riscalare le stime e confrontare con Open-Meteo.
- Ritarare la regola sul periodo medio e scaricare tutte le zone dal dataset puntuale.


## 2026-10-19 — Fase 2, zone

### Fatto
- Spot grezzi scaricati in `data/raw/spots_raw.json` (5890 spot). `data/raw/` non è versionata: gli script riscaricano i file se mancano.
- `scripts/build_zones.py` (venv `.venv`, dipendenza solo shapely):
  - coordinate non valide scartate: 12;
  - spot sulla terraferma a più di 10 km dalla costa Natural Earth 1:50m scartati: 59 (fiumi, laghi, Grandi Laghi, errori);
  - doppioni scartati: 1023. Regola: due spot entro 1 km, oppure stesso nome nello stesso paese entro 50 km. Lo stesso nome in posti lontani non è un doppione (ci sono 5 "Backdoor"). La regola del km toglie anche picchi vicini (es. Pipeline/Backdoor), quindi abbassa `n_spot` nelle zone dense;
  - esposizione per spot: sei anelli da 3 a 120 km attorno allo spot, si guarda in quale direzione c'è mare; la media vettoriale dà la direzione verso il largo. Verificata a Oahu (Pipeline 333°, Waikiki ~195°, Makaha 251°);
  - clustering a leader entro 60 km, con il paese come confine (la parte prima della virgola nel campo `country`). Uno spot entra nella zona solo se la sua esposizione è entro 45° da quella dello spot centrale, così le coste rivolte in direzioni diverse restano separate (North Shore e South Shore di Oahu);
  - risultato: 1013 zone candidate, 415 con un solo spot, 45 senza esposizione (isolotti che non compaiono nella costa 1:50m, oppure spot con esposizioni troppo diverse).
- `data/review/zones_candidates.csv`: separatore `;`, decimali con la virgola (Excel in italiano), UTF-8 con BOM.
- `scripts/apply_review.py`: legge il CSV (anche se Excel lo risalva in cp1252), tiene le righe con `tieni = si` e scrive `data/zones.json`. Per ogni zona aggiunge:
  - l'aeroporto più vicino con voli di linea (OurAirports, tipo large/medium con codice IATA). Serve all'app, la logica voli non è cambiata;
  - `nearEurope` per Marocco e Canarie, come nel prototipo;
  - `exposure` e `spots`;
  - i parametri `demo` per i dati onda finti.
- Colonne di revisione `nome_manuale` ed `esposizione_manuale`. Se sono compilate, `apply_review.py` le usa al posto di `nome` ed `esposizione_gradi`:
  - `nome_manuale` può essere solo il nome ("North Shore", resta la regione proposta) oppure "Nome · Regione";
  - un'esposizione non numerica blocca lo script indicando la zona.
  - `build_zones.py` considera revisione anche queste colonne e non sovrascrive il CSV.
  - CSV esistente aggiornato senza perdere i "si"; con le colonne vuote `zones.json` resta identico.
- Preselezionate le 150 zone con più spot (`--preseleziona 150`). L'app gira con posizioni vere e onde ancora finte.
- Globo con 150 zone:
  - pallini più piccoli, che crescono con lo zoom;
  - zona selezionata disegnata sopra le altre;
  - etichette solo da zoom e senza sovrapposizioni;
  - lista zone sotto la timeline con altezza massima e scorrimento.
  - Misura in Chrome headless: ridisegno durante il trascinamento 1,5 ms; zoom con coste 1:50m ~16 ms come prima, dominato dalle coste.

### Aperti
- Revisione a mano del CSV: nomi (lo spot centrale non è sempre il più noto, es. il North Shore si chiama "Graters", correggibile con `nome_manuale`), zone da tenere, esposizioni mancanti o sbagliate con `esposizione_manuale`.
- Nomi di paesi e regioni in inglese, come nella fonte.
- Nelle 150 tre zone sono senza esposizione: 4 Bobs (Mentawai), Temae (Polinesia), Airport Left (St Barth). Isolator (WA) ha l'aeroporto a 221 km.
- Il menu "Arrivo" ha 150 voci in ordine di numero di spot.

### Prossimi passi
- Revisione del CSV e nuovo `apply_review.py`.
- Fase 3: formato del JSON onde ERA5 per zona e settimana; `exposure` serve a giudicare direzione swell e vento offshore.


## 2026-10-19 — Fase 1, base (completata)

### Fatto
- Diviso `swell-atlas.html` in `index.html`, `style.css`, `app.js`. Nessuna funzione nuova, aspetto e comportamento invariati.
- Coste spostate in `data/land-50m.json` e `data/land-110m.json`, caricate con `fetch`.
- Zone, aeroporti e scala qualità spostati in `data/zones.json`, `data/airports.json`, `data/scale.json`, con nomi di campo leggibili (`name`, `region`, `airport.code`…).
- Dati onda finti isolati in `getZoneWeeks(zone)`; i parametri del generatore stanno in `zone.demo`. Verificato che le 52 settimane generate sono identiche a quelle del prototipo.
- La regola "Taghazout e Fuerteventura hanno voli come l'Europa" ora è il campo `airport.nearEurope` invece di codici scritti nel codice.
- Parametri della stima voli e prezzi spostati in `data/flight-estimate.json`; verificato che le stime sono identiche (784 combinazioni aeroporto/zona/distanza).
- `app.js` è un modulo ES (top-level `await` per il caricamento dati); se i dati non arrivano, il pannello lo segnala.
- README, DIARIO, CLAUDE.md, `.gitignore`.
- Repo pubblico https://github.com/mattialangella95-bit/swell-atlas, GitHub Pages attivo da `main` (root): https://mattialangella95-bit.github.io/swell-atlas/

### Aperti
- Le etichette dei mesi (`MESI`) restano nel codice: sono testo dell'interfaccia, non dati.
- Il prototipo originale `swell-atlas.html` resta nella cartella ma è escluso da git.

### Prossimi passi
- Fase 2: definire il formato definitivo di `zones.json` (cosa resta di `demo`, quali campi servono a ERA5) e ampliare la lista.
- Fase 3: decidere il formato del JSON onde (es. `data/waves/<id>.json` con 52 settimane `{q,h,t}`) così `getZoneWeeks` diventa una lettura.

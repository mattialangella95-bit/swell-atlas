# Diario

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

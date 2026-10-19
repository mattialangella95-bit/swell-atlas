# Diario

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

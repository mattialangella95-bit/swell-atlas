# Diario

## 2026-10-19 — Fase 1, base

### Fatto
- Diviso `swell-atlas.html` in `index.html`, `style.css`, `app.js`. Nessuna funzione nuova, aspetto e comportamento invariati.
- Coste spostate in `data/land-50m.json` e `data/land-110m.json`, caricate con `fetch`.
- Zone, aeroporti e scala qualità spostati in `data/zones.json`, `data/airports.json`, `data/scale.json`, con nomi di campo leggibili (`name`, `region`, `airport.code`…).
- Dati onda finti isolati in `getZoneWeeks(zone)`; i parametri del generatore stanno in `zone.demo`. Verificato che le 52 settimane generate sono identiche a quelle del prototipo.
- La regola "Taghazout e Fuerteventura hanno voli come l'Europa" ora è il campo `airport.nearEurope` invece di codici scritti nel codice.
- `app.js` è un modulo ES (top-level `await` per il caricamento dati); se i dati non arrivano, il pannello lo segnala.
- README, DIARIO, CLAUDE.md, `.gitignore`, repo git locale.

### Aperti
- In `flight()` restano i parametri della stima finta (moltiplicatori stagionali dei prezzi, velocità media, tempo per scalo). Spariranno con le fasi 4 e 5; se servono prima, vanno in un JSON.
- Le etichette dei mesi (`MESI`) restano nel codice: sono testo dell'interfaccia, non dati.
- Il prototipo originale `swell-atlas.html` resta nella cartella ma è escluso da git.
- Repo GitHub `mattialangella95-bit/swell-atlas` non ancora creato (in attesa di conferma).

### Prossimi passi
- Creare il repo e attivare GitHub Pages dal branch `main`, cartella root.
- Fase 2: definire il formato definitivo di `zones.json` (cosa resta di `demo`, quali campi servono a ERA5) e ampliare la lista.
- Fase 3: decidere il formato del JSON onde (es. `data/waves/<id>.json` con 52 settimane `{q,h,t}`) così `getZoneWeeks` diventa una lettura.

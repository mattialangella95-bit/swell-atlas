# Swell Atlas — note per Claude

Progetto hobby di Mattia. Rispondi in italiano.

## Cos'è
Sito statico su GitHub Pages (account `mattialangella95-bit`, repo `swell-atlas`): globo D3 ortografico con zone surf colorate per qualità media settimanale (52 settimane, scala Flat → Epic), più stima ore di volo e prezzo dagli aeroporti italiani. Stessa architettura di Sala Aste: niente framework, niente build.

## Regole
- Solo HTML + CSS + JS separati (`index.html`, `style.css`, `app.js`). Librerie solo da CDN (D3 7.8.5, topojson-client 3.0.2). Non installare dipendenze se non servono.
- **Il codice non contiene dati**: zone, aeroporti, scala, parametri stima voli e coste stanno in `data/*.json` e si caricano con `fetch`.
- I dati onda passano tutti da `getZoneWeeks(zone)` in `app.js`: restituisce 52 elementi `{q, h, t}` (indice scala, altezza m, periodo s). Oggi sono finti (parametri in `zone.demo`); in fase 3 diventerà la lettura del JSON calcolato da ERA5. Non generare dati onda altrove.
- Lo stile del codice è compatto (righe dense, nomi brevi): mantienilo.
- Non leggere file fuori da questa cartella.
- Lavora una fase alla volta (vedi README); non aggiungere funzioni non richieste.
- Supabase solo se e quando serve in fase 5.
- Chiedi conferma prima di creare repo, fare push o pubblicare.
- A fine sessione aggiorna `DIARIO.md` (fatto, aperti, prossimi passi).

## Link
- Sito: https://mattialangella95-bit.github.io/swell-atlas/
- Repo: https://github.com/mattialangella95-bit/swell-atlas

## Script dati (Python)
- Venv in `.venv`, dipendenze in `requirements.txt` (solo shapely). Lancia con `.venv/bin/python scripts/...`.
- `data/zones.json` non si modifica a mano: si rigenera con `scripts/build_zones.py` -> revisione di `data/review/zones_candidates.csv` -> `scripts/apply_review.py`.
- Il CSV di revisione è di Mattia: non sovrascriverlo se ha `tieni`/`note` compilati.
- `data/raw/` contiene solo download, non è versionata.

## Test in locale
`python3 -m http.server 8000` e apri http://localhost:8000 (con `file://` il fetch fallisce).

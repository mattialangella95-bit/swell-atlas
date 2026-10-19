# Swell Atlas

Atlante delle stagioni surf: un globo con le zone colorate per qualità media dell'onda, settimana per settimana, più una stima di ore di volo e prezzo dall'Italia. È una statistica storica per scegliere *quando* partire, non una previsione.

Sito statico (HTML + CSS + JS, nessun build), pubblicato su GitHub Pages. Librerie da CDN: D3 7 e topojson-client 3.

Online: https://mattialangella95-bit.github.io/swell-atlas/

## Struttura

```
index.html          markup
style.css           stili (tema chiaro/scuro)
app.js              logica: globo, timeline, pannello zona, stima voli
data/
  zones.json        zone surf (generato da scripts/apply_review.py)
  airports.json     aeroporti di partenza
  scale.json        scala qualità Flat → Epic (indice 0-9, colore)
  flight-estimate.json  parametri della stima finta di ore di volo e prezzi
  land-50m.json     coste Natural Earth 1:50m (world-atlas, TopoJSON)
  land-110m.json    coste 1:110m, usate durante trascinamento e animazioni
  review/
    zones_candidates.csv   zone candidate da revisionare a mano (Excel)
  raw/              download grezzi, non versionati (spot, OurAirports)
scripts/
  build_zones.py    spot grezzi -> zone candidate (CSV)
  apply_review.py   CSV revisionato -> data/zones.json
requirements.txt    dipendenze Python degli script (shapely)
README.md
DIARIO.md           diario di lavoro
CLAUDE.md           istruzioni per Claude Code
```

## Avvio in locale

I dati sono caricati con `fetch`, quindi serve un server (aprire il file direttamente non funziona):

```
python3 -m http.server 8000
```

poi http://localhost:8000

## Zone (fase 2)

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_zones.py      # scarica gli spot se mancano, scrive data/review/zones_candidates.csv
# revisione in Excel: colonna "tieni" = si per le zone da usare, nome e note a piacere
.venv/bin/python scripts/apply_review.py     # scrive data/zones.json
```

`build_zones.py` non sovrascrive un CSV già revisionato (serve `--force`). `apply_review.py --preseleziona N` segna "si" sulle N zone con più spot, utile come punto di partenza.

Fonti: spot dal gist pubblico di naotokui (~5900 spot), coste Natural Earth, aeroporti OurAirports.

## Fasi

1. **Base** — prototipo trasformato in progetto: file separati, dati in JSON, GitHub Pages. *(completata)*
2. **Zone** — zone reali da ~5900 spot: pulizia, clustering, esposizione della costa, aeroporto di riferimento, revisione a mano. *(in corso)*
3. **Onde ERA5** — medie storiche 20-30 anni da ERA5 Copernicus, calcolate offline in un JSON per zona e settimana; sostituisce `getZoneWeeks()`.
4. **Ore di volo** — aeroporti e rotte da OurAirports al posto della stima da distanza.
5. **Prezzi** — prezzi reali da Travelpayouts, oppure raccolta periodica salvata su Supabase.

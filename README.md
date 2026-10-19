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
  climate.json      climatologia settimanale per zona (generato da scripts/build_climate.py)
  quality-rule.json soglie della regola qualità (Flat → Epic)
  airports.json     aeroporti di partenza
  scale.json        scala qualità Flat → Epic (indice 0-9, colore)
  flight-estimate.json  parametri della stima finta di ore di volo e prezzi
  land-50m.json     coste Natural Earth 1:50m (world-atlas, TopoJSON)
  land-110m.json    coste 1:110m, usate durante trascinamento e animazioni
  review/
    zones_candidates.csv   zone candidate da revisionare a mano (Excel)
  raw/              download grezzi, non versionati (spot, OurAirports, onde orarie)
scripts/
  build_zones.py    spot grezzi -> zone candidate (CSV)
  apply_review.py   CSV revisionato -> data/zones.json
  fetch_waves.py    onde e vento orari 2005-2024 da Open-Meteo (ERA5)
  era5_cds.py       stesso formato da Copernicus CDS, più costi e prove
  build_climate.py  dati orari + regola qualità -> data/climate.json
requirements.txt    dipendenze Python degli script
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
# revisione in Excel: "tieni" = si per le zone da usare; "nome_manuale" ("Nome" o "Nome · Regione")
# ed "esposizione_manuale" (gradi 0-359), se compilate, sostituiscono i valori calcolati; "note" libera
.venv/bin/python scripts/apply_review.py     # scrive data/zones.json
```

`build_zones.py` non sovrascrive un CSV già revisionato (serve `--force`). `apply_review.py --preseleziona N` segna "si" sulle N zone con più spot, utile come punto di partenza.

Fonti: spot dal gist pubblico di naotokui (~5900 spot), coste Natural Earth, aeroporti OurAirports.

## Onde (fase 3)

```
.venv/bin/python scripts/fetch_waves.py --zone <id>      # Open-Meteo, ~3 min e ~313 chiamate a zona
.venv/bin/python scripts/era5_cds.py scarica --zone <id> # oppure Copernicus (serve chiave CDS)
.venv/bin/python scripts/build_climate.py --verifica <id>
```

La regola qualità si tara solo in `data/quality-rule.json`. Fonte: ERA5 2005-2024, ore di luce, onda totale al largo (niente swell separato) e vento a 10 m nella cella di mare sulla costa.

## Fasi

1. **Base** — prototipo trasformato in progetto: file separati, dati in JSON, GitHub Pages. *(completata)*
2. **Zone** — zone reali da ~5900 spot: pulizia, clustering, esposizione della costa, aeroporto di riferimento, revisione a mano. *(completata)*
3. **Onde ERA5** — climatologia 2005-2024 da ERA5 (Open-Meteo per il collaudo, Copernicus CDS per tutte le zone), regola qualità in JSON, `climate.json` letto da `getZoneWeeks()`. *(in corso: 5 zone di collaudo fatte)*
4. **Ore di volo** — aeroporti e rotte da OurAirports al posto della stima da distanza.
5. **Prezzi** — prezzi reali da Travelpayouts, oppure raccolta periodica salvata su Supabase.

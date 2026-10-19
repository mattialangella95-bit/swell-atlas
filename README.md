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
  zones.json        zone surf: coordinate, aeroporto, parametri demo
  airports.json     aeroporti di partenza
  scale.json        scala qualità Flat → Epic (indice 0-9, colore)
  flight-estimate.json  parametri della stima finta di ore di volo e prezzi
  land-50m.json     coste Natural Earth 1:50m (world-atlas, TopoJSON)
  land-110m.json    coste 1:110m, usate durante trascinamento e animazioni
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

## Fasi

1. **Base** — prototipo trasformato in progetto: file separati, dati in JSON, GitHub Pages. *(completata)*
2. **Zone** — lista zone ampliata e curata (spot, coordinate, aeroporto di riferimento).
3. **Onde ERA5** — medie storiche 20-30 anni da ERA5 Copernicus, calcolate offline in un JSON per zona e settimana; sostituisce `getZoneWeeks()`.
4. **Ore di volo** — aeroporti e rotte da OurAirports al posto della stima da distanza.
5. **Prezzi** — prezzi reali da Travelpayouts, oppure raccolta periodica salvata su Supabase.

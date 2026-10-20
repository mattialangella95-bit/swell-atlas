# Swell Atlas

Atlante delle stagioni surf: un globo con le zone colorate per qualità media dell'onda, settimana per settimana, più una stima di ore di volo e prezzo dall'Italia. È una statistica storica per scegliere *quando* partire, non una previsione.

Sito statico (HTML + CSS + JS, nessun build), pubblicato su GitHub Pages. Librerie da CDN: D3 7 e topojson-client 3.

Online: https://mattialangella95-bit.github.io/swell-atlas/

## Struttura

```
index.html          markup
style.css           stili (tema chiaro/scuro)
app.js              logica: globo, timeline, pannello zona, stima voli
auth.js             accesso con email e password (Supabase Auth), come Piano alimentare
profile.js          profilo e preferiti
feedback.js         segnalazioni
admin.js            segnalazioni dentro il profilo, solo per gli admin
calendar.js         vista Calendario (mese e anno) · calendar.css i suoi stili
prices.js           prezzi voli indicativi da Supabase (swell_prices), con la stima come riserva
.github/workflows-da-attivare/prezzi.yml  raccolta settimanale dei prezzi
supabase-config.js  URL e chiave anon di Supabase (vuoti = account disattivati)
supabase/migrations/ SQL delle tabelle swell_* con Row Level Security
.env.example        nomi delle chiavi per gli script (.env resta fuori da git)
data/
  zones.json        zone surf (generato da scripts/apply_review.py)
  zone-ids.json     registro degli id zona stabili (generato da scripts/build_zones.py)
  climate.json      climatologia settimanale per zona (generato da scripts/build_climate.py)
  quality-rule.json soglie della regola qualità (Flat → Epic) e altezza massima per livello surf
  calendar.json     fasce di ore di volo e nomi d'aeroporto della vista Calendario
  prices.json       partenze, mesi, valuta e ritmo della raccolta prezzi
  airports.json     partenze italiane (generato da scripts/build_airports.py)
  scale.json        scala qualità Flat → Epic (indice 0-9, colore)
  flight-estimate.json  parametri della stima di ore di volo e scali, prezzi finti
  land-50m.json     coste Natural Earth 1:50m (world-atlas, TopoJSON)
  land-110m.json    coste 1:110m, usate durante trascinamento e animazioni
  review/
    zones_candidates.csv   zone candidate da revisionare a mano (Excel)
  raw/              download grezzi, non versionati (spot, OurAirports in raw/airports, onde orarie)
scripts/
  build_zones.py    spot grezzi -> zone candidate (CSV)
  build_airports.py OurAirports -> partenze italiane (data/airports.json)
  apply_review.py   CSV revisionato -> data/zones.json (con airport_main e airport_local)
  fetch_waves.py    onde e vento orari 2005-2024 da Open-Meteo (ERA5)
  era5_cds.py       stesso formato da Copernicus CDS, più costi e prove
  build_climate.py  dati orari + regola qualità -> data/climate.json
  feedback.py       legge le segnalazioni e ne cambia lo stato (chiave di servizio da .env)
  test_rls.py       collaudo dei permessi Supabase con utenti di prova (anche admin)
  admin.py          aggiunge o toglie gli admin che vedono le segnalazioni nell'app
  fetch_prices.py   prezzi indicativi da Travelpayouts -> swell_prices (GitHub Actions, settimanale)
requirements.txt    dipendenze Python degli script
README.md
DIARIO.md           diario di lavoro
CLAUDE.md           istruzioni per Claude Code
```

## Avvio in locale

Dal Finder: doppio clic su `Apri in locale.command` (avvia il server e apre il browser; per spegnerlo chiudi la finestra del Terminale). Da terminale:

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
# "esposizione_manuale" (gradi 0-359) e "aeroporto_manuale" (IATA), se compilate, sostituiscono i valori calcolati; "note" libera
.venv/bin/python scripts/apply_review.py     # scrive data/zones.json
```

`build_zones.py` non sovrascrive un CSV già revisionato: con `--force` lo riscrive e riporta la revisione per id. Gli id restano stabili tra un ricalcolo e l'altro (registro `data/zone-ids.json`). `apply_review.py --preseleziona N` segna "si" sulle N zone con più spot, utile come punto di partenza.

Fonti: spot dal gist pubblico di naotokui (~5900 spot), coste Natural Earth, aeroporti OurAirports.

## Onde (fase 3)

```
.venv/bin/python scripts/fetch_waves.py --crea-coda     # congela le zone in data/raw/waves/_queue.json
.venv/bin/python scripts/fetch_waves.py                  # Open-Meteo, ~3 min e ~313 chiamate a zona, tetto 9.000/giorno
.venv/bin/python scripts/fetch_waves.py --stato          # avanzamento (data/raw/waves/_progress.json)
.venv/bin/python scripts/era5_cds.py scarica --zone <id> # oppure Copernicus (serve chiave CDS)
.venv/bin/python scripts/build_climate.py --verifica <id>
```

Ripresa del download Copernicus (si ferma con `touch data/raw/waves/_stop`, salta le zone già fatte):

```
nohup .venv/bin/python -u scripts/era5_cds.py scarica >> data/raw/waves/_download_cds.log 2>&1 < /dev/null &
nohup caffeinate -i -w $! >/dev/null 2>&1 < /dev/null &
```

La regola qualità si tara solo in `data/quality-rule.json` (usa il periodo medio). Fonte: ERA5 2005-2024, ore di luce, onda totale al largo (niente swell separato) e vento a 10 m nella cella di mare sulla costa.

## Calendario

Sotto il globo: scelto un mese, le zone raggruppate per aeroporto di arrivo, per paese e regione o per ore di volo, con qualità del mese, % giorni Good+, altezza e ore di volo stimate. La vista "Anno" mostra la matrice zone × mesi. Usa i riepiloghi mensili di `climate.json`; le zone senza dati non compaiono.

## Account e segnalazioni (Supabase)

L'app funziona tutta senza account; l'accesso (email e password) serve solo per preferiti e profilo. Le segnalazioni si mandano anche senza login e si leggono solo da qui:

```
.venv/bin/python scripts/feedback.py            # nuove
.venv/bin/python scripts/feedback.py letta 3    # oppure: risolta 3
.venv/bin/python scripts/test_rls.py            # collaudo permessi
.venv/bin/python scripts/admin.py aggiungi tu@mail.it   # admin: segnalazioni anche nel profilo dell'app
```

La publishable key sta in `supabase-config.js`; la secret key solo in `.env`, mai nel repository.

## Prezzi (fase 5)

```
.venv/bin/python scripts/fetch_prices.py --prova --solo GOA-DPS MXP-HNL   # prova senza scrivere
```

Il giro completo lo farà GitHub Actions ogni lunedì: il workflow è pronto in `.github/workflows-da-attivare/prezzi.yml` e va spostato in `.github/workflows/` quando ci sono i secret con i secret `TRAVELPAYOUTS_TOKEN` e `SUPABASE_SECRET_KEY`. Il token non va mai nel sito. Nell'app i prezzi sono sempre "indicativi" (rilevati) o "stima".

## Fasi

1. **Base** — prototipo trasformato in progetto: file separati, dati in JSON, GitHub Pages. *(completata)*
2. **Zone** — zone reali da ~5900 spot: pulizia, clustering, esposizione della costa, aeroporto di riferimento, revisione a mano. *(completata)*
3. **Onde ERA5** — climatologia 2005-2024 da ERA5 (Open-Meteo per il collaudo, Copernicus CDS per tutte le zone), regola qualità in JSON, `climate.json` letto da `getZoneWeeks()`. *(fatta: 150 zone su 150; resta la taratura della regola)*
4. **Ore di volo** — aeroporto principale e locale per zona da OurAirports, partenza da tutti gli aeroporti italiani, ore e scali stimati con parametri in `data/flight-estimate.json`. *(fatta, stima senza rotte vere)*
5. **Prezzi** — prezzi indicativi dalla cache di Aviasales (Travelpayouts), raccolti ogni settimana da GitHub Actions in `swell_prices` su Supabase; storico per vedere la stagionalità vera. *(codice pronto; mancano token, migrazione e collaudo)*

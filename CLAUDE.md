# Swell Atlas — note per Claude

Progetto hobby di Mattia. Rispondi in italiano.

## Cos'è
Sito statico su GitHub Pages (account `mattialangella95-bit`, repo `swell-atlas`): globo D3 ortografico con zone surf colorate per qualità media settimanale (52 settimane, scala Flat → Epic), più stima ore di volo e prezzo dagli aeroporti italiani. Stessa architettura di Sala Aste: niente framework, niente build.

## Stile dell'interfaccia
- Scrivere come una persona: frasi brevi in italiano ("6 giorni buoni su 10", "5½ h di volo"), niente sigle tipo "Good+", niente maiuscoletto spaziato o numeri monospace, pochi bordi e badge.
- Una cosa importante per riga, il resto in grigio sotto. Controlli rari dentro "Filtri" o altri `details`.
- Provare sempre anche a 400 px di larghezza.

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
- Gli id zona sono stabili grazie a `data/zone-ids.json`: preferiti e segnalazioni su Supabase li usano. Non cancellare righe dal registro e non rinominare id a mano; le zone confluite restano raggiungibili come `aliases`.
- Il CSV di revisione è di Mattia: non sovrascriverlo se ha `nome_manuale`, `esposizione_manuale`, `tieni` o `note` compilati. Le colonne `*_manuale` vincono su quelle calcolate.
- `data/raw/` contiene solo download, non è versionata.
- Onde: le soglie della regola qualità stanno solo in `data/quality-rule.json`, mai nel codice. I dati orari passano dal formato intermedio parquet (`data/raw/waves/<id>.parquet`) sia da Open-Meteo (`fetch_waves.py`) sia da Copernicus (`era5_cds.py`); `build_climate.py` scrive `data/climate.json`.
- Open-Meteo gratuito: 10.000 chiamate al giorno, una zona da 20 anni ne vale circa 313. Niente download massivi senza chiedere.
- Il download gira staccato dalla sessione e legge solo `data/raw/waves/_queue.json`. Stato: `.venv/bin/python scripts/fetch_waves.py --stato`; stop: `kill $(python3 -c "import json;print(json.load(open('data/raw/waves/_progress.json'))['pid'])")`. Non lanciarne un secondo in parallelo.
- Prima di cambiare soglie, mostra la tabella mese per mese delle 5 zone di collaudo (`build_climate.py --verifica ...`) e spiega il perché.

## Calendario
- `calendar.js` legge solo `climate.json` (campo `months`) e i parametri in `data/calendar.json` e `quality-rule.json` (`levels`); la stima voli è quella di `app.js` (`app.flight`), non va duplicata.
- `app.js` espone gli agganci (`app`, `app.hooks`, `app.user`); le viste nuove stanno in file propri.

## Voli
- Ore e scali sono stimati, mai presentati come reali: nella scheda sempre "stimato".
- Tutti i parametri (velocità, tempi fissi, coincidenze, fasce di scali, hub, eccezioni) stanno in `data/flight-estimate.json`. Se il collaudo da Genova e Malpensa sbaglia di oltre il 15%, si correggono i parametri, non il codice.
- Le zone hanno `airport_main` (usato per i voli) e `airport_local`. Le partenze italiane si rigenerano con `scripts/build_airports.py`.

## Supabase
- Progetto dedicato "Swell Atlas": `https://macixwnxvlyhqbqvypao.supabase.co`, chiavi nuove (publishable e secret, non le legacy anon/service_role).
- Tabelle solo con prefisso `swell_` (il progetto può essere condiviso con altre app). Ogni modifica allo schema è una nuova migrazione in `supabase/migrations/`, che esegue Mattia; non modificare le migrazioni già eseguite.
- Row Level Security sempre attiva: profilo e preferiti solo propri, segnalazioni solo in inserimento.
- La publishable key può stare in `supabase-config.js`; la secret key MAI nel repository o nel codice del sito, solo in `.env` (in `.gitignore`). Non leggere né stampare `.env`.
- L'app deve funzionare tutta senza login e anche con `supabase-config.js` vuoto. Le funzioni di account stanno in `auth.js`, `profile.js` e `feedback.js`; `app.js` espone solo gli agganci.

## Prezzi
- Fonte: API dati di Travelpayouts (cache Aviasales). Il token sta solo in `.env` o nei secret di GitHub (`TRAVELPAYOUTS_TOKEN`), mai nel sito.
- `swell_prices` è uno storico: si aggiungono righe, non si aggiornano né cancellano. L'app legge `swell_prices_latest`.
- Nell'interfaccia un prezzo è sempre "indicativo" o "stima": niente link, pulsanti o parole che lo facciano sembrare prenotabile.
- Limite Travelpayouts: 600 richieste al minuto per i metodi v3; lo script va a 8 al secondo.

## Test in locale
`python3 -m http.server 8000` e apri http://localhost:8000 (con `file://` il fetch fallisce).

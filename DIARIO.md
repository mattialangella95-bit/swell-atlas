# Diario

## 2026-10-22 — Finestra "Novità"

### Fatto
- `news.js` + `data/news.json`, come in Piano alimentare: alla prima apertura dopo un aggiornamento si mostrano le novità non ancora viste (al massimo 3 voci), poi mai più; il link "Novità" in fondo alla pagina le riapre.
- Diversamente da Piano alimentare, la "vista" si ricorda nel browser e non nel profilo, perché qui quasi tutti entrano senza account. Quindi la vede una volta anche chi apre il sito per la prima volta. Se il browser non permette di ricordarlo (navigazione privata) non si mostra, per non comparire a ogni apertura.
- Prima voce "Ottobre 2026": le novità delle segnalazioni e la spiegazione sui dati live.
- Collaudo: compare alla prima apertura, non alla seconda, si riapre dal link; 400 px leggibile; nessun errore.


## 2026-10-22 — Segnalazioni: correzioni di forma, filtri, A/R, costo della vita

### Fatto
- Lette le segnalazioni #11-#23 e fatto il resoconto. Decisioni di Mattia:
  - niente proposta di nuovi spot (#18);
  - niente dati live (#19, #21): va spiegato all'amico;
  - le cose facili subito; i download pesanti (temperature) da combinare dopo.
- Barra colorata dell'anno trascinabile: tocco o trascinamento del dito (#23).
- Settimana di oggi: bordo rosso nella barra dell'anno e "· questa settimana" nella timeline (#11).
- Prezzi:
  - sempre con "A/R" o "solo andata" (#20);
  - scelta "A/R / solo andata" nella sezione Volo, ricordata nel browser;
  - la sola andata per ora è una stima, pari al 60% dell'andata e ritorno (`oneWayFactor` in `flight-estimate.json`), finché la fase 5 non rileva prezzi veri di sola andata.
- Filtri della pagina Mondo sotto la timeline, in "Filtri" (#22):
  - "Onde adatte a" (livello, con `levels` di `quality-rule.json` sul 75° percentile della settimana);
  - "Misura delle onde" (fasce in `data/filters.json`);
  - nascondono gli spot su globo, tendine e lista, e si aggiornano cambiando settimana.
- Filtri del calendario: misura delle onde, prezzo fino a, costo della vita (#20).
- Costo della vita €/€€/€€€ rispetto all'Italia (#11):
  - `scripts/build_costs.py` → `data/costs.json`, dati Banca Mondiale 2025 (PPP / cambio, `PA.NUS.PPP` / `PA.NUS.FCRF`; l'indicatore diretto è stato archiviato);
  - fasce: sotto 0,7 €, fino a 1,1 €€, oltre €€€;
  - Isole Vergini britanniche, Polinesia francese e Saint-Barth senza dato: €€€ a mano;
  - si vede nella scheda ("· vita €€", con spiegazione), nella tendina Paese e nei gruppi per paese del calendario.
- Collaudo nel browser headless: trascinamento dalla settimana 1 alla 32, filtri, prezzi, costi, 400 px senza sforamenti, nessun errore.

### Aperti
- Mappa nel Calendario (#17): da decidere se planisfero piatto o globo.
- Temperature di acqua e aria (#11): download di circa 3-4 ore, da combinare.
- Prezzi di sola andata veri e filtro sul prezzo reale: con la fase 5.


## 2026-10-20 — Tendine Paese e Spot

### Fatto
- Corretta l'interpretazione della segnalazione dell'amico: scegliendo un paese si vuole vedere solo i suoi spot, con la mappa che ci gira sopra (prima la lista mostrava tutti gli spot, raggruppati).
- Sopra il globo due tendine, Paese e Spot. Scegliendo un paese (dalla tendina o toccandolo sul globo):
  - il globo ruota e zooma per inquadrare i suoi spot, e il paese si colora;
  - la tendina Spot si riempie dal migliore al peggiore per la settimana scelta (giorni buoni, a parità la classe);
  - si apre lo spot migliore.
- Toccando uno spot si apre lui e il suo paese va nelle tendine. Cambiando settimana l'ordine si aggiorna.
- Sotto il globo, "Spot in <paese>": solo gli spot del paese scelto, dal migliore. Senza paese, l'invito a sceglierne uno.
- Collaudo:
  - Portugal apre Buarcos, il migliore della settimana 42 secondo i dati (58%);
  - tocco su Spagna e Francia vuote: si aprono Bastiagueiro e Le Penon con 8 e 10 spot;
  - settimana 3: A-ver-o-mar in testa;
  - dal calendario Medewi porta Indonesia nelle tendine;
  - 400 px senza sforamenti, nessun errore.


## 2026-10-20 — Pagine Mondo e Calendario, periodo a giorni, paese dalla mappa

### Fatto
- Due pagine con linguette in alto, Mondo e Calendario (`pages.js`). La pagina sta nell'indirizzo (`#calendario`); il clic su una zona del calendario riporta al Mondo con la scheda aperta.
- Mondo: globo, scheda, timeline e, al posto del calendario, "Le zone, paese per paese" (gruppi per paese con il colore della settimana; "Solo preferiti" con login).
- Paese dalla mappa (`data/countries-110m.json`, confini world-atlas):
  - qualunque tocco porta in testa alla lista il paese toccato;
  - su uno spot si apre la scheda e la pagina non scorre;
  - su un punto vuoto il paese si colora sul globo e la pagina scorre alla lista;
  - isole piccole senza confini a questa scala (Maldive, Barbados): vale la zona più vicina entro 500 km;
  - "mostra tutti in ordine" toglie la selezione.
  - Il test aveva mostrato che a zoom normale gli spot sono così fitti che toccando il Portogallo si prendeva sempre uno spot: per questo anche il tocco su uno spot porta in testa il suo paese.
- Calendario: oltre ai mesi, "oppure dal … al …" a giorno. I dati sono per settimana: ogni settimana pesa quanti giorni cadono nel periodo (% giorni buoni e altezze in media pesata, classe del giorno tipico come mediana pesata); il prezzo è quello del mese a metà periodo. Funziona anche a cavallo d'anno.
  - 5-19 agosto: in testa 4 Bobs, Herolds Bay, Tropical's, Blinkklip Reef.
  - 28 dicembre-10 gennaio: Klamath Rivermouth, Scott's Creek, Oubaha, Double point.
- Corretto "Dove andare a agosto" in "ad agosto" (anche aprile e ottobre).
- Collaudo nel browser headless: pagine, tocco su Portogallo, Maldive e Hawaii, periodi, clic che riporta al Mondo, 400 px senza sforamenti su entrambe le pagine, nessun errore.


## 2026-10-20 — Download onde completato

### Fatto
- Download ripreso alle 11:20 dal comando del diario, finito alle 13:00: **150 zone su 150**, nessuna saltata, circa 2 minuti a zona, un paio di errori di rete superati da soli. Download e `caffeinate` si sono chiusi da soli.
- `climate.json` ricostruito con tutte le zone (285 KB, settimane e mesi). Le 5 zone di collaudo sono invariate (es. Graters gen 72% / lug 0%, Medewi gen 37% / lug 90%).
- Calendario completo: 150 zone; in luglio in testa Mentawai, Sudafrica (George, Città del Capo), Lombok, Australia occidentale.
- Controlli prima del push: nessun segreto nei 6 commit nuovi, `data/raw` fuori da git, nessun errore in console, 400 px senza sforamenti.

### Aperti
- 12 zone non sono mai "buone" in nessun mese, tutte in mari chiusi o con onda corta: Langevelderslag, Bay of Heist, Sunset Beach, Garraf, Cap Blanc Nez, 3-poles reef, Deep Creek, Playa Grande, Il Convento, Calita, Bexhill, Batts Rock. Da guardare nella taratura (periodo minimo, onde corte).


## 2026-10-20 — Accesso con email e password, come Piano alimentare

### Fatto
- Letti in sola lettura `piano-alimentare` e `sala-aste` su GitHub. Piano alimentare entra con email e password, ha il cambio password nel profilo e mostra all'amministratore una striscia "N segnalazioni nuove". Lo schema admin (tabella `amministratori` + regole) era già uguale al nostro.
- Il solo link via mail non andava bene: le app di posta aprono il link nel loro browser interno e l'accesso resta lì.
- Nuovo accesso (`auth.js`):
  - email e password, "Entra" e "Crea account": la mail serve solo una volta per confermare l'account, poi si entra con la password da qualsiasi browser;
  - "Password dimenticata?": manda una mail per sceglierne una nuova, e all'arrivo si apre subito "Scegli una password";
  - messaggi d'errore in italiano, presi da Piano alimentare.
- Profilo: "Nuova password" con il pulsante "Cambia".
- Admin: striscia in cima alla pagina "📬 N segnalazioni nuove · Apri", che si ricontrolla quando si torna sulla pagina.
- Collaudo nel browser headless con un utente di prova (creato e poi cancellato): password sbagliata, entrata, striscia con le 2 segnalazioni, elenco, cambio password, uscita; 400 px senza sforamenti; nessun errore. Non provati "Crea account" e "Password dimenticata?", per non mandare mail vere.

### Aperti
- Il tuo account è nato con il link e non ha una password: la prima volta usa "Password dimenticata?".


## 2026-10-20 — Segnalazioni nel profilo admin

### Fatto
- Prima segnalazione vera arrivata (#11, anonima, da iPhone, 20/10 00:13): temperatura di acqua e aria, finestra di più settimane, settimana di oggi evidenziata, costo della vita €/€€/€€€, zoom animato sul paese cliccato. Lasciata "nuova".
- Migrazione `20261020120000_swell_admin.sql`: tabella `swell_admins` (si scrive solo via SQL o secret key), funzione `swell_is_admin()`, regole nuove su `swell_feedback`: gli admin leggono e cambiano solo lo stato; utenti normali e visitatori continuano a non vedere nulla.
- `scripts/admin.py`: elenco, `aggiungi <email>`, `togli <email>` (l'utente deve essere entrato una volta nell'app).
- `admin.js`: se l'utente è admin, nel profilo compare "Segnalazioni (N nuove)". Si aprono elenco e filtro "solo le nuove"; per ognuna tipo, testo, zona, settimana, partenza e telefono o no, con "Apri la zona", "Segna come letta" o "risolta", "Rimetti come nuova". I testi si mostrano solo come testo, mai come HTML.
- `test_rls.py`: 7 controlli admin in più, saltati finché la migrazione non è eseguita.

- Migrazione admin eseguita da Mattia; `mattialangella95@gmail.com` aggiunto come admin. `test_rls.py`: 27/27 controlli superati (7 nuovi sull'admin).

- `Apri in locale.command`: doppio clic dal Finder per avviare il sito su http://localhost:8000 (con login e segnalazioni). Con `file://` non può funzionare: Chrome blocca i file JavaScript con origine "null" (CORS), verificato.

### Aperti
- Il pannello admin è nei commit locali: sul sito pubblicato compare dopo il push.


## 2026-10-20 — Colori coerenti tra globo e calendario

### Fatto
- Problema: il globo colora la zona con la classe della settimana, il calendario con quella del mese, e la classe era la più frequente (moda). La moda salta tra classi lontane: una zona con il 22% di giorni buoni risultava "Flat". Globo e calendario differivano di 2 o più classi nel 9% delle settimane (233 su 2.652).
- Correzione in `build_climate.py`: la classe mostrata è quella del giorno tipico, cioè la mediana dei giorni. Differenze di 2 o più classi: 8 su 2.652 (0%). La % di giorni buoni non cambia.
- Verifica sull'Europa (settimana 42 / ottobre): 12 zone su 15 con lo stesso colore, le altre 3 a un gradino di distanza, perché la settimana è un po' diversa dalla media del mese. A metà ottobre l'Europa è soprattutto verde-giallo e giallo; l'arancione ("Very Good") compare in inverno.


## 2026-10-19 sera — Chiusura di giornata

### Fatto
- Download onde fermato alle 23:29, appena chiusa la zona `france-st-jean-de-monts`: **51 zone su 150** con dati, 99 mancanti, prossima `spain-montalvo-beach`. Nessun file a metà; `_progress.json` salvato con stato "fermato dopo la zona in corso".
- `era5_cds.py scarica` ora:
  - salta le zone già fatte;
  - si ferma pulito con `touch data/raw/waves/_stop`, prima della zona successiva, dicendo quale sarebbe;
  - con kill o Ctrl-C salva lo stato.
  - Ripresa provata senza scaricare: salta le 51 zone fatte e riparte da `spain-montalvo-beach`.
- `climate.json` ricostruito: 51 zone con settimane e mesi, 99 "dati in arrivo".
- Collaudo locale prima del push, senza errori in console:
  - zona senza dati grigia con "Dati in arrivo";
  - stella senza login che apre l'accesso;
  - segnalazione arrivata nel database e poi cancellata;
  - 400 px senza sforamenti, sia nella vista mese sia nella vista anno.
  - L'unico avviso rimasto riguarda i prezzi, che non ci sono finché non si esegue la migrazione `swell_prices`.
- Corretto: con chiamate contemporanee si creavano due client Supabase (avviso "Multiple GoTrueClient instances"); ora si memorizza la promessa.
- Controllo segreti su tutta la cronologia (18 commit): nessuna secret key Supabase, nessun token Travelpayouts, nessuna chiave Copernicus, nessun `.env` o `.cdsapirc`; `data/raw` mai tracciato. Unica chiave presente la publishable, pubblica per natura.

- Push: GitHub ha rifiutato il primo tentativo perché il token di `gh` non ha il permesso `workflow`. Il workflow dei prezzi (inutile finché mancano i secret) è stato spostato nei commit non pubblicati in `.github/workflows-da-attivare/prezzi.yml`: stesso contenuto, cartella che GitHub non esegue. Ramo locale `backup-prima-del-push` con la versione originale.

- Push fatto (`5ccc6a5..568572b`, 16 commit). Sito pubblicato verificato: si apre, carica i dati (51 zone con dati, 99 "in arrivo"), calendario con 51 righe, nessun errore in console.
- Processi fermati: download Copernicus (PID 5884) e il suo `caffeinate` (5885), lo script che avrebbe ricostruito il clima a fine download (6670), il server locale sulla porta 8000 (8545). Le porte 8000, 8765 e 9333 sono libere: niente del progetto resta attivo.

### Ripresa del download (comando esatto)
```
cd /Users/mattia/Documents/swell-atlas
nohup .venv/bin/python -u scripts/era5_cds.py scarica >> data/raw/waves/_download_cds.log 2>&1 < /dev/null &
nohup caffeinate -i -w $! >/dev/null 2>&1 < /dev/null &
```
- Stato: `.venv/bin/python scripts/fetch_waves.py --stato`
- Fermare dopo la zona in corso: `touch data/raw/waves/_stop`
- A download finito: `.venv/bin/python scripts/build_climate.py`, poi commit di `data/climate.json`.
- Ritmo: circa 75-125 s a zona, quindi per le 99 zone mancanti circa 2-3 ore.

### Prossimi passi (domani, in quest'ordine)
1. Calendario: rivederlo con più zone e ritoccare dove serve.
2. Fase 5 prezzi: token Travelpayouts in `.env`, migrazione `20261020090000_swell_prices.sql`, collaudo su GOA-DPS, MXP-HNL, PSA-LIS; poi `gh auth refresh -h github.com -s workflow`, secret `TRAVELPAYOUTS_TOKEN` e `SUPABASE_SECRET_KEY` su GitHub, `git mv .github/workflows-da-attivare/prezzi.yml .github/workflows/prezzi.yml` e push.
3. Ripresa del download onde con il comando qui sopra, poi `build_climate.py`.


## 2026-10-20 — Fase 5, prezzi voli indicativi

### Fatto
- Verifica di Travelpayouts (Aviasales Data API), ottobre 2026:
  - gratuita con token, dopo l'iscrizione a Travelpayouts ("Access is allowed without restrictions, but you must have a token");
  - prezzi dalla cache delle ricerche degli utenti Aviasales, conservati da 2 a 7 giorni (le tratte poco cercate possono avere mesi vuoti);
  - limiti per minuto (dal 14/06/2024): 600 al minuto per `/aviasales/v3/prices_for_dates` e `/aviasales/v3/grouped_prices`, nessun tetto giornaliero dichiarato; oltre il limite risponde 429 per il resto del minuto;
  - nessun obbligo di attribuzione trovato nella documentazione né nei Termini; si indica comunque la fonte.
- Metodo scelto: `prices_for_dates` con `one_way=false` e `departure_at=AAAA-MM`. Una chiamata per tratta e mese, offerte di andata e ritorno: minimo, mediana, numero di offerte. Mercato `it`, euro (`data/prices.json`).
- Giro: 10 partenze × 115 aeroporti principali = 1.150 tratte (meno quelle con partenza uguale all'arrivo) × 12 mesi = circa 13.800 chiamate, a 8 al secondo (480 al minuto, sotto le 600): circa 29 minuti a settimana.
- `supabase/migrations/20261020090000_swell_prices.sql`: tabella `swell_prices` solo in aggiunta (storico), lettura per tutti, scrittura solo con la secret key; vista `swell_prices_latest` (ultima rilevazione per tratta e mese, `security_invoker`).
- `scripts/fetch_prices.py` (solo libreria standard): token da `TRAVELPAYOUTS_TOKEN`, scrive a blocchi di 500 righe con la stessa data di rilevazione; `--prova` e `--solo GOA-DPS ...` per i collaudi.
- `.github/workflows-da-attivare/prezzi.yml`: ogni lunedì alle 04:17 UTC e a mano; secret `TRAVELPAYOUTS_TOKEN` e `SUPABASE_SECRET_KEY`.
- Nizza (NCE) aggiunta alle partenze dell'app come partenza di confine, altrimenti i suoi prezzi non si vedrebbero.
- App: `prices.js` legge `swell_prices_latest` per la partenza scelta (publishable key, senza login). Scheda e calendario mostrano "circa X € indicativi" con la data di rilevazione (mediana delle offerte, altrimenti minimo), oppure "stima". Barre piene se rilevate, tratteggiate se stimate. Mai link o parole da offerta prenotabile.

### Aperti
- Collaudo sulle 3 tratte (GOA-DPS, MXP-HNL, PSA-LIS) in attesa del token Travelpayouts e della migrazione dei prezzi.
- GitHub sospende i workflow pianificati dopo 60 giorni senza attività nel repository: se il progetto resta fermo, va riattivato dalla scheda Actions.


## 2026-10-19 — Collaudo Supabase

### Fatto
- Migrazione eseguita da Mattia sul progetto "Swell Atlas"; secret key in `.env` verificata (tipo `sb_secret_`, API admin 200) senza stamparla.
- `scripts/test_rls.py`: 20/20 controlli superati con due utenti di prova. Ognuno vede e modifica solo profilo e preferiti propri; senza login non si vede nulla; le segnalazioni anonime entrano ma non si leggono né si modificano con la publishable key né da utente; niente segnalazioni a nome di altri o già "risolte"; con la secret key si leggono.
- Corretto un errore dello script: il marcatore delle righe di prova conteneva uno spazio non codificato nell'URL. Il primo giro si era fermato dopo 18 controlli superati senza pulire; avanzi (2 utenti, 2 segnalazioni) cancellati a mano con la secret key, profili e preferiti erano già spariti in cascata.
- `feedback.py --tutte`: nessuna segnalazione, il progetto è pulito.


## 2026-10-19 — Chiavi Supabase

### Fatto
- Progetto Supabase dedicato "Swell Atlas" (`https://macixwnxvlyhqbqvypao.supabase.co`), chiavi nuove (non legacy). URL e publishable key in `supabase-config.js` (costante rinominata `SUPABASE_PUBLISHABLE_KEY`) e in `.env`.
- Verifiche:
  - `/auth/v1/settings` risponde con la publishable key, accesso via email attivo;
  - nell'app supabase-js 2.116.0 crea il client e apre la sessione senza errori, e la richiesta arriva al database;
  - le tabelle `swell_*` non esistono ancora: la migrazione va eseguita.
- La publishable key può stare nel codice: è pubblica, i permessi li decide la RLS.
- `.env` creato (fuori da git, verificato con `git check-ignore`, permessi 600) con publishable key, URL vuoto e riga della secret key vuota con le istruzioni.
- Variabili allineate ai nomi nuovi di Supabase: `SUPABASE_PUBLISHABLE_KEY` e `SUPABASE_SECRET_KEY` (i vecchi `SUPABASE_ANON_KEY` e `SUPABASE_SERVICE_ROLE_KEY` restano validi). Le chiavi `sb_…` non sono JWT: gli script le mandano solo nell'header `apikey`.
- supabase-js portato da 2.45.4 (2024, prima delle publishable key) a 2.116.0.


## 2026-10-19 — Revisione dello stile

### Fatto
- Calendario riscritto per leggersi come un testo:
  - titolo "Dove andare a luglio", mesi come linguette;
  - "Raggruppa per aeroporto · paese · ore di volo" e "Vedi il mese · tutto l'anno" come scelte testuali; filtri chiusi in "Filtri";
  - gruppi con il nome della città ("Bali · DPS · 23½ h di volo") e una frase sola ("2 zone buone su 3. La migliore è …");
  - righe con barra colorata, "6 giorni buoni su 10", qualità, onde e volo in una riga sotto;
  - colonna di lettura larga al massimo 760 px; nomi d'aeroporto più noti in `data/calendar.json` (`airportNames`: Bali, Lisbona, Città del Capo…).
- Pagina:
  - sottotitolo al posto del badge tratteggiato; etichette normali al posto del maiuscolo spaziato; numeri nel font del testo invece che monospace;
  - "Giorni buoni" invece di "Giorni Good+"; note e piè di pagina più corti;
  - i 150 bottoni delle zone chiusi in "Tutte le zone".
- `zones.json`: l'aeroporto principale ha anche la città (`city`).
- Corretto un errore del globo: con il riquadro misurato quasi a zero durante un ridimensionamento il raggio diventava negativo e il disegno andava in errore.
- Dati: `climate.json` ricostruito con le zone arrivate (27). Un processo staccato aspetta la fine del download Copernicus e lo ricostruisce da solo (nessun commit automatico).


## 2026-10-19 — Calendario

### Fatto
- `build_climate.py`: riepilogo mensile per zona (`months` in `climate.json`, campi `monthFields`): classe prevalente, altezza 25/75, periodo mediano, % giorni Good+, vento offshore prevalente (1 se nelle ore di luce l'offshore supera l'onshore, null senza esposizione). Il regime di vento ha una funzione sola (`wind_regime`), usata anche dalla classe oraria.
- `calendar.js` + `calendar.css`, sezione "Calendario" sotto la timeline. `app.js` toccato solo per gli agganci (esporta `flight`, `SCALE`, `MESI`, `CLIMATE`, `app.user`); `profile.js` pubblica preferiti e livello.
  - 12 bottoni mese, quello corrente preselezionato;
  - raggruppamento per aeroporto di arrivo (`airport_main`, gruppi ordinati per % Good+ media), per paese e regione, per ore di volo (fasce in `data/calendar.json`: entro 4, 4-8, 8-14, oltre 14 h);
  - righe compatte: nome, chip qualità del mese, % Good+, altezza 25-75, ore di volo stimate (stessa `flight()` della scheda); riassunto in testa al gruppo (zone Good+, migliore, ore di volo);
  - filtri: qualità minima, ore di volo massime, solo preferiti (con login), livello;
  - clic su una zona: scheda e globo ruotato lì;
  - vista "Anno": matrice zone × 12 mesi colorata con la scala, righe raggruppate, intestazione e colonna zona fisse, scorre dentro il suo riquadro.
- Livelli in `quality-rule.json` (`levels`): altezza massima indicativa principiante 1,5 m, intermedio 2,5 m, esperto nessun limite, confrontata con il 75° percentile del mese (valore al largo). Le zone oltre il limite restano visibili con "onde impegnative per il tuo livello". Con login il livello viene dal profilo.
- Collaudo, con 24 zone scaricate su 150:
  - gennaio da Genova, primi 3 gruppi per aeroporto: HNL (Graters 72%, ~24,5 h), LIS (Magoito 58%, ~5,5 h), BIO (2 zone Good+, Islares 61% e Le Penon, ~1,5 h);
  - gennaio, prime 5 entro 8 h: Islares 61%, Magoito 58%, Le Penon 54%, Boobies 38%, Oléron 34%;
  - luglio: Bali (Medewi) 1ª con 90%, Mentawai 2ª con 89%, Jeffreys Bay 5ª con 60%, North Shore 23ª su 24 con 0%;
  - 400 px: pagina larga 400 px, nessuna riga fuori, matrice che scorre dentro il riquadro; nessun errore in console;
  - livello in gennaio: avvisi su 20 zone su 24 (principiante), 10 (intermedio), 0 (esperto).

### Aperti
- Collaudo da ripetere a download finito, con tutte le 150 zone (`build_climate.py` va rilanciato).
- Soglie dei livelli da tarare: con altezze al largo il principiante vede avvisi quasi ovunque in inverno.


## 2026-10-19 — Account, preferiti e segnalazioni (Supabase)

### Fatto
- `supabase/migrations/20261019120000_swell_init.sql`, tutto con prefisso `swell_` e Row Level Security attiva:
  - `swell_profiles`: nome visualizzato, partenza preferita (IATA), livello surf, date;
  - `swell_favorites`: utente, id zona, nota, data;
  - `swell_feedback`: utente facoltativo, tipo, zona facoltativa, testo, pagina, stato dell'app, user agent, stato, data;
  - permessi: profilo e preferiti solo propri; segnalazioni inseribili da tutti (anche anonime, solo come "nuova" e mai a nome di altri), non leggibili né modificabili dall'app. Permessi di tabella ristretti al minimo (`revoke all` + `grant` espliciti).
- App, in file nuovi (`app.js` toccato solo per gli agganci: filtro zone, callback dopo il render, oggetto `app` esportato):
  - `supabase-config.js` con URL e chiave anon. Vuoti = account e segnalazioni disattivati, il resto funziona uguale (verificato: nessun errore in console);
  - `auth.js`: magic link (`signInWithOtp`) che torna alla pagina da cui si è partiti; supabase-js 2.116.0 da jsdelivr, caricato solo se configurato;
  - `profile.js`: al primo accesso crea il profilo copiando la partenza già scelta nel browser; stella sulla scheda; filtro "Solo preferiti" su lista e globo; pannello profilo con partenza, livello, nome e preferiti con nota. Gli id vecchi delle zone confluite si risolvono con gli alias;
  - `feedback.js`: bottone "Segnala" sempre visibile, tipo, zona corrente precompilata, testo, conferma dopo l'invio.
- `scripts/feedback.py`: elenca le segnalazioni nuove (o `--tutte`), `letta`/`risolta <id>`. Chiave di servizio solo da `.env`, che è in `.gitignore`; `.env.example` mostra i nomi.
- `scripts/test_rls.py`: collaudo sul progetto vero con due utenti di prova creati e poi cancellati (20 controlli).

### Aperti
- Il livello surf per ora si salva e basta.


## 2026-10-19 — Id zona stabili

### Fatto
- Verifica: gli id nascevano da paese + spot centrale del clustering, quindi cambiavano con piccole variazioni dei dati. Su 5 prove per tipo, id delle 150 zone persi:

  | Variazione | Senza registro | Con registro |
  |---|---|---|
  | tolgo l'1% degli spot | 4,0 | 0 |
  | sposto le coordinate di ~100 m | 14,0 | 0,8 |
  | aggiungo 50 spot | 4,8 | 0,4 |

- `data/zone-ids.json`: registro degli id assegnati (paese, centro, esposizione), creato dagli id attuali, che sono già usati da `zones.json`, dal clima e dai download. `build_zones.py` abbina le zone ricalcolate agli id esistenti: stesso paese, esposizione compatibile, entro 30 km e poi un secondo giro entro 60. Gli id non si riusano mai.
- Le perdite rimaste sono fusioni vere (due zone che diventano una). Il registro annota `unito_a`, `apply_review.py` mette gli id vecchi in `aliases` dentro `zones.json` e i preferiti salvati con un id vecchio finiscono sulla zona nuova.
- `build_zones.py --force` ora riporta la revisione (colonne manuali, tieni, note) nel nuovo CSV per id. Rilanciato sui dati veri: CSV e `zones.json` identici byte per byte.


## 2026-10-19 — Fase 3, passaggio a Copernicus

### Fatto
- Account CDS pronto, `prova-puntuale` sulle 5 zone di collaudo (gennaio 2020):
  - 27 s per richiesta da 1 mese (18-38 s), circa 12 KB;
  - scarto rispetto a Open-Meteo sulle stesse 744 ore: altezza 0,00-0,01 m, periodo 0,01 s, direzione 0,2-0,3°. È lo stesso ERA5, le fonti sono intercambiabili.
- Una zona completa da 20 anni (onde e vento, dataset puntuale): 74 s, contro una media di circa 50 minuti con Open-Meteo per via dei tetti di chiamate. Stima per le zone rimaste: circa 3 ore invece di circa 5 giorni.
- Open-Meteo fermato alle 22:37 dopo la zona in corso; Copernicus lanciato in background (`nohup` + `caffeinate`) sulle zone rimanenti, log in `data/raw/waves/_download_cds.log`. Ritmo misurato: circa 85 s a zona.
- `era5_cds.py scarica`:
  - legge solo `_queue.json`;
  - vento nella cella ERA5 di mare più vicina (coste Natural Earth, al posto di `cell_selection=sea`);
  - se il punto onde non ha dati prova i punti alternativi;
  - scrive lo stesso `_progress.json`, quindi `fetch_waves.py --stato` vale per entrambe le fonti.
- `fetch_waves.py`: `touch data/raw/waves/_stop` ferma il download dopo la zona in corso.
- Grecia ionica (prima zona da Copernicus): quasi sempre Flat, periodo medio 3,5-5 s. È plausibile, ma il Mediterraneo con questa regola risulterà quasi sempre scarso: da discutere nella taratura.


## 2026-10-19 — Fase 4, ore di volo

### Fatto
- `scripts/build_airports.py`: scarica `airports.csv` e `runways.csv` di OurAirports in `data/raw/airports/`. Tiene solo large e medium con voli di linea e codice IATA. Scrive le partenze italiane in `data/airports.json`: 41 aeroporti, con nome italiano per la ricerca.
- `apply_review.py`, per ogni zona:
  - `airport_local`: il più vicino con voli di linea;
  - `airport_main`: il large più vicino entro 300 km, altrimenti il medium con la pista più lunga (OurAirports non ha i passeggeri), altrimenti il locale;
  - nuova colonna `aeroporto_manuale` (IATA) nel CSV, che vince se compilata;
  - risultato: principale diverso dal locale in 55 zone su 150 (Lisbona LIS invece di CAT, Costa Rica LIR/SJO invece di Nosara e Quepos). Hossegor prende Bilbao (BIO) invece di Biarritz (BIQ): da decidere con `aeroporto_manuale`.
- Stima voli riscritta, parametri tutti in `data/flight-estimate.json`:
  - ore = distanza × (1 + 0,08 × scali) / 820 km/h + 0,5 h a tratta + 2,5 h a coincidenza;
  - scali per fascia di distanza, diversa se si parte da un hub (MXP, FCO) o da un altro aeroporto;
  - `extraStops` per gli arrivi senza voli dagli hub (per ora solo PDG +1); massimo 3 scali.
  - OurAirports classifica "large" anche Genova, Perugia e Padang, quindi il tipo non basta: hub ed eccezioni sono dati nel JSON.
- App:
  - partenza con ricerca per nome o IATA (datalist), ricordata nel browser (localStorage);
  - scheda: "diretto stimato" / "1 scalo stimato" / "N scali stimati", aeroporto principale e quello più vicino;
  - zone senza climatologia in grigio, con "Dati in arrivo";
  - corretto l'arrotondamento delle ore (poteva scrivere "19h 60").
- Collaudo contro tempi tipici reali (itinerario veloce comune, da Trip.com, Rome2rio, FlightRoutes; Bali, Maldive e MXP-Lisbona a memoria):

  | Partenza | Arrivo | km | Scali stimati | Stima | Tipico reale | Scarto |
  |---|---|---|---|---|---|---|
  | GOA | Bali (DPS) | 11.982 | 2 | 23h25 | ~21h | +12% |
  | GOA | Oahu (HNL) | 12.583 | 2 | 24h20 | ~25h | -3% |
  | GOA | Lisbona (LIS) | 1.616 | 1 | 5h40 | ~5h05 | +10% |
  | GOA | Maldive (MLE) | 7.690 | 1 | 13h40 | ~14h | -3% |
  | GOA | Costa Rica (LIR) | 9.529 | 2 | 20h00 | ~20h | 0% |
  | GOA | Mentawai (PDG) | 10.183 | 3 | 24h55 | ~24h | +4% |
  | MXP | Bali (DPS) | 11.978 | 1 | 19h15 | ~17h | +13% |
  | MXP | Oahu (HNL) | 12.449 | 1 | 19h55 | ~21h40 | -8% |
  | MXP | Lisbona (LIS) | 1.652 | 0 | 2h30 | 2h45 | -9% |
  | MXP | Maldive (MLE) | 7.735 | 1 | 13h40 | ~12h30 | +10% |
  | MXP | Costa Rica (LIR) | 9.496 | 1 | 16h00 | ~17h25 | -8% |
  | MXP | Mentawai (PDG) | 10.191 | 2 | 20h55 | ~21h | 0% |

  Unica correzione: da aeroporto non hub la fascia con 1 scalo è passata da 10.000 a 9.000 km (Genova-Costa Rica era -20%).

### Aperti
- Le fasce di distanza non conoscono le rotte vere: Genova-Bilbao esce "diretto stimato" anche se non esiste. Si risolve con i dati della fase 5.
- Genova-Padang esce con 3 scali (2 di fascia + 1 di eccezione): il tempo torna, il numero di scali è probabilmente alto di uno.


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

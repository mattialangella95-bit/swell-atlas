"""Fase 5: prezzi voli indicativi per mese, dalla cache di Aviasales (API dati di Travelpayouts).

Per ogni partenza di data/prices.json e ogni aeroporto principale delle zone (airport_main in
data/zones.json), per ciascuno dei prossimi 12 mesi chiede a /aviasales/v3/prices_for_dates le
offerte di andata e ritorno in cache (one_way=false) e ne tiene il minimo, la mediana e il numero.
Ogni giro AGGIUNGE righe a swell_prices su Supabase (storico), con la stessa data di rilevazione.

Solo libreria standard (gira anche in GitHub Actions senza installare nulla).
Variabili d'ambiente (o .env in locale):
  TRAVELPAYOUTS_TOKEN   token dell'API dati (Travelpayouts -> Profilo -> API token)
  SUPABASE_URL, SUPABASE_SECRET_KEY   per scrivere (non servono con --prova)

Uso:    python3 scripts/fetch_prices.py                         # giro completo
        python3 scripts/fetch_prices.py --prova --solo GOA-DPS  # niente scrittura, stampa i numeri
"""
import argparse, json, os, statistics, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supa import env, request

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


def months_ahead(n, today=None):
    d = (today or date.today()).replace(day=1)
    out = []
    for _ in range(n):
        out.append(d)
        d = date(d.year + d.month // 12, d.month % 12 + 1, 1)
    return out


def offers(token, cfg, origin, dest, month):
    """Prezzi delle offerte di andata e ritorno in cache con partenza nel mese. Lista vuota se non ce ne sono."""
    q = urllib.parse.urlencode({"origin": origin, "destination": dest, "departure_at": month.strftime("%Y-%m"),
                                "one_way": "false", "currency": cfg["currency"], "market": cfg["market"],
                                "sorting": "price", "limit": 1000, "page": 1, "unique": "false"})
    req = urllib.request.Request(f"{API}?{q}", headers={"X-Access-Token": token, "Accept-Encoding": "identity"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
            if not d.get("success", True):
                return []
            return [int(round(x["price"])) for x in d.get("data", []) if x.get("price")]
        except urllib.error.HTTPError as e:
            if e.code == 429:   # oltre 600 al minuto: si aspetta il minuto
                time.sleep(61); continue
            if e.code in (400, 404):
                return []
            time.sleep(10 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(10 * (attempt + 1))
    print(f"  {origin}-{dest} {month:%Y-%m}: nessuna risposta dopo 6 tentativi", flush=True)
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prova", action="store_true", help="non scrive su Supabase, stampa i numeri")
    ap.add_argument("--solo", nargs="+", metavar="ORIG-DEST", help="solo queste tratte, es. GOA-DPS MXP-HNL")
    a = ap.parse_args()

    e = env()
    token = os.environ.get("TRAVELPAYOUTS_TOKEN") or e.get("TRAVELPAYOUTS_TOKEN")
    if not token:
        sys.exit("Manca TRAVELPAYOUTS_TOKEN (variabile d'ambiente o .env).")
    url, secret = e.get("SUPABASE_URL"), e.get("SUPABASE_SECRET_KEY")
    if not a.prova and not (url and secret):
        sys.exit("Mancano SUPABASE_URL e SUPABASE_SECRET_KEY per scrivere (oppure usa --prova).")

    cfg = json.loads((ROOT / "data/prices.json").read_text())
    dests = sorted({z["airport_main"]["code"] for z in json.loads((ROOT / "data/zones.json").read_text())})
    routes = [(o, d) for o in cfg["origins"] for d in dests if o != d]
    if a.solo:
        wanted = {tuple(r.upper().split("-")) for r in a.solo}
        routes = [r for r in routes if r in wanted] + sorted(wanted - set(routes))
    months = months_ahead(cfg["monthsAhead"])
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pause = 1 / cfg["requestsPerSecond"]
    print(f"{len(routes)} tratte × {len(months)} mesi = {len(routes) * len(months)} chiamate, rilevazione {observed}", flush=True)

    rows, calls, t0 = [], 0, time.time()
    for n, (o, d) in enumerate(routes, 1):
        found = []
        for m in months:
            p = offers(token, cfg, o, d, m); calls += 1
            time.sleep(pause)
            if p:
                row = {"origin": o, "destination": d, "month": m.isoformat(), "price_min": min(p),
                       "price_median": int(round(statistics.median(p))), "offers": len(p),
                       "currency": cfg["currency"].upper(), "source": "travelpayouts", "observed_at": observed}
                rows.append(row); found.append(row)
        if a.prova or a.solo:
            print(f"\n{o} -> {d}: {len(found)} mesi su {len(months)} con prezzi in cache")
            for r in found:
                print(f"  {r['month'][:7]}  minimo {r['price_min']:>5} €  mediana {r['price_median']:>5} €  offerte {r['offers']}")
        elif n % 50 == 0:
            print(f"{n}/{len(routes)} tratte, {len(rows)} righe, {time.time() - t0:.0f}s", flush=True)

    print(f"\n{calls} chiamate in {time.time() - t0:.0f}s, {len(rows)} righe con prezzi "
          f"({len(rows) / max(1, calls):.0%} delle combinazioni tratta-mese)", flush=True)
    if a.prova:
        print("prova: niente scritto su Supabase"); return
    for i in range(0, len(rows), 500):
        c, r = request("POST", f"{url}/rest/v1/swell_prices", secret, body=rows[i:i + 500], prefer="return=minimal")
        if c >= 300:
            sys.exit(f"Scrittura su Supabase fallita: {c} {r}")
    print(f"scritte {len(rows)} righe in swell_prices")


if __name__ == "__main__":
    main()

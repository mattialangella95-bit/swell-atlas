"""Fase 3: scarica 20 anni di onde e vento orari da Open-Meteo per ogni zona.

Le zone si leggono SOLO dalla coda congelata data/raw/waves/_queue.json (creata con
--crea-coda da data/zones.json), così zones.json si può modificare mentre il download gira.
Per ogni zona:
  - onde (Marine API, modello era5_ocean): altezza, periodo medio, periodo di picco e
    direzione dell'onda totale, su un punto in mare spostato di 40 km dal centro verso
    l'esposizione. ERA5 su Open-Meteo non separa lo swell: lo swell separato esiste solo
    dal 2022 in poi.
  - vento (Archive API, modello era5): velocità e direzione a 10 m, nella cella di mare
    più vicina al centro della zona (sulla costa, dove conta per offshore/onshore).
Salva data/raw/waves/<id>.parquet (fuori da git).

Limiti gratuiti di Open-Meteo: 600 chiamate/minuto, 5000/ora, 10000/giorno (giorno UTC), e una
richiesta lunga vale come molte chiamate. Il peso stimato è giorni/14 × variabili/10 (dedotto
dalle misure del collaudo: onde ~209, vento ~104, ~313 a zona). Lo script tiene il conto in
data/raw/waves/_progress.json, si ferma prima dei tetti (BUDGET_*) e riparte da solo all'ora o al
giorno successivo; se Open-Meteo risponde comunque "limit exceeded", aspetta e riprova.
Si può fermare e rilanciare: riparte dalle zone mancanti (e dal vento, se le onde c'erano già).

Uso:    .venv/bin/python scripts/fetch_waves.py --crea-coda           # congela la lista zone
        .venv/bin/python scripts/fetch_waves.py                       # scarica le zone mancanti della coda
        .venv/bin/python scripts/fetch_waves.py --zone usa-graters    # solo alcune (ripetibile)
        .venv/bin/python scripts/fetch_waves.py --rifai-vento --zone usa-graters   # riscarica solo il vento
        .venv/bin/python scripts/fetch_waves.py --stato               # riassunto di _progress.json
        touch data/raw/waves/_stop                                    # ferma dopo la zona in corso
"""
import argparse, json, math, os, signal, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
ZONES = ROOT / "data/zones.json"
OUT = ROOT / "data/raw/waves"
QUEUE = OUT / "_queue.json"
PROGRESS = OUT / "_progress.json"
STOP = OUT / "_stop"   # se esiste, il download si ferma prima della zona successiva

START, END = "2005-01-01", "2024-12-31"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
MARINE_VARS = ["wave_height", "wave_period", "wave_peak_period", "wave_direction"]
WIND_VARS = ["wind_speed_10m", "wind_direction_10m"]
OFFSHORE_KM = 40      # distanza del punto onde dal centro zona, verso l'esposizione
STEP_KM = 20          # spostamento se il punto non ha dati
PAUSE_S = 75          # pausa dopo ogni richiesta lunga (limite al minuto)
MAX_MISSING = 0.05    # quota massima di ore senza dati accettata
BUDGET_DAY = 9000     # chiamate stimate al giorno (UTC), margine sotto le 10000 di Open-Meteo
BUDGET_HOUR = 4500    # chiamate stimate all'ora, margine sotto le 5000


def destination(lat, lon, bearing, km):
    d, b = km / 6371.0, math.radians(bearing)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return round(math.degrees(p2), 4), round((math.degrees(l2) + 540) % 360 - 180, 4)


def candidates(zone):
    """Punti onde in ordine di preferenza. Primo: 40 km verso l'esposizione; poi spostamenti di 20 km."""
    lat, lon, e = zone["lat"], zone["lon"], zone.get("exposure")
    if e is None:   # esposizione sconosciuta: centro, poi a 20 e 40 km in 8 direzioni
        return [(lat, lon)] + [destination(lat, lon, b, k) for k in (STEP_KM, 2 * STEP_KM) for b in range(0, 360, 45)]
    p = destination(lat, lon, e, OFFSHORE_KM)
    out = [p, destination(lat, lon, e, OFFSHORE_KM + STEP_KM)]
    out += [destination(*p, (e + s) % 360, STEP_KM) for s in (-90, 90)]
    out += [destination(lat, lon, e, OFFSHORE_KM - STEP_KM), destination(lat, lon, e, OFFSHORE_KM + 2 * STEP_KM)]
    return out


DAYS = (datetime.fromisoformat(END) - datetime.fromisoformat(START)).days + 1


def weight(days, nvars):
    """Peso stimato di una richiesta in chiamate Open-Meteo (minimo 1)."""
    return max(1.0, days / 14 * nvars / 10)


def log(msg):
    print(f"{datetime.now():%d/%m %H:%M:%S} {msg}", flush=True)


class Progress:
    """Stato del download in _progress.json: zone, chiamate stimate di oggi e dell'ora, prossima ripresa."""

    def __init__(self, queue, already_today=0.0):
        old = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
        self.queue = queue
        self.day = old.get("giorno_utc"); self.calls_day = old.get("chiamate_stimate_oggi", 0.0)
        self.hour = old.get("ora_utc"); self.calls_hour = old.get("chiamate_stimate_ora", 0.0)
        self.skipped = old.get("saltate", {})
        self.roll()
        self.calls_day = max(self.calls_day, already_today)
        self.state, self.current, self.resume = "avvio", None, None

    def roll(self):
        now = datetime.now(timezone.utc)
        if self.day != now.strftime("%Y-%m-%d"):
            self.day, self.calls_day = now.strftime("%Y-%m-%d"), 0.0
        if self.hour != now.strftime("%Y-%m-%dT%H"):
            self.hour, self.calls_hour = now.strftime("%Y-%m-%dT%H"), 0.0

    def write(self):
        ids = [z["id"] for z in self.queue]
        done = [i for i in ids if (OUT / f"{i}.parquet").exists()]
        todo = [i for i in ids if i not in done]
        per_zone = weight(DAYS, len(MARINE_VARS)) + weight(DAYS, len(WIND_VARS))
        PROGRESS.write_text(json.dumps({
            "aggiornato": datetime.now().isoformat(timespec="seconds"), "stato": self.state, "pid": os.getpid(),
            "zona_in_corso": self.current, "fatte": len(done), "mancanti": len(todo), "totale": len(ids),
            "giorno_utc": self.day, "chiamate_stimate_oggi": round(self.calls_day), "tetto_giornaliero": BUDGET_DAY,
            "ora_utc": self.hour, "chiamate_stimate_ora": round(self.calls_hour), "tetto_orario": BUDGET_HOUR,
            "prossima_ripresa": self.resume,
            "giorni_stimati_alla_fine": round(len(todo) * per_zone / BUDGET_DAY, 1),
            "saltate": self.skipped, "zone_mancanti": todo, "zone_fatte": done}, ensure_ascii=False, indent=1))

    def pause_until(self, until, state):
        self.state, self.resume = state, until.astimezone().isoformat(timespec="minutes")
        self.write()
        log(f"  {state}: riprendo alle {until.astimezone():%H:%M} del {until.astimezone():%d/%m}")
        time.sleep(max(1, (until - datetime.now(timezone.utc)).total_seconds()))
        self.resume = None; self.state = "scarico"; self.roll()

    def spend(self, w):
        """Prima di ogni richiesta: se supera un tetto, aspetta l'ora o il giorno UTC successivo."""
        self.roll()
        now = datetime.now(timezone.utc)
        if self.calls_day + w > BUDGET_DAY:
            self.pause_until((now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0), "pausa tetto giornaliero")
        elif self.calls_hour + w > BUDGET_HOUR:
            self.pause_until((now + timedelta(hours=1)).replace(minute=1, second=0, microsecond=0), "pausa tetto orario")
        self.calls_day += w; self.calls_hour += w
        self.write()

    def limit_hit(self, reason):
        """Open-Meteo ha risposto "limit exceeded": il conto stimato era basso, si aspetta comunque."""
        now = datetime.now(timezone.utc)
        r = reason.lower()
        if "daily" in r:
            self.calls_day = BUDGET_DAY
            self.pause_until((now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0), f"limite Open-Meteo ({reason})")
        elif "hourly" in r:
            self.calls_hour = BUDGET_HOUR
            self.pause_until((now + timedelta(hours=1)).replace(minute=1, second=0, microsecond=0), f"limite Open-Meteo ({reason})")
        else:
            self.pause_until(now + timedelta(seconds=65), f"limite Open-Meteo ({reason})")


P = None   # Progress attivo


def get(url, params, w):
    """GET JSON con conto delle chiamate, gestione dei limiti e degli errori di rete."""
    q = url + "?" + urllib.parse.urlencode(params)
    backoff = 30
    P.spend(w)
    while True:
        try:
            with urllib.request.urlopen(q, timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                reason = json.load(e).get("reason", "")
            except Exception:
                reason = ""
            if e.code == 429 or "limit" in reason.lower():
                P.limit_hit(reason or "HTTP 429")
                continue
            if e.code == 400:
                raise RuntimeError(f"richiesta rifiutata: {reason}") from e
            log(f"  HTTP {e.code} {reason}: riprovo tra {backoff}s")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            log(f"  errore di rete ({e}): riprovo tra {backoff}s")
        time.sleep(backoff)
        backoff = min(backoff * 2, 900)


def marine(lat, lon, start, end, days):
    return get(MARINE_URL, {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                            "hourly": ",".join(MARINE_VARS), "models": "era5_ocean",
                            "timezone": "GMT", "timeformat": "unixtime"}, weight(days, len(MARINE_VARS)))


def has_waves(lat, lon):
    """Prova economica su 2 giorni: la cella del modello è mare?"""
    h = marine(lat, lon, "2005-01-15", "2005-01-16", 2)["hourly"]
    return any(v is not None for v in h["wave_height"])


def to_array(values):
    return np.array([np.nan if v is None else v for v in values], dtype=np.float32)


def fetch_marine(zone, part):
    for lat, lon in candidates(zone):
        if not has_waves(lat, lon):
            log(f"  ({lat}, {lon}) senza dati onda, sposto di {STEP_KM} km")
            continue
        d = marine(lat, lon, START, END, DAYS)
        time.sleep(PAUSE_S)
        h = d["hourly"]
        missing = float(np.isnan(to_array(h["wave_height"])).mean())
        if missing > MAX_MISSING:
            log(f"  ({lat}, {lon}) mancano il {missing:.0%} delle ore, sposto di {STEP_KM} km")
            continue
        table = pa.table({"time": pa.array(h["time"], pa.int64()), **{v: to_array(h[v]) for v in MARINE_VARS}})
        meta = {"wave_point": json.dumps([lat, lon]), "wave_grid": json.dumps([d["latitude"], d["longitude"]])}
        pq.write_table(table.replace_schema_metadata(meta), part)
        return
    raise RuntimeError("nessun punto con dati onda tra i candidati")


def fetch_wind(zone):
    d = get(ARCHIVE_URL, {"latitude": zone["lat"], "longitude": zone["lon"], "start_date": START, "end_date": END,
                          "hourly": ",".join(WIND_VARS), "models": "era5", "wind_speed_unit": "kmh",
                          "cell_selection": "sea",   # la cella di terra sottostima il vento costiero
                          "timezone": "GMT", "timeformat": "unixtime"}, weight(DAYS, len(WIND_VARS)))
    time.sleep(PAUSE_S)
    return d


def make_queue():
    """Congela la lista zone (ordinata per numero di spot) con centro, esposizione e punto onde."""
    zones = sorted(json.loads(ZONES.read_text()), key=lambda z: (-z.get("spots", 0), z["id"]))
    queue = [{"id": z["id"], "name": z["name"], "spots": z.get("spots"), "lat": z["lat"], "lon": z["lon"],
              "exposure": z.get("exposure"), "wave_point": list(candidates(z)[0])} for z in zones]
    OUT.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=1))
    print(f"coda congelata: {len(queue)} zone in {QUEUE.relative_to(ROOT)}")


def show_state():
    if not PROGRESS.exists():
        sys.exit("nessun _progress.json: il download non è mai partito")
    p = json.loads(PROGRESS.read_text())
    alive = False
    try:
        os.kill(p["pid"], 0); alive = True
    except (OSError, KeyError):
        pass
    print(f"fonte: {p.get('fonte', 'open-meteo')}")
    print(f"stato: {p['stato']} (processo {p.get('pid')} {'attivo' if alive else 'non attivo'}), aggiornato {p['aggiornato']}")
    print(f"zone: {p['fatte']}/{p['totale']} fatte, {p['mancanti']} mancanti, in corso: {p.get('zona_in_corso')}")
    if "chiamate_stimate_oggi" in p:   # solo per Open-Meteo
        print(f"chiamate stimate oggi ({p['giorno_utc']} UTC): {p['chiamate_stimate_oggi']} / {p['tetto_giornaliero']}")
        print(f"giorni stimati alla fine: {p['giorni_stimati_alla_fine']}")
    if p.get("prossima_ripresa"):
        print(f"prossima ripresa: {p['prossima_ripresa']}")
    if p.get("saltate"):
        print("saltate:", ", ".join(f"{k} ({v})" for k, v in p["saltate"].items()))


def main():
    global P
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crea-coda", action="store_true", help="congela data/zones.json in _queue.json ed esce")
    ap.add_argument("--stato", action="store_true", help="mostra il riassunto di _progress.json ed esce")
    ap.add_argument("--zone", action="append", help="id zona della coda (ripetibile); senza, tutte")
    ap.add_argument("--rifai-vento", action="store_true", help="riscarica il vento delle zone già scaricate, tenendo le onde")
    ap.add_argument("--gia-usate-oggi", type=float, default=0, help="chiamate stimate già consumate oggi fuori dallo script")
    a = ap.parse_args()
    if a.crea_coda:
        return make_queue()
    if a.stato:
        return show_state()
    if not QUEUE.exists():
        sys.exit(f"manca {QUEUE.relative_to(ROOT)}: lancia prima --crea-coda")

    queue = json.loads(QUEUE.read_text())
    zones = queue
    if a.zone:
        by_id = {z["id"]: z for z in queue}
        unknown = [i for i in a.zone if i not in by_id]
        if unknown:
            sys.exit(f"zone non presenti nella coda: {', '.join(unknown)}")
        zones = [by_id[i] for i in a.zone]
    if a.rifai_vento:   # riporta le zone complete allo stato "onde scaricate, vento mancante"
        for z in zones:
            final = OUT / f"{z['id']}.parquet"
            if final.exists():
                t = pq.read_table(final)
                pq.write_table(t.drop_columns(WIND_VARS), OUT / f"{z['id']}.marine.parquet")
                final.unlink()

    P = Progress(queue, a.gia_usate_oggi)

    def stop(signum, frame):
        P.state, P.current = "fermato", None
        P.write(); log("fermato"); sys.exit(0)
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)

    todo = [z for z in zones if not (OUT / f"{z['id']}.parquet").exists()]
    log(f"zone da scaricare: {len(todo)} su {len(zones)}")
    P.state = "scarico"; P.write()

    for n, z in enumerate(todo, 1):
        if STOP.exists():
            STOP.unlink()
            P.state, P.current = "fermato dopo la zona in corso", None
            P.write(); log("fermato su richiesta (_stop)"); return
        final, part = OUT / f"{z['id']}.parquet", OUT / f"{z['id']}.marine.parquet"
        log(f"[{n}/{len(todo)}] {z['id']} ({z['name']})")
        P.current = z["id"]; P.write()
        try:
            if not part.exists():
                fetch_marine(z, part)
            waves = pq.read_table(part)
            d = fetch_wind(z)
        except RuntimeError as e:
            log(f"  saltata: {e}")
            P.skipped[z["id"]] = str(e); P.write()
            continue
        h = d["hourly"]
        if h["time"] != waves.column("time").to_pylist():
            log("  saltata: ore del vento diverse da quelle delle onde")
            P.skipped[z["id"]] = "ore del vento diverse da quelle delle onde"; P.write()
            continue
        table = waves
        for v in WIND_VARS:
            table = table.append_column(v, pa.array(to_array(h[v])))
        meta = {k: v for k, v in (waves.schema.metadata or {}).items() if k != b"wind_grid"}
        meta[b"wind_grid"] = json.dumps([d["latitude"], d["longitude"]]).encode()
        pq.write_table(table.replace_schema_metadata(meta), final, compression="zstd")
        part.unlink()
        P.skipped.pop(z["id"], None)
        log(f"  ok: {table.num_rows} ore, onde in {json.loads(meta[b'wave_grid'])}, vento in {json.loads(meta[b'wind_grid'])}")
    P.current = None
    P.state = "finito" if all((OUT / f"{z['id']}.parquet").exists() for z in queue) else "finito con zone saltate"
    P.write()
    done = sum((OUT / f"{z['id']}.parquet").exists() for z in queue)
    log(f"fatto: {done}/{len(queue)} zone con dati")


if __name__ == "__main__":
    main()

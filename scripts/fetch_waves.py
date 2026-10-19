"""Fase 3: scarica 20 anni di onde e vento orari da Open-Meteo per ogni zona.

Per ogni zona di data/zones.json:
  - onde (Marine API, modello era5_ocean): altezza, periodo medio, periodo di picco e
    direzione dell'onda totale, su un punto in mare spostato di 40 km dal centro verso
    l'esposizione. ERA5 su Open-Meteo non separa lo swell: lo swell separato esiste solo
    dal 2022 in poi.
  - vento (Archive API, modello era5): velocità e direzione a 10 m, nella cella di mare
    più vicina al centro della zona (sulla costa, dove conta per offshore/onshore).
Salva data/raw/waves/<id>.parquet (fuori da git).

Limiti gratuiti di Open-Meteo: 600 chiamate/minuto, 5000/ora, 10000/giorno, e una richiesta
di 20 anni vale centinaia di chiamate. Lo script fa pause tra le richieste e, se riceve
"limit exceeded", aspetta il minuto/ora/giorno successivo e riprova. Si può interrompere e
rilanciare: riparte dalle zone mancanti (e dal vento, se le onde erano già scaricate).

Uso:    .venv/bin/python scripts/fetch_waves.py                      # tutte le zone mancanti
        .venv/bin/python scripts/fetch_waves.py --zone usa-graters   # solo alcune (ripetibile)
        .venv/bin/python scripts/fetch_waves.py --rifai-vento --zone usa-graters   # riscarica solo il vento
"""
import argparse, json, math, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
ZONES = ROOT / "data/zones.json"
OUT = ROOT / "data/raw/waves"

START, END = "2005-01-01", "2024-12-31"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
MARINE_VARS = ["wave_height", "wave_period", "wave_peak_period", "wave_direction"]
WIND_VARS = ["wind_speed_10m", "wind_direction_10m"]
OFFSHORE_KM = 40      # distanza del punto onde dal centro zona, verso l'esposizione
STEP_KM = 20          # spostamento se il punto non ha dati
PAUSE_S = 75          # pausa dopo ogni richiesta lunga (limite al minuto)
MAX_MISSING = 0.05    # quota massima di ore senza dati accettata


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


def wait_for_limit(reason):
    now = datetime.now(timezone.utc)
    r = reason.lower()
    if "daily" in r:
        until = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
    elif "hourly" in r:
        until = (now + timedelta(hours=1)).replace(minute=1, second=0, microsecond=0)
    else:
        until = now + timedelta(seconds=65)
    print(f"  limite Open-Meteo ({reason}): riprendo alle {until.astimezone():%H:%M} del {until.astimezone():%d/%m}", flush=True)
    time.sleep(max(1, (until - now).total_seconds()))


def get(url, params):
    """GET JSON con gestione dei limiti e degli errori di rete. Ritorna il JSON della risposta."""
    q = url + "?" + urllib.parse.urlencode(params)
    backoff = 30
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
                wait_for_limit(reason or "HTTP 429")
                continue
            if e.code == 400:
                raise RuntimeError(f"richiesta rifiutata: {reason}") from e
            print(f"  HTTP {e.code} {reason}: riprovo tra {backoff}s", flush=True)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"  errore di rete ({e}): riprovo tra {backoff}s", flush=True)
        time.sleep(backoff)
        backoff = min(backoff * 2, 900)


def marine(lat, lon, start, end):
    return get(MARINE_URL, {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                            "hourly": ",".join(MARINE_VARS), "models": "era5_ocean",
                            "timezone": "GMT", "timeformat": "unixtime"})


def has_waves(lat, lon):
    """Prova economica su 2 giorni: la cella del modello è mare?"""
    h = marine(lat, lon, "2005-01-15", "2005-01-16")["hourly"]
    return any(v is not None for v in h["wave_height"])


def to_array(values):
    return np.array([np.nan if v is None else v for v in values], dtype=np.float32)


def fetch_marine(zone, part):
    for lat, lon in candidates(zone):
        if not has_waves(lat, lon):
            print(f"  ({lat}, {lon}) senza dati onda, sposto di {STEP_KM} km", flush=True)
            continue
        d = marine(lat, lon, START, END)
        time.sleep(PAUSE_S)
        h = d["hourly"]
        missing = float(np.isnan(to_array(h["wave_height"])).mean())
        if missing > MAX_MISSING:
            print(f"  ({lat}, {lon}) mancano il {missing:.0%} delle ore, sposto di {STEP_KM} km", flush=True)
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
                          "timezone": "GMT", "timeformat": "unixtime"})
    time.sleep(PAUSE_S)
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zone", action="append", help="id zona (ripetibile); senza, tutte")
    ap.add_argument("--rifai-vento", action="store_true", help="riscarica il vento delle zone già scaricate, tenendo le onde")
    a = ap.parse_args()

    zones = json.loads(ZONES.read_text())
    if a.zone:
        by_id = {z["id"]: z for z in zones}
        unknown = [i for i in a.zone if i not in by_id]
        if unknown:
            sys.exit(f"zone sconosciute: {', '.join(unknown)}")
        zones = [by_id[i] for i in a.zone]
    OUT.mkdir(parents=True, exist_ok=True)
    if a.rifai_vento:   # riporta le zone complete allo stato "onde scaricate, vento mancante"
        for z in zones:
            final = OUT / f"{z['id']}.parquet"
            if final.exists():
                t = pq.read_table(final)
                pq.write_table(t.drop_columns(WIND_VARS), OUT / f"{z['id']}.marine.parquet")
                final.unlink()
    todo = [z for z in zones if not (OUT / f"{z['id']}.parquet").exists()]
    print(f"zone da scaricare: {len(todo)} su {len(zones)}", flush=True)

    for n, z in enumerate(todo, 1):
        final, part = OUT / f"{z['id']}.parquet", OUT / f"{z['id']}.marine.parquet"
        print(f"[{n}/{len(todo)}] {z['id']} ({z['name']})", flush=True)
        try:
            if not part.exists():
                fetch_marine(z, part)
            waves = pq.read_table(part)
            d = fetch_wind(z)
        except RuntimeError as e:
            print(f"  saltata: {e}", flush=True)
            continue
        h = d["hourly"]
        if h["time"] != waves.column("time").to_pylist():
            print("  saltata: ore del vento diverse da quelle delle onde", flush=True)
            continue
        table = waves
        for v in WIND_VARS:
            table = table.append_column(v, pa.array(to_array(h[v])))
        meta = {k: v for k, v in (waves.schema.metadata or {}).items() if k != b"wind_grid"}
        meta[b"wind_grid"] = json.dumps([d["latitude"], d["longitude"]]).encode()
        pq.write_table(table.replace_schema_metadata(meta), final, compression="zstd")
        part.unlink()
        print(f"  ok: {table.num_rows} ore, onde in {json.loads(meta[b'wave_grid'])}, vento in {json.loads(meta[b'wind_grid'])}", flush=True)
    done = sum((OUT / f"{z['id']}.parquet").exists() for z in zones)
    print(f"fatto: {done}/{len(zones)} zone con dati", flush=True)


if __name__ == "__main__":
    main()

"""Fase 3, strada Copernicus: ERA5 dal Climate Data Store (CDS).

Serve un account CDS, la licenza ERA5 accettata sul sito e la chiave API in ~/.cdsapirc
(oppure nelle variabili d'ambiente CDSAPI_URL e CDSAPI_KEY).

Comandi:
  costi            costo di ogni scenario rispetto ai limiti CDS (endpoint pubblico, niente account)
  prova-puntuale   1 mese (gennaio 2020) dal dataset puntuale per le 5 zone di collaudo:
                   tempi, dimensioni e confronto con i dati Open-Meteo già scaricati
  prova-griglia    1 mese (gennaio 2020) ogni 6 ore dalla griglia globale, tutte le variabili:
                   tempo, dimensione, estrazione dei 5 punti e confronto con Open-Meteo
  scarica          20 anni orari dal dataset puntuale per le zone indicate (o tutte),
                   scritti in data/raw/waves/<id>.parquet nello stesso formato di fetch_waves.py

Formato intermedio comune (letto da build_climate.py): parquet con colonne
time (s UTC), wave_height, wave_period, [wave_peak_period], wave_direction,
wind_speed_10m (km/h), wind_direction_10m (gradi, provenienza) e metadati wave_grid/wind_grid/source.
Il dataset puntuale non ha periodo di picco: con questa fonte in quality-rule.json
period.field va messo a "wave_period".

Uso:    .venv/bin/python scripts/era5_cds.py costi
        .venv/bin/python scripts/era5_cds.py prova-puntuale
        .venv/bin/python scripts/era5_cds.py prova-griglia
        .venv/bin/python scripts/era5_cds.py scarica --zone usa-graters
"""
import argparse, csv, io, json, math, os, signal, sys, time, urllib.request, zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
ZONES = ROOT / "data/zones.json"
RAW = ROOT / "data/raw/waves"
CDS_RAW = ROOT / "data/raw/cds"
STOP = RAW / "_stop"
API = "https://cds.climate.copernicus.eu/api/retrieve/v1/processes"
TS = "reanalysis-era5-single-levels-timeseries"
GRID = "reanalysis-era5-single-levels"
TEST_ZONES = ["usa-graters", "south-africa-doughnuts-backreef", "france-le-penon", "indonesia-medewi", "indonesia-4-bobs"]
TEST_MONTH = ("2020", "01")

TS_WAVE = ["significant_height_of_combined_wind_waves_and_swell", "mean_wave_period", "mean_wave_direction"]
TS_WIND = ["10m_u_component_of_wind", "10m_v_component_of_wind"]
GRID_VARS = ["significant_height_of_total_swell", "mean_period_of_total_swell", "mean_direction_of_total_swell",
             "significant_height_of_combined_wind_waves_and_swell", "peak_wave_period",
             "10m_u_component_of_wind", "10m_v_component_of_wind"]
# nomi brevi ERA5 -> colonne del formato intermedio
SHORT = {"swh": "wave_height", "mwp": "wave_period", "pp1d": "wave_peak_period", "mwd": "wave_direction",
         "shts": "swell_height", "mpts": "swell_period", "mdts": "swell_direction", "u10": "u10", "v10": "v10"}


# ---------- formato intermedio

def wind_from_uv(u, v):
    """Componenti u/v (m/s) -> velocità km/h e direzione di provenienza in gradi."""
    speed = np.hypot(u, v) * 3.6
    direction = (np.degrees(np.arctan2(-u, -v)) + 360) % 360
    return speed.astype(np.float32), direction.astype(np.float32)


def to_intermediate(cols, meta):
    """cols: dict con 'time' (s UTC) e colonne con nomi brevi ERA5. Ritorna la tabella del formato comune."""
    out = {"time": pa.array(np.asarray(cols["time"], dtype=np.int64))}
    for short, name in SHORT.items():
        if short in cols and name not in ("u10", "v10"):
            out[name] = np.asarray(cols[short], dtype=np.float32)
    if "u10" in cols:
        out["wind_speed_10m"], out["wind_direction_10m"] = wind_from_uv(np.asarray(cols["u10"], float), np.asarray(cols["v10"], float))
    table = pa.table(out)
    return table.replace_schema_metadata({k: json.dumps(v) for k, v in meta.items()})


# ---------- CDS

def client():
    try:
        import cdsapi
        return cdsapi.Client(quiet=True)
    except Exception as e:
        sys.exit(f"CDS non configurato ({e}).\nServono account CDS, licenza ERA5 accettata e chiave in ~/.cdsapirc "
                 "o nelle variabili CDSAPI_URL/CDSAPI_KEY.")


def retrieve(c, dataset, request, target):
    t0 = time.time()
    c.retrieve(dataset, request, str(target))
    return time.time() - t0


def read_ts_csv(path):
    """CSV (o zip di CSV) del dataset puntuale -> dict {time, nomi brevi}."""
    texts = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            texts = [z.read(n).decode() for n in z.namelist() if n.endswith(".csv")]
    else:
        texts = [Path(path).read_text()]
    merged = {}
    for text in texts:
        rows = list(csv.DictReader(io.StringIO(text)))
        tkey = next(k for k in rows[0] if k in ("valid_time", "time", "date"))
        times = np.array([np.datetime64(r[tkey].replace(" ", "T").rstrip("Z"), "s").astype(np.int64) for r in rows])
        merged.setdefault("time", times)
        for k in rows[0]:
            if k in SHORT:
                merged[k] = np.array([float(r[k]) if r[k] not in ("", "nan") else np.nan for r in rows])
    return merged


def read_grid_nc(path):
    """NetCDF (o zip di NetCDF) della griglia -> dict {nome breve: (lat, lon, time, array)}."""
    import h5py
    files = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".nc"):
                    files.append(io.BytesIO(z.read(n)))
    else:
        files = [path]
    out = {}
    for f in files:
        with h5py.File(f, "r") as h:
            lat, lon = h["latitude"][:], h["longitude"][:]
            tname = "valid_time" if "valid_time" in h else "time"
            t = h[tname][:].astype(np.int64)
            for k in h:
                if k in SHORT:
                    ds = h[k]
                    a = ds[:].astype(np.float32)
                    fill = ds.attrs.get("_FillValue")
                    if fill is not None:
                        a[a == fill] = np.nan
                    a = a * ds.attrs.get("scale_factor", 1) + ds.attrs.get("add_offset", 0)
                    out[k] = (lat, lon, t, a)
    return out


def nearest(lat, lon, glat, glon):
    i = int(np.abs(glat - lat).argmin())
    j = int(np.abs(((glon - lon + 180) % 360) - 180).argmin())
    return i, j


def compare(zid, cds_time, cds_h, cds_t, cds_d):
    """Scarti medi CDS - Open-Meteo sulle stesse ore."""
    om = pq.read_table(RAW / f"{zid}.parquet")
    ot = om.column("time").to_numpy()
    idx = {t: i for i, t in enumerate(ot)}
    sel = [(k, idx[t]) for k, t in enumerate(cds_time) if t in idx]
    a, b = np.array([k for k, _ in sel]), np.array([i for _, i in sel])
    oh, otm, od = (om.column(c).to_numpy()[b] for c in ("wave_height", "wave_period", "wave_direction"))
    dh, dt = cds_h[a] - oh, cds_t[a] - otm
    dd = np.abs((cds_d[a] - od + 180) % 360 - 180)
    return len(sel), np.nanmean(dh), np.nanmean(np.abs(dh)), np.nanmean(dt), np.nanmean(np.abs(dt)), np.nanmean(dd)


def print_compare(rows):
    print(f"\n{'zona':34} {'ore':>5} {'Δh media':>9} {'|Δh|':>6} {'ΔT media':>9} {'|ΔT|':>6} {'|Δdir|':>7}")
    for zid, r in rows:
        n, mh, ah, mt, at, ad = r
        print(f"{zid:34} {n:5} {mh:+8.2f}m {ah:5.2f}m {mt:+8.2f}s {at:5.2f}s {ad:6.1f}°")


# ---------- comandi

def cmd_costi(_):
    def cost(dataset, inputs):
        req = urllib.request.Request(f"{API}/{dataset}/costing", data=json.dumps({"inputs": inputs}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        return d["cost"], d["limit"]

    days = [f"{d:02d}" for d in range(1, 32)]
    scen = {"ogni 6 ore": ["00:00", "06:00", "12:00", "18:00"], "3 orari": ["06:00", "12:00", "18:00"],
            "orario": [f"{h:02d}:00" for h in range(24)]}
    print("griglia globale, 7 variabili, una richiesta:")
    for name, times in scen.items():
        for label, months in (("1 mese", ["01"]), ("1 anno", [f"{m:02d}" for m in range(1, 13)])):
            c, lim = cost(GRID, {"product_type": ["reanalysis"], "variable": GRID_VARS, "year": ["2020"], "month": months,
                                 "day": days, "time": times, "data_format": "netcdf", "download_format": "unarchived"})
            print(f"  {name:11} {label:7} costo {c:9.0f} / limite {lim:.0f}  {'ok' if c <= lim else 'TROPPO'}")
    print("dataset puntuale, 20 anni orari, un punto:")
    for label, var in (("onde (3 var.)", TS_WAVE), ("vento (2 var.)", TS_WIND), ("tutte (5 var.)", TS_WAVE + TS_WIND)):
        c, lim = cost(TS, {"variable": var, "location": {"longitude": -158.0, "latitude": 22.0},
                           "date": ["2005-01-01/2024-12-31"], "data_format": "csv"})
        print(f"  {label:15} costo {c:5.0f} / limite {lim:.0f}")


def zone_points(zid):
    meta = pq.read_schema(RAW / f"{zid}.parquet").metadata
    return json.loads(meta[b"wave_grid"]), json.loads(meta[b"wind_grid"])


def cmd_prova_puntuale(_):
    c = client()
    CDS_RAW.mkdir(parents=True, exist_ok=True)
    y, m = TEST_MONTH
    date = [f"{y}-{m}-01/{y}-{m}-31"]
    rows, total_t, total_b = [], 0.0, 0
    for zid in TEST_ZONES:
        (wlat, wlon), (vlat, vlon) = zone_points(zid)
        fw, fv = CDS_RAW / f"ts_{zid}_onde.csv", CDS_RAW / f"ts_{zid}_vento.csv"
        tw = retrieve(c, TS, {"variable": TS_WAVE, "location": {"longitude": wlon, "latitude": wlat}, "date": date, "data_format": "csv"}, fw)
        tv = retrieve(c, TS, {"variable": TS_WIND, "location": {"longitude": vlon, "latitude": vlat}, "date": date, "data_format": "csv"}, fv)
        total_t += tw + tv; total_b += fw.stat().st_size + fv.stat().st_size
        print(f"{zid}: onde {tw:.0f}s, vento {tv:.0f}s, {(fw.stat().st_size + fv.stat().st_size) / 1024:.0f} KB", flush=True)
        d = read_ts_csv(fw)
        rows.append((zid, compare(zid, d["time"], d["swh"], d["mwp"], d["mwd"])))
    print_compare(rows)
    n = len(TEST_ZONES) * 2
    print(f"\nmedia per richiesta (1 mese): {total_t / n:.0f} s, {total_b / n / 1024:.0f} KB")


def cmd_prova_griglia(_):
    c = client()
    CDS_RAW.mkdir(parents=True, exist_ok=True)
    y, m = TEST_MONTH
    target = CDS_RAW / f"griglia_{y}{m}_6h.nc"
    req = {"product_type": ["reanalysis"], "variable": GRID_VARS, "year": [y], "month": [m],
           "day": [f"{d:02d}" for d in range(1, 32)], "time": ["00:00", "06:00", "12:00", "18:00"],
           "data_format": "netcdf", "download_format": "unarchived"}
    print("richiesta inviata (attesa in coda + elaborazione)...", flush=True)
    t = retrieve(c, GRID, req, target)
    size = target.stat().st_size
    print(f"scaricato in {t / 60:.1f} min, {size / 1e6:.0f} MB", flush=True)
    t0 = time.time()
    g = read_grid_nc(target)
    rows = []
    for zid in TEST_ZONES:
        (wlat, wlon), _ = zone_points(zid)
        lat, lon, tt, swh = g["swh"]
        i, j = nearest(wlat, wlon, lat, lon)
        rows.append((zid, compare(zid, tt, swh[:, i, j], g["mwp"][3][:, i, j] if "mwp" in g else g["mpts"][3][:, i, j], g["mwd"][3][:, i, j] if "mwd" in g else g["mdts"][3][:, i, j])))
    t_ext = time.time() - t0
    print_compare(rows)
    print(f"\nestrazione dei punti: {t_ext:.1f} s")
    steps = {"20 anni ogni 6 ore": 240, "10 anni ogni 6 ore": 120, "10 anni 3 orari": 120 * 3 / 4}
    print("\nstime riscalate su questa misura (richieste da 1 mese):")
    for k, months in steps.items():
        print(f"  {k:20} richieste {int(math.ceil(months)):4}  disco totale {size * months / 1e9:6.0f} GB  "
              f"tempo download {t * months / 3600:6.1f} h  estrazione {t_ext * months / 60:5.1f} min")


def sea_cell(lat, lon, land, step=0.25):
    """Cella ERA5 (griglia 0,25°) di mare più vicina al punto: fa le veci di cell_selection=sea di Open-Meteo."""
    import shapely
    base_lat, base_lon = round(lat / step) * step, round(lon / step) * step
    cells = [(base_lat + a * step, base_lon + b * step) for a in range(-3, 4) for b in range(-3, 4)]
    cells.sort(key=lambda c: (c[0] - lat) ** 2 + ((c[1] - lon) * math.cos(math.radians(lat))) ** 2)
    for c in cells:
        if not shapely.contains_xy(land, c[1], c[0]):
            return round(c[0], 2), round((c[1] + 540) % 360 - 180, 2)
    return base_lat, base_lon


def cmd_scarica(a):
    """Dataset puntuale, 20 anni orari, zone della coda congelata data/raw/waves/_queue.json."""
    c = client()
    queue = json.loads((RAW / "_queue.json").read_text())
    zones = queue if not a.zone else [z for z in queue if z["id"] in set(a.zone)]
    if a.dalla_fine:
        zones = zones[::-1]
    CDS_RAW.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "scripts"))
    from fetch_waves import candidates
    from build_zones import LAND, load_land
    land = load_land(LAND)
    date = ["2005-01-01/2024-12-31"]
    done, skipped = 0, {}

    def progress(state, current=None):
        """Stesso _progress.json di fetch_waves.py, così --stato funziona con entrambe le fonti."""
        ids = [q["id"] for q in queue]
        ok = [i for i in ids if (RAW / f"{i}.parquet").exists()]
        (RAW / "_progress.json").write_text(json.dumps({
            "aggiornato": datetime.now().isoformat(timespec="seconds"), "stato": state, "fonte": "copernicus",
            "pid": os.getpid(), "zona_in_corso": current, "fatte": len(ok), "mancanti": len(ids) - len(ok), "totale": len(ids),
            "saltate": skipped, "zone_mancanti": [i for i in ids if i not in ok], "zone_fatte": ok}, ensure_ascii=False, indent=1))

    def stop(signum, frame):   # kill o Ctrl-C: si salva lo stato; la zona a metà si rifà alla ripresa
        progress("fermato"); print("fermato", flush=True); sys.exit(0)
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)

    for z in zones:
        if a.max and done >= a.max:
            break
        final = RAW / f"{z['id']}.parquet"
        if final.exists() or (RAW / f"{z['id']}.marine.parquet").exists():
            continue   # già fatta, o in corso con Open-Meteo
        if STOP.exists():   # touch data/raw/waves/_stop: si ferma prima della zona successiva
            STOP.unlink(); progress("fermato dopo la zona in corso")
            print(f"fermato su richiesta (_stop): la prossima zona sarebbe {z['id']}", flush=True); return
        t0 = time.time()
        progress("scarico (Copernicus)", z["id"])
        vlat, vlon = sea_cell(z["lat"], z["lon"], land)
        fv = CDS_RAW / f"ts_{z['id']}_vento.csv"
        retrieve(c, TS, {"variable": TS_WIND, "location": {"longitude": vlon, "latitude": vlat}, "date": date, "data_format": "csv"}, fv)
        v = read_ts_csv(fv)
        w = None
        for wlat, wlon in [tuple(z["wave_point"])] + [p for p in candidates(z) if list(p) != z["wave_point"]]:
            fw = CDS_RAW / f"ts_{z['id']}_onde.csv"
            retrieve(c, TS, {"variable": TS_WAVE, "location": {"longitude": wlon, "latitude": wlat}, "date": date, "data_format": "csv"}, fw)
            w = read_ts_csv(fw)
            if np.isnan(w["swh"]).mean() <= 0.05:
                break
            print(f"{z['id']}: punto onde ({wlat}, {wlon}) senza dati, provo il successivo", flush=True)
            w = None
        if w is None or not np.array_equal(w["time"], v["time"]):
            skipped[z["id"]] = "dati incompleti"
            print(f"{z['id']}: dati incompleti, saltata", flush=True); continue
        cols = {"time": w["time"], "swh": w["swh"], "mwp": w["mwp"], "mwd": w["mwd"], "u10": v["u10"], "v10": v["v10"]}
        pq.write_table(to_intermediate(cols, {"source": "cds-timeseries", "wave_point": [wlat, wlon], "wave_grid": [wlat, wlon],
                                              "wind_grid": [vlat, vlon]}), final, compression="zstd")
        fw.unlink(); fv.unlink(); done += 1
        print(f"{datetime.now():%d/%m %H:%M:%S} {z['id']}: ok in {time.time() - t0:.0f}s ({len(w['time'])} ore)", flush=True)
    progress("finito (Copernicus)" if not skipped else "finito con zone saltate (Copernicus)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("costi"); sub.add_parser("prova-puntuale"); sub.add_parser("prova-griglia")
    s = sub.add_parser("scarica"); s.add_argument("--zone", action="append")
    s.add_argument("--dalla-fine", action="store_true", help="parte dal fondo della coda (per non incrociare Open-Meteo)")
    s.add_argument("--max", type=int, help="al massimo N zone")
    a = ap.parse_args()
    {"costi": cmd_costi, "prova-puntuale": cmd_prova_puntuale, "prova-griglia": cmd_prova_griglia, "scarica": cmd_scarica}[a.cmd](a)


if __name__ == "__main__":
    main()

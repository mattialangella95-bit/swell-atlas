"""Fase 3: dai dati orari grezzi alla climatologia settimanale letta dall'app.

Input:  data/raw/waves/<id>.parquet   (scripts/fetch_waves.py)
        data/zones.json                (esposizione della costa)
        data/quality-rule.json         (tutte le soglie della regola qualità)
Output: data/climate.json (le zone senza dati grezzi ci sono con weeks = null)

Per ogni zona e settimana dell'anno (0-51, la 52a raccoglie anche il 365/366° giorno),
usando solo le ore diurne:
  - ogni ora riceve una classe 0-9 dalla regola, ogni giorno la classe migliore tenuta
    per almeno day.minHours ore;
  - per settimana: classe prevalente dei giorni, % di giorni Good o meglio,
    25°/50°/75° percentile di altezza onda e periodo (colonna scelta in quality-rule.json).

Uso:    .venv/bin/python scripts/build_climate.py
        .venv/bin/python scripts/build_climate.py --verifica usa-graters france-le-penon   # tabella mese per mese
"""
import argparse, json, sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/waves"
ZONES = ROOT / "data/zones.json"
RULE = ROOT / "data/quality-rule.json"
SCALE = ROOT / "data/scale.json"
OUT = ROOT / "data/climate.json"
FIELDS = ["q", "h25", "h50", "h75", "t25", "t50", "t75", "good"]
MESI = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]


def angdiff(a, b):
    return np.abs((a - b + 180) % 360 - 180)


def sun_elevation(t, lat, lon):
    """Elevazione del sole in gradi (formula NOAA semplificata), t in secondi UTC."""
    d = t.astype("datetime64[s]").astype("datetime64[D]")
    doy = (d - d.astype("datetime64[Y]")).astype(int)        # 0 = 1 gennaio
    g = 2 * np.pi / 365 * (doy + ((t % 86400) / 3600.0 - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    minutes = (t % 86400) / 60.0 + eqt + 4 * lon
    ha = np.radians(minutes / 4 - 180)
    phi = np.radians(lat)
    return np.degrees(np.arcsin(np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(ha)))


def hourly_class(h, tp, wdir, wspd, wndir, expo, R):
    """Classe 0-9 per ogni ora; -1 se mancano i dati."""
    H, P, D, W, P_ = R["height"], R["period"], R["direction"], R["wind"], R["points"]
    if expo is None:   # esposizione sconosciuta: onda presa tutta, vento solo se debole
        dir_f = np.ones_like(h)
    else:
        diff = angdiff(wdir, expo)
        dir_f = np.clip((D["maxDeg"] - diff) / (D["maxDeg"] - D["fullDeg"]), 0, 1)
    he = h * dir_f
    hs = np.clip((he - H["min"]) / (H["ideal"] - H["min"]), 0, 1)
    hs = hs * (1 - np.clip((he - H["max"]) / (H["tooBig"] - H["max"]), 0, 1))   # mareggiate: punteggio in calo
    ps = np.clip((tp - P["min"]) / (P["good"] - P["min"]), 0, 1)

    adj = np.zeros_like(h)
    light = wspd < W["lightKmh"]
    adj[light] = W["lightBonus"]
    if expo is not None:
        d_off = angdiff(wndir, (expo + 180) % 360)
        off = ~light & (d_off <= W["offshoreDeg"])
        cross_off = ~light & ~off & (d_off <= W["crossOffshoreDeg"])
        on = ~light & (angdiff(wndir, expo) <= W["onshoreDeg"])
        adj[off] = W["offshoreBonus"]
        adj[cross_off] = W["crossOffshoreBonus"]
        adj[on] = -W["onshorePenalty"]
        adj[on & (wspd >= W["onshoreStrongKmh"])] = -W["onshoreStrongPenalty"]

    cls = np.clip(np.round(P_["height"] * hs + P_["period"] * ps + adj), 1, 9)
    cls = np.where(he < H["min"], 0, cls)
    bad = np.isnan(h) | np.isnan(tp) | np.isnan(wdir) | np.isnan(wspd) | np.isnan(wndir)
    return np.where(bad, -1, cls).astype(int)


def daily(zone, table, R):
    """Per ogni giorno locale con ore diurne valide: classe, giorno dell'anno, mese, e le ore diurne usate."""
    t = table.column("time").to_numpy()
    col = lambda c: table.column(c).to_numpy().astype(float)
    h, tp, wdir = col("wave_height"), col(R["period"]["field"]), col("wave_direction")
    wspd, wndir = col("wind_speed_10m"), col("wind_direction_10m")
    cls = hourly_class(h, tp, wdir, wspd, wndir, zone.get("exposure"), R)
    day_mask = (sun_elevation(t, zone["lat"], zone["lon"]) > R["daylight"]["minSunElevationDeg"]) & (cls >= 0)

    local = t + zone["lon"] / 15 * 3600            # ora solare locale
    day = (local // 86400).astype(np.int64)
    dt = np.array(day, dtype="datetime64[D]")
    doy = (dt - dt.astype("datetime64[Y]")).astype(int)
    month = dt.astype("datetime64[M]").astype(int) % 12

    step_h = float(np.median(np.diff(t))) / 3600    # 1 con dati orari, 3 o 6 con dati più radi
    k = max(1, int(np.ceil(R["day"]["minHours"] / step_h)))
    days = {}
    for i in np.flatnonzero(day_mask):
        days.setdefault(day[i], []).append(i)
    out_cls, out_doy, out_month, hours = [], [], [], []
    for d, idx in days.items():
        c = np.sort(cls[idx])[::-1]
        out_cls.append(c[min(k, len(c)) - 1])   # la classe migliore tenuta per almeno k ore
        out_doy.append(doy[idx[0]]); out_month.append(month[idx[0]]); hours.append(idx)
    return np.array(out_cls), np.array(out_doy), np.array(out_month), hours, h, tp


def summarize(sel, cls, hours, h, tp, good_cls):
    """Classe prevalente, percentili di altezza e periodo, % giorni Good+ per un gruppo di giorni."""
    if not len(sel):
        return None
    idx = np.concatenate([hours[i] for i in sel])
    c = cls[sel]
    q = int(np.bincount(c, minlength=10).argmax())
    h25, h50, h75 = np.percentile(h[idx], [25, 50, 75])
    t25, t50, t75 = np.percentile(tp[idx], [25, 50, 75])
    return [q, round(h25, 1), round(h50, 1), round(h75, 1), round(t25, 1), round(t50, 1), round(t75, 1),
            round(100 * float((c >= good_cls).mean()))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verifica", nargs="*", metavar="ID", help="stampa la tabella mese per mese di queste zone")
    a = ap.parse_args()

    R = json.loads(RULE.read_text())
    labels = [s["label"] for s in json.loads(SCALE.read_text())]
    zones = json.loads(ZONES.read_text())
    good = R["goodClass"]
    out = {"source": "ERA5 via Open-Meteo (onde: era5_ocean, vento: era5), 2005-2024, ore diurne",
           "rule": "data/quality-rule.json", "fields": FIELDS, "zones": {}}
    missing = []
    for z in zones:
        f = RAW / f"{z['id']}.parquet"
        if not f.exists():   # resta nel JSON senza climatologia: l'app la mostra come "dati in arrivo"
            missing.append(z["id"]); out["zones"][z["id"]] = {"wave": None, "wind": None, "weeks": None}; continue
        table = pq.read_table(f)
        meta = {k.decode(): json.loads(v) for k, v in (table.schema.metadata or {}).items() if k.decode().endswith("_grid")}
        cls, doy, month, hours, h, tp = daily(z, table, R)
        week = np.minimum(doy // 7, 51)
        weeks = [summarize(np.flatnonzero(week == w), cls, hours, h, tp, good) for w in range(52)]
        out["zones"][z["id"]] = {"wave": meta.get("wave_grid"), "wind": meta.get("wind_grid"), "weeks": weeks}

        if a.verifica is not None and z["id"] in a.verifica:
            print(f"\n{z['id']} ({z['name']}, {z['region']}), esposizione {z.get('exposure')}°, onde in {meta.get('wave_grid')}")
            print(f"{'mese':5} {'classe prev.':14} {'Good+':>6} {'altezza 25-75':>14} {'periodo':>8}")
            for m in range(12):
                s = summarize(np.flatnonzero(month == m), cls, hours, h, tp, good)
                print(f"{MESI[m]:5} {labels[s[0]]:14} {s[7]:5}% {s[1]:6.1f}-{s[3]:.1f} m {s[5]:6.1f} s")

    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(f"\nscritto {OUT.relative_to(ROOT)}: {len(out['zones'])} zone, {OUT.stat().st_size // 1024} KB"
          + (f"; senza dati grezzi {len(missing)} zone" if missing else ""))


if __name__ == "__main__":
    main()

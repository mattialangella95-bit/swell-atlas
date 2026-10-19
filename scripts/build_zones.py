"""Fase 2: dagli spot grezzi alle zone candidate da revisionare a mano.

Input:  data/raw/spots_raw.json  (gist naotokui, ~5900 spot: name, country, lat, lng come stringhe)
        data/land-50m.json       (coste Natural Earth 1:50m, la stessa del globo)
Output: data/review/zones_candidates.csv  (separatore ;, decimali con virgola per Excel in italiano)

Uso:    .venv/bin/python scripts/build_zones.py [--raggio 60] [--force]
"""
import argparse, csv, json, math, re, sys, unicodedata, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/spots_raw.json"
RAW_URL = "https://gist.githubusercontent.com/naotokui/01c384bf58ca43261eafe6a5e2ad6e85/raw"
LAND = ROOT / "data/land-50m.json"
OUT = ROOT / "data/review/zones_candidates.csv"
# le colonne *_manuale, tieni e note sono della revisione a mano: lo script le lascia vuote
COLUMNS = ["id", "nome", "nome_manuale", "paese", "lat", "lon", "n_spot", "esposizione_gradi", "esposizione_manuale",
           "aeroporto_manuale", "tieni", "note"]
MANUAL_COLS = ["nome_manuale", "esposizione_manuale", "aeroporto_manuale", "tieni", "note"]

R_EARTH = 6371.0
LAND_MAX_KM = 10      # spot sulla terraferma più lontano di così dalla costa: scartato (fiumi, laghi, errori)
DUP_KM = 1            # due spot entro 1 km sono lo stesso spot
DUP_NAME_KM = 50      # stesso nome nello stesso paese entro 50 km: stesso spot
EXPO_RADII_KM = [3, 8, 15, 30, 60, 120]   # anelli su cui si guarda se c'è mare
EXPO_STEP_DEG = 5
EXPO_MIN_R = 0.5      # coerenza minima delle esposizioni degli spot per dare un valore alla zona
EXPO_SAME_DEG = 45    # nella stessa zona solo spot entro 45° dallo spot centrale (quindi entro 90° tra loro)


# ---------- geometria

def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(np.minimum(1, a)))


def destination(lat, lon, bearing, km):
    """Punto a distanza km lungo la rotta bearing (gradi da nord, senso orario)."""
    d, b = km / R_EARTH, np.radians(bearing)
    p1, l1 = np.radians(lat), np.radians(lon)
    p2 = np.arcsin(np.sin(p1) * np.cos(d) + np.cos(p1) * np.sin(d) * np.cos(b))
    l2 = l1 + np.arctan2(np.sin(b) * np.sin(d) * np.cos(p1), np.cos(d) - np.sin(p1) * np.sin(p2))
    return np.degrees(p2), (np.degrees(l2) + 540) % 360 - 180


def load_land(path):
    """TopoJSON world-atlas -> MultiPolygon shapely (decodifica archi quantizzati)."""
    topo = json.loads(path.read_text())
    sx, sy = topo["transform"]["scale"]; tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx):
        pts = []
        for i in idx:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        return pts

    polys = []
    for g in topo["objects"]["land"]["geometries"]:
        groups = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for rings in groups:
            polys.append(Polygon(ring(rings[0]), [ring(r) for r in rings[1:]]))
    # make_valid può restituire una GeometryCollection con pezzi lineari: si tengono solo i poligoni
    parts = shapely.get_parts(shapely.make_valid(MultiPolygon(polys)))
    land = shapely.union_all([p for p in parts if p.geom_type in ("Polygon", "MultiPolygon")])
    shapely.prepare(land)
    return land


def coast_index(land):
    """Costa spezzata in tratti corti dentro un STRtree, per trovare in fretta il punto di costa più vicino."""
    pieces = []
    for line in shapely.get_parts(shapely.line_merge(land.boundary)):
        c = list(line.coords)
        for i in range(0, len(c) - 1, 40):
            pieces.append(LineString(c[i:i + 41]))
    return shapely.STRtree(pieces), pieces


def coast_distance_km(lat, lon, tree, pieces):
    pts = shapely.points(lon, lat)
    idx = tree.query_nearest(pts, all_matches=False)[1]
    near = shapely.shortest_line(pts, np.array(pieces, dtype=object)[idx])
    end = shapely.get_point(near, 1)
    return haversine(lat, lon, shapely.get_y(end), shapely.get_x(end))


def exposure(lat, lon, land):
    """Direzione verso il mare aperto in gradi (0 = nord, 90 = est) per ogni spot, None se non stimabile.

    Su anelli a più distanze si guarda in quali direzioni c'è mare; la media vettoriale
    delle direzioni libere punta verso il largo. Se c'è mare quasi ovunque (isolotti non
    presenti nella costa 1:50m) o il vettore è troppo debole, l'esposizione resta vuota.
    """
    bearings = np.arange(0, 360, EXPO_STEP_DEG, dtype=float)
    n, nb = len(lat), len(bearings)
    water = np.zeros((n, nb))
    for r in EXPO_RADII_KM:
        la, lo = destination(lat[:, None], lon[:, None], bearings[None, :], r)
        water += ~shapely.contains_xy(land, lo.ravel(), la.ravel()).reshape(n, nb)
    water /= len(EXPO_RADII_KM)
    b = np.radians(bearings)
    vx, vy = (water * np.sin(b)).mean(1), (water * np.cos(b)).mean(1)
    strength = np.hypot(vx, vy)
    deg = (np.degrees(np.arctan2(vx, vy)) + 360) % 360
    ok = (water.mean(1) < 0.97) & (strength > 0.05)
    return [round(float(d)) % 360 if o else None for d, o in zip(deg, ok)]


def circular_mean(degs):
    v = [d for d in degs if d is not None]
    if not v:
        return None
    x = sum(math.sin(math.radians(d)) for d in v) / len(v)
    y = sum(math.cos(math.radians(d)) for d in v) / len(v)
    if math.hypot(x, y) < EXPO_MIN_R:
        return None
    return round((math.degrees(math.atan2(x, y)) + 360) % 360) % 360


# ---------- spot

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def slug(s):
    return re.sub(r"\s+", "-", norm(s))[:40] or "zona"


def parse_spots(raw):
    spots, bad = [], 0
    for x in raw:
        try:
            lat, lon = float(x["lat"]), float(x["lng"])
        except (TypeError, ValueError):
            bad += 1; continue
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            bad += 1; continue
        parts = [p.strip() for p in x["country"].split(",")]
        spots.append({"name": x["name"].strip(), "country": parts[0], "region": ", ".join(parts[1:]), "lat": lat, "lon": lon})
    return spots, bad


def grid_neighbors(spots, km):
    """Per ogni spot gli indici degli altri entro km (griglia di celle da ~km)."""
    cell = km / 111.0
    grid = defaultdict(list)
    for i, s in enumerate(spots):
        grid[(int(s["lat"] // cell), int(s["lon"] // cell))].append(i)
    out = []
    for i, s in enumerate(spots):
        ci, cj = int(s["lat"] // cell), int(s["lon"] // cell)
        lonspan = int(math.ceil(1 / max(0.05, math.cos(math.radians(s["lat"])))))
        cand = [j for a in range(ci - 1, ci + 2) for b in range(cj - lonspan, cj + lonspan + 1) for j in grid.get((a, b), ())]
        cand = np.array([j for j in cand if j != i], dtype=int)
        if len(cand):
            d = haversine(s["lat"], s["lon"], np.array([spots[j]["lat"] for j in cand]), np.array([spots[j]["lon"] for j in cand]))
            cand = cand[d <= km]
        out.append(cand.tolist())
    return out


def dedupe(spots):
    """Tiene il primo spot (ordine alfabetico) e scarta i doppioni: entro 1 km, o stesso nome e paese entro 50 km."""
    spots = sorted(spots, key=lambda s: (s["country"], norm(s["name"]), s["lat"], s["lon"]))
    near = grid_neighbors(spots, DUP_KM)
    keep, dropped = [], set()
    by_name = defaultdict(list)
    for i, s in enumerate(spots):
        if i in dropped:
            continue
        key = (s["country"], norm(s["name"]))
        if any(haversine(s["lat"], s["lon"], k["lat"], k["lon"]) <= DUP_NAME_KM for k in by_name[key]):
            continue
        keep.append(s); by_name[key].append(s)
        dropped.update(j for j in near[i] if j > i)
    return keep


# ---------- zone

def same_side(a, b):
    """Due esposizioni compatibili: differenza entro EXPO_SAME_DEG (una mancante va bene con tutto)."""
    return a is None or b is None or abs((a - b + 180) % 360 - 180) <= EXPO_SAME_DEG


def cluster(spots, radius):
    """Clustering a leader per paese: lo spot con più vicini liberi entro radius (e con la costa
    rivolta dalla stessa parte) diventa il centro di una zona e si prende tutti quei vicini.
    Si ripete finché restano spot. Così ad esempio North Shore e South Shore di Oahu restano separati."""
    zones = []
    by_country = defaultdict(list)
    for s in spots:
        by_country[s["country"]].append(s)
    for country in sorted(by_country):
        cs = by_country[country]
        neigh = [[j for j in nb if same_side(cs[i]["expo"], cs[j]["expo"])] for i, nb in enumerate(grid_neighbors(cs, radius))]
        free = set(range(len(cs)))
        while free:
            lead = max(sorted(free), key=lambda i: (sum(j in free for j in neigh[i]), -i))
            members = [lead] + [j for j in neigh[lead] if j in free]
            free -= set(members)
            zones.append({"country": country, "leader": cs[lead], "spots": [cs[j] for j in members]})
    return zones


def center(spots):
    """Centro come media vettoriale (regge anche a cavallo dell'antimeridiano)."""
    x = y = z = 0.0
    for s in spots:
        p, l = math.radians(s["lat"]), math.radians(s["lon"])
        x += math.cos(p) * math.cos(l); y += math.cos(p) * math.sin(l); z += math.sin(p)
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))


def fmt(v, nd):
    return "" if v is None else f"{v:.{nd}f}".replace(".", ",")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raggio", type=float, default=60, help="raggio zona in km (default 60)")
    ap.add_argument("--force", action="store_true", help="sovrascrive il CSV anche se contiene una revisione")
    a = ap.parse_args()

    if OUT.exists() and not a.force:
        with OUT.open(encoding="utf-8-sig") as f:
            if any((r.get(c) or "").strip() for r in csv.DictReader(f, delimiter=";") for c in MANUAL_COLS):
                sys.exit(f"{OUT.relative_to(ROOT)} contiene già una revisione ({', '.join(MANUAL_COLS)}). Usa --force per sovrascriverlo.")

    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        print("scarico", RAW_URL)
        urllib.request.urlretrieve(RAW_URL, RAW)
    raw = json.loads(RAW.read_text())
    spots, bad = parse_spots(raw)
    print(f"spot grezzi {len(raw)}, coordinate non valide {bad}")

    land = load_land(LAND)
    tree, pieces = coast_index(land)
    lat = np.array([s["lat"] for s in spots]); lon = np.array([s["lon"] for s in spots])
    on_land = shapely.contains_xy(land, lon, lat)
    dist = coast_distance_km(lat, lon, tree, pieces)
    inland = on_land & (dist > LAND_MAX_KM)
    print(f"sulla terraferma a più di {LAND_MAX_KM} km dalla costa: {int(inland.sum())} scartati")
    spots = [s for s, x in zip(spots, inland) if not x]

    n0 = len(spots)
    spots = dedupe(spots)
    print(f"doppioni scartati {n0 - len(spots)}, spot validi {len(spots)}")

    expo = exposure(np.array([s["lat"] for s in spots]), np.array([s["lon"] for s in spots]), land)
    for s, e in zip(spots, expo):
        s["expo"] = e

    zones = cluster(spots, a.raggio)
    rows, used = [], Counter()
    for z in zones:
        lead = z["leader"]
        regions = Counter(s["region"] for s in z["spots"] if s["region"])
        region = regions.most_common(1)[0][0] if regions else ""
        lat_c, lon_c = center(z["spots"])
        zid = slug(f'{z["country"]} {lead["name"]}')
        used[zid] += 1
        if used[zid] > 1:
            zid += f"-{used[zid]}"
        rows.append({"id": zid, "nome": lead["name"] + (f" · {region}" if region else ""), "paese": z["country"],
                     "lat": lat_c, "lon": lon_c, "n_spot": len(z["spots"]),
                     "esposizione_gradi": circular_mean([s["expo"] for s in z["spots"]])})
    rows.sort(key=lambda r: (-r["n_spot"], r["id"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([r["id"], r["nome"], "", r["paese"], fmt(r["lat"], 4), fmt(r["lon"], 4), r["n_spot"],
                        "" if r["esposizione_gradi"] is None else r["esposizione_gradi"], "", "", "", ""])
    sizes = [r["n_spot"] for r in rows]
    print(f"zone {len(rows)} (raggio {a.raggio:g} km): con 1 spot {sizes.count(1)}, max {max(sizes)}, "
          f"senza esposizione {sum(r['esposizione_gradi'] is None for r in rows)}")
    print("scritto", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

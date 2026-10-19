"""Fase 2: dal CSV revisionato a data/zones.json (formato letto dall'app).

Tiene solo le righe con tieni = si. Se compilate, nome_manuale ed esposizione_manuale
prendono il posto di nome ed esposizione_gradi (nome_manuale: "Nome" oppure "Nome · Regione";
senza regione resta quella proposta). Per ogni zona aggiunge l'aeroporto di riferimento
(il più vicino con voli di linea, da OurAirports) e i parametri demo per i dati onda finti
di getZoneWeeks, che spariranno in fase 3.

Input:  data/review/zones_candidates.csv  (oppure il percorso passato con --csv)
        data/raw/airports.csv              (OurAirports, scaricato se manca)
Output: data/zones.json

Uso:    .venv/bin/python scripts/apply_review.py
        .venv/bin/python scripts/apply_review.py --preseleziona 150   # segna "si" sulle 150 zone con più spot
"""
import argparse, csv, io, json, math, random, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data/review/zones_candidates.csv"
AIRPORTS = ROOT / "data/raw/airports.csv"
AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OUT = ROOT / "data/zones.json"

YES = {"si", "sì", "s", "x", "1", "yes", "y"}
AIRPORT_TYPES = {"large_airport", "medium_airport"}
# come nel prototipo (Taghazout, Fuerteventura): da qui i voli si stimano come se fossero in Europa
NEAR_EUROPE = {"Morocco", "Canary"}


def read_csv(path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252"):   # Excel a volte risalva in cp1252
        try:
            text = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    delim = ";" if text.splitlines()[0].count(";") >= text.splitlines()[0].count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader(); w.writerows(rows)


def num(s):
    return float(str(s).strip().replace(",", "."))


def load_airports():
    if not AIRPORTS.exists():
        AIRPORTS.parent.mkdir(parents=True, exist_ok=True)
        print("scarico", AIRPORTS_URL)
        urllib.request.urlretrieve(AIRPORTS_URL, AIRPORTS)
    with AIRPORTS.open(encoding="utf-8") as f:
        return [{"code": r["iata_code"], "lat": float(r["latitude_deg"]), "lon": float(r["longitude_deg"])}
                for r in csv.DictReader(f)
                if r["type"] in AIRPORT_TYPES and r["scheduled_service"] == "yes" and len(r["iata_code"]) == 3]


def km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(min(1, a)))


def demo_params(zid, lat):
    """Parametri finti per getZoneWeeks: picco d'inverno nel proprio emisfero, il resto casuale ma stabile per id."""
    r = random.Random(zid)
    peak = (2 if lat >= 0 else 28) + r.randint(-6, 6) if abs(lat) > 10 else r.randint(0, 51)
    h0 = round(r.uniform(0.4, 1.0), 1); t0 = r.randint(7, 12)
    return {"peak": peak % 52, "base": round(r.uniform(1.5, 3.5), 1), "amp": round(r.uniform(4.5, 6.5), 1),
            "height": [h0, round(h0 + r.uniform(1.2, 2.4), 1)], "period": [t0, t0 + r.randint(4, 6)]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=CSV, help="CSV revisionato (default data/review/zones_candidates.csv)")
    ap.add_argument("--preseleziona", type=int, metavar="N",
                    help='scrive "si" nella colonna tieni delle N zone con più spot (solo se tieni è ancora tutta vuota)')
    a = ap.parse_args()

    fields, rows = read_csv(a.csv)
    if a.preseleziona:
        if any(r["tieni"].strip() for r in rows):
            sys.exit("La colonna tieni è già compilata: non la sovrascrivo.")
        for r in sorted(rows, key=lambda r: -int(r["n_spot"]))[:a.preseleziona]:
            r["tieni"] = "si"
        write_csv(a.csv, fields, rows)
        print(f'segnate {a.preseleziona} zone con tieni = si in {a.csv.relative_to(ROOT)}')

    kept = [r for r in rows if r["tieni"].strip().lower() in YES]
    if not kept:
        sys.exit("Nessuna riga con tieni = si.")
    airports = load_airports()
    zones, ids = [], set()
    for r in kept:
        zid = r["id"].strip()
        if zid in ids:
            sys.exit(f"id ripetuto nel CSV: {zid}")
        ids.add(zid)
        lat, lon = num(r["lat"]), num(r["lon"])
        # le colonne *_manuale, se compilate, vincono su quelle calcolate
        name, _, region = r["nome"].partition(" · ")
        manual = (r.get("nome_manuale") or "").strip()
        if manual:
            m_name, sep, m_region = manual.partition(" · ")
            name, region = m_name, (m_region if sep else region)
        country = r["paese"].strip()
        expo = (r.get("esposizione_manuale") or "").strip() or r["esposizione_gradi"].strip()
        try:
            expo = int(round(num(expo))) % 360 if expo else None
        except ValueError:
            sys.exit(f"{zid}: esposizione non valida {expo!r} (servono gradi 0-359)")
        apt = min(airports, key=lambda p: km(lat, lon, p["lat"], p["lon"]))
        airport = {"code": apt["code"], "lat": apt["lat"], "lon": apt["lon"]}
        if country in NEAR_EUROPE:
            airport["nearEurope"] = True
        zones.append({"id": zid, "name": name.strip(), "region": ", ".join(x for x in (country, region.strip()) if x),
                      "lat": round(lat, 4), "lon": round(lon, 4), "spots": int(r["n_spot"]),
                      "exposure": expo,
                      "airport": airport, "demo": demo_params(zid, lat)})

    OUT.write_text(json.dumps(zones, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    far = [z for z in zones if km(z["lat"], z["lon"], z["airport"]["lat"], z["airport"]["lon"]) > 200]
    print(f"scritte {len(zones)} zone in {OUT.relative_to(ROOT)} (aeroporto a più di 200 km: {len(far)})")
    for z in far:
        print(f'  {z["id"]}: {z["airport"]["code"]} a {km(z["lat"], z["lon"], z["airport"]["lat"], z["airport"]["lon"]):.0f} km')


if __name__ == "__main__":
    main()

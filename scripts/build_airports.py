"""Fase 4: aeroporti da OurAirports.

Scarica airports.csv e runways.csv in data/raw/airports/ (se mancano) e scrive
data/airports.json: le partenze italiane, cioè gli aeroporti large e medium con voli di
linea e codice IATA, più poche partenze di confine (Nizza). Le funzioni di caricamento servono anche a scripts/apply_review.py.

Uso:    .venv/bin/python scripts/build_airports.py            # usa i CSV già scaricati
        .venv/bin/python scripts/build_airports.py --scarica  # riscarica da OurAirports
"""
import argparse, csv, json, math, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/airports"
BASE_URL = "https://davidmegginson.github.io/ourairports-data/"
OUT = ROOT / "data/airports.json"
TYPES = {"large_airport": "large", "medium_airport": "medium"}
# nomi italiani mostrati nella scelta della partenza (OurAirports ha nomi inglesi e comuni come "Ferno (VA)")
LABELS = {"BRI": "Bari", "BLQ": "Bologna", "BDS": "Brindisi", "CAG": "Cagliari", "VRN": "Verona", "TRN": "Torino",
          "CTA": "Catania", "MXP": "Milano Malpensa", "FLR": "Firenze", "GOA": "Genova", "SUF": "Lamezia Terme",
          "NAP": "Napoli", "OLB": "Olbia", "BGY": "Bergamo Orio al Serio", "PMO": "Palermo", "PEG": "Perugia",
          "PSR": "Pescara", "PSA": "Pisa", "RMI": "Rimini", "CIA": "Roma Ciampino", "FCO": "Roma Fiumicino",
          "TRS": "Trieste", "LIN": "Milano Linate", "TSF": "Treviso", "VCE": "Venezia", "AHO": "Alghero",
          "BZO": "Bolzano", "EBA": "Isola d'Elba", "CIY": "Comiso", "AOI": "Ancona", "FOG": "Foggia", "FRL": "Forlì",
          "CRV": "Crotone", "LMP": "Lampedusa", "CUF": "Cuneo", "VBS": "Brescia", "PNL": "Pantelleria", "PMF": "Parma",
          "REG": "Reggio Calabria", "QSR": "Salerno", "TPS": "Trapani", "NCE": "Nizza"}
# partenze fuori dall'Italia ma comode da qui
EXTRA_DEPARTURES = {"NCE"}


def download(force=False):
    RAW.mkdir(parents=True, exist_ok=True)
    for name in ("airports.csv", "runways.csv"):
        if force or not (RAW / name).exists():
            print("scarico", BASE_URL + name)
            urllib.request.urlretrieve(BASE_URL + name, RAW / name)


def longest_runways():
    """ident aeroporto -> pista aperta più lunga in piedi (indicatore di grandezza per i medium)."""
    out = {}
    with (RAW / "runways.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["closed"] == "1" or not r["length_ft"].strip():
                continue
            k = r["airport_ident"]
            out[k] = max(out.get(k, 0), int(float(r["length_ft"])))
    return out


def load_scheduled():
    """Aeroporti large e medium con voli di linea e codice IATA."""
    download()
    runways = longest_runways()
    with (RAW / "airports.csv").open(encoding="utf-8") as f:
        return [{"code": r["iata_code"], "name": r["name"], "city": r["municipality"], "country": r["iso_country"],
                 "type": TYPES[r["type"]], "lat": float(r["latitude_deg"]), "lon": float(r["longitude_deg"]),
                 "runway_ft": runways.get(r["ident"], 0)}
                for r in csv.DictReader(f)
                if r["type"] in TYPES and r["scheduled_service"] == "yes" and len(r["iata_code"]) == 3]


def load_by_iata():
    """Tutti gli aeroporti con codice IATA, di qualunque tipo (per aeroporto_manuale)."""
    download()
    with (RAW / "airports.csv").open(encoding="utf-8") as f:
        return {r["iata_code"]: {"code": r["iata_code"], "name": r["name"], "city": r["municipality"],
                                 "type": TYPES.get(r["type"], "small"), "lat": float(r["latitude_deg"]),
                                 "lon": float(r["longitude_deg"])}
                for r in csv.DictReader(f) if len(r["iata_code"]) == 3 and r["type"] != "closed"}


def km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lon2 - lon1)
    a = math.sin(math.radians(lat2 - lat1) / 2) ** 2 + math.cos(p1) * math.cos(math.radians(lat2)) * math.sin(p2 / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(min(1, a)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scarica", action="store_true", help="riscarica i CSV da OurAirports")
    a = ap.parse_args()
    download(a.scarica)
    it = sorted((x for x in load_scheduled() if x["country"] == "IT" or x["code"] in EXTRA_DEPARTURES),
                key=lambda x: (x["type"] != "large", x["city"], x["code"]))
    deps = [{"code": x["code"], "label": LABELS.get(x["code"], x["city"]), "name": x["name"], "city": x["city"],
             "type": x["type"], "lat": round(x["lat"], 4), "lon": round(x["lon"], 4)} for x in it]
    deps.sort(key=lambda d: d["label"])
    missing = [d["code"] for d in deps if d["code"] not in LABELS]
    if missing:
        print("senza nome italiano (uso il comune):", ", ".join(missing))
    OUT.write_text(json.dumps(deps, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"scritte {len(deps)} partenze italiane in {OUT.relative_to(ROOT)} "
          f"({sum(d['type'] == 'large' for d in deps)} large, {sum(d['type'] == 'medium' for d in deps)} medium)")


if __name__ == "__main__":
    main()

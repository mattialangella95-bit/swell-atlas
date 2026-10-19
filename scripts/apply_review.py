"""Fase 2: dal CSV revisionato a data/zones.json (formato letto dall'app).

Tiene solo le righe con tieni = si. Se compilate, nome_manuale ed esposizione_manuale
prendono il posto di nome ed esposizione_gradi (nome_manuale: "Nome" oppure "Nome · Regione";
senza regione resta quella proposta). Per ogni zona aggiunge due aeroporti (OurAirports):
  - airport_local: il più vicino con voli di linea (large o medium);
  - airport_main: quello internazionale di riferimento per i voli, cioè il large più vicino
    entro 300 km, altrimenti il medium con la pista più lunga entro 300 km, altrimenti il locale.
    Se compilata, la colonna aeroporto_manuale (codice IATA) vince.

Input:  data/review/zones_candidates.csv  (oppure il percorso passato con --csv)
        data/raw/airports/                 (OurAirports, scaricato se manca)
Output: data/zones.json

Uso:    .venv/bin/python scripts/apply_review.py
        .venv/bin/python scripts/apply_review.py --preseleziona 150   # segna "si" sulle 150 zone con più spot
"""
import argparse, csv, io, json, sys
from pathlib import Path

from build_airports import km, load_by_iata, load_scheduled

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data/review/zones_candidates.csv"
OUT = ROOT / "data/zones.json"

YES = {"si", "sì", "s", "x", "1", "yes", "y"}
MAIN_KM = 300   # raggio per l'aeroporto principale (internazionale) di una zona


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


def airport_info(a):
    return {"code": a["code"], "name": a["name"], "type": a["type"], "lat": round(a["lat"], 4), "lon": round(a["lon"], 4)}


def pick_airports(lat, lon, scheduled):
    """(principale, locale). Locale: il più vicino con voli di linea. Principale: il large più vicino
    entro MAIN_KM, altrimenti il medium con la pista più lunga entro MAIN_KM, altrimenti il locale."""
    dist = [(km(lat, lon, a["lat"], a["lon"]), a) for a in scheduled]
    local = min(dist, key=lambda x: x[0])[1]
    near = [(d, a) for d, a in dist if d <= MAIN_KM]
    large = [x for x in near if x[1]["type"] == "large"]
    if large:
        return min(large, key=lambda x: x[0])[1], local
    medium = [x for x in near if x[1]["type"] == "medium"]
    if medium:
        return max(medium, key=lambda x: (x[1]["runway_ft"], -x[0]))[1], local
    return local, local


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
    scheduled, by_iata = load_scheduled(), load_by_iata()
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
        main_apt, local_apt = pick_airports(lat, lon, scheduled)
        manual_apt = (r.get("aeroporto_manuale") or "").strip().upper()
        if manual_apt:
            if manual_apt not in by_iata:
                sys.exit(f"{zid}: aeroporto_manuale {manual_apt!r} non trovato in OurAirports")
            main_apt = by_iata[manual_apt]
        zones.append({"id": zid, "name": name.strip(), "region": ", ".join(x for x in (country, region.strip()) if x),
                      "lat": round(lat, 4), "lon": round(lon, 4), "spots": int(r["n_spot"]),
                      "exposure": expo,
                      "airport_main": airport_info(main_apt), "airport_local": airport_info(local_apt)})

    OUT.write_text(json.dumps(zones, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    d = lambda z: km(z["lat"], z["lon"], z["airport_main"]["lat"], z["airport_main"]["lon"])
    changed = sum(z["airport_main"]["code"] != z["airport_local"]["code"] for z in zones)
    print(f"scritte {len(zones)} zone in {OUT.relative_to(ROOT)}: aeroporto principale diverso dal locale in {changed}, "
          f"principale a più di {MAIN_KM} km in {sum(d(z) > MAIN_KM for z in zones)}")
    for z in zones:
        if d(z) > MAIN_KM:
            print(f'  {z["id"]}: {z["airport_main"]["code"]} a {d(z):.0f} km')


if __name__ == "__main__":
    main()

"""Costo della vita indicativo per paese (€, €€, €€€), rispetto all'Italia.

Fonte: Banca Mondiale. Livello dei prezzi = fattore di conversione PPP (PA.NUS.PPP, valuta locale per
dollaro internazionale) diviso il cambio ufficiale (PA.NUS.FCRF, valuta locale per dollaro), ultimo anno
disponibile; poi diviso il valore dell'Italia. È un dato nazionale e indicativo: le isole turistiche
possono costare molto più della media del loro paese.

Uso:    .venv/bin/python scripts/build_costs.py      # scrive data/costs.json
"""
import json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/costs.json"
API = "https://api.worldbank.org/v2/country/all/indicator/{}?format=json&per_page=400&mrnev=1"
LEVELS = [(0.7, 1), (1.1, 2), (float("inf"), 3)]   # rapporto con l'Italia: sotto 0,7 €, fino a 1,1 €€, oltre €€€
EURO = {"BEL", "CYP", "ESP", "FRA", "GRC", "IRL", "ITA", "NLD", "PRT"}   # cambio dell'euro (EMU)
USD = {"ECU", "SLV", "PRI", "USA"}                                       # usano il dollaro
# paese delle zone (campo country degli spot) -> codice ISO3; i territori seguono il paese a cui appartengono
ISO3 = {"Argentina": "ARG", "Australia": "AUS", "Barbados": "BRB", "Belgium": "BEL", "Brazil": "BRA",
        "British Virgin": "VGB", "Canary": "ESP", "Chile": "CHL", "Costa Rica": "CRI", "Cyprus": "CYP",
        "Ecuador": "ECU", "El Salvador": "SLV", "France": "FRA", "French Polynesia": "PYF", "Greece": "GRC",
        "Indonesia": "IDN", "Ireland": "IRL", "Israel": "ISR", "Italy": "ITA", "Japan": "JPN", "Madeira": "PRT",
        "Azores": "PRT", "Maldives": "MDV", "Mexico": "MEX", "Morocco": "MAR", "Netherlands": "NLD",
        "New Zealand": "NZL", "Nicaragua": "NIC", "Peru": "PER", "Philippines": "PHL", "Portugal": "PRT",
        "Puerto Rico": "PRI", "Reunion": "FRA", "Senegal": "SEN", "Seychelles": "SYC", "South Africa": "ZAF",
        "Spain": "ESP", "Sri Lanka": "LKA", "St Barthelemy": "BLM", "UK": "GBR", "USA": "USA", "Uruguay": "URY"}
# senza dato della Banca Mondiale: livello messo a mano (isole notoriamente care)
MANUAL = {"VGB": 3, "PYF": 3, "BLM": 3}


def indicator(code):
    with urllib.request.urlopen(API.format(code), timeout=60) as r:
        d = json.load(r)
    return {x["countryiso3code"]: (x["value"], x["date"]) for x in d[1] if x["value"]}


def main():
    ppp, fx = indicator("PA.NUS.PPP"), indicator("PA.NUS.FCRF")
    def level_of(c):
        rate = fx.get(c) or (fx.get("EMU") if c in EURO else (1.0, None) if c in USD else None)
        return (ppp[c][0] / rate[0], ppp[c][1]) if c in ppp and rate else None
    it = level_of("ITA")[0]
    zones = json.loads((ROOT / "data/zones.json").read_text())
    out, missing = {}, []
    for name in sorted({z["region"].split(", ")[0] for z in zones}):
        c = ISO3.get(name)
        if not c:
            missing.append(name); continue
        v = level_of(c)
        if v:
            ratio = round(v[0] / it, 2)
            out[name] = {"iso3": c, "ratio": ratio, "level": next(n for lim, n in LEVELS if ratio < lim), "year": v[1]}
        elif c in MANUAL:
            out[name] = {"iso3": c, "ratio": None, "level": MANUAL[c], "year": None, "manual": True}
        else:
            missing.append(name)
    OUT.write_text(json.dumps({
        "_note": "Costo della vita indicativo rispetto all'Italia (Banca Mondiale: PPP / cambio). level 1 = €, 2 = €€, 3 = €€€. "
                 "manual = senza dato, livello messo a mano. Rigenerare con scripts/build_costs.py.",
        "countries": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"scritti {len(out)} paesi in {OUT.relative_to(ROOT)}" + (f"; senza codice o dato: {', '.join(missing)}" if missing else ""))
    for k in (1, 2, 3):
        print("€" * k, ", ".join(n for n, v in out.items() if v["level"] == k))


if __name__ == "__main__":
    main()

"""Segnalazioni dell'app (tabella swell_feedback su Supabase).

Usa la secret key da .env (SUPABASE_URL, SUPABASE_SECRET_KEY), che resta fuori da git.

Uso:    .venv/bin/python scripts/feedback.py                 # elenca le nuove
        .venv/bin/python scripts/feedback.py --tutte         # elenca tutte
        .venv/bin/python scripts/feedback.py letta 3 4       # segna come lette
        .venv/bin/python scripts/feedback.py risolta 3       # segna come risolte
"""
import argparse, json, sys
from datetime import datetime

from supa import env, request

KINDS = {"bug": "bug", "miglioria": "miglioria", "dato_zona": "dato sbagliato su una zona"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("azione", nargs="?", choices=["letta", "risolta"], help="cambia lo stato delle segnalazioni indicate")
    ap.add_argument("id", nargs="*", type=int)
    ap.add_argument("--tutte", action="store_true", help="elenca anche quelle lette e risolte")
    a = ap.parse_args()
    e = env()
    url, key = e.get("SUPABASE_URL"), e.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        sys.exit("Mancano SUPABASE_URL e SUPABASE_SECRET_KEY in .env (vedi .env.example).")
    base = f"{url}/rest/v1/swell_feedback"

    if a.azione:
        if not a.id:
            sys.exit("Indica gli id, es. feedback.py letta 3 4")
        code, rows = request("PATCH", f"{base}?id=in.({','.join(map(str, a.id))})", key, body={"status": a.azione},
                             prefer="return=representation")
        if code >= 300:
            sys.exit(f"Errore {code}: {rows}")
        print(f"{len(rows)} segnalazioni segnate come {a.azione}: {', '.join(str(r['id']) for r in rows)}")
        return

    q = "order=created_at.asc" + ("" if a.tutte else "&status=eq.nuova")
    code, rows = request("GET", f"{base}?{q}", key)
    if code >= 300:
        sys.exit(f"Errore {code}: {rows}")
    if not rows:
        print("Nessuna segnalazione" + ("" if a.tutte else " nuova") + ".")
        return
    for r in rows:
        when = datetime.fromisoformat(r["created_at"]).astimezone().strftime("%d/%m/%Y %H:%M")
        st = r.get("app_state") or {}
        print(f"#{r['id']}  {when}  [{r['status']}]  {KINDS.get(r['kind'], r['kind'])}"
              + (f"  zona {r['zone_id']}" if r.get("zone_id") else "")
              + ("  (utente registrato)" if r.get("user_id") else "  (anonima)"))
        print(f"    {r['message']}")
        print(f"    stato app: settimana {st.get('settimana')}, zona {st.get('zona')}, partenza {st.get('partenza')} · {r.get('page')}")
        print(f"    {r.get('user_agent', '')[:110]}\n")
    print(f"{len(rows)} segnalazioni. Per cambiarne lo stato: feedback.py letta <id> / risolta <id>")


if __name__ == "__main__":
    main()

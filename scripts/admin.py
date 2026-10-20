"""Admin dell'app (tabella swell_admins): chi è qui vede e gestisce le segnalazioni nel pannello profilo.

L'utente deve essere entrato almeno una volta nell'app (link via mail), così esiste in Supabase Auth.
Usa la secret key da .env (SUPABASE_URL, SUPABASE_SECRET_KEY).

Uso:    .venv/bin/python scripts/admin.py                     # elenco admin
        .venv/bin/python scripts/admin.py aggiungi tu@mail.it
        .venv/bin/python scripts/admin.py togli tu@mail.it
"""
import argparse, sys

from supa import env, request


def users(url, key):
    out, page = [], 1
    while True:
        c, r = request("GET", f"{url}/auth/v1/admin/users?page={page}&per_page=200", key)
        if c >= 300:
            sys.exit(f"Errore {c}: {r}")
        batch = r.get("users", [])
        out += batch
        if len(batch) < 200:
            return out
        page += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("azione", nargs="?", choices=["aggiungi", "togli"])
    ap.add_argument("email", nargs="?")
    a = ap.parse_args()
    e = env()
    url, key = e.get("SUPABASE_URL"), e.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        sys.exit("Mancano SUPABASE_URL e SUPABASE_SECRET_KEY in .env.")
    by_id = {u["id"]: u.get("email") for u in users(url, key)}

    if a.azione:
        if not a.email:
            sys.exit("Indica la mail, es. admin.py aggiungi tu@mail.it")
        uid = next((i for i, m in by_id.items() if (m or "").lower() == a.email.lower()), None)
        if not uid:
            sys.exit(f"{a.email} non ha ancora un account: entra una volta nell'app con il link via mail, poi riprova.")
        if a.azione == "aggiungi":
            c, r = request("POST", f"{url}/rest/v1/swell_admins", key, body={"user_id": uid},
                           prefer="resolution=ignore-duplicates,return=minimal")
        else:
            c, r = request("DELETE", f"{url}/rest/v1/swell_admins?user_id=eq.{uid}", key)
        if c >= 300:
            sys.exit(f"Errore {c}: {r}")
        print(f"{a.email}: {'ora è admin' if a.azione == 'aggiungi' else 'non è più admin'}")

    c, r = request("GET", f"{url}/rest/v1/swell_admins?select=user_id,created_at", key)
    if c >= 300:
        sys.exit(f"Errore {c}: {r} (la migrazione swell_admin è stata eseguita?)")
    print("admin:", ", ".join(by_id.get(x["user_id"], x["user_id"]) for x in r) or "nessuno")


if __name__ == "__main__":
    main()

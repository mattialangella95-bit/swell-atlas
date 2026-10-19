"""Collaudo della Row Level Security sul progetto Supabase vero.

Crea due utenti di prova (con la chiave di servizio, già confermati), li fa entrare con la chiave
anon e verifica che:
  - ognuno veda e modifichi solo profilo e preferiti propri;
  - le segnalazioni anonime entrino ma non si leggano né con la chiave anon né da utente;
  - non si possa segnalare a nome di un altro utente o con uno stato diverso da "nuova".
Alla fine cancella utenti e righe di prova (anche se un controllo fallisce).

Serve .env con SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY e le migrazioni eseguite.
Uso:    .venv/bin/python scripts/test_rls.py
"""
import secrets, sys
from urllib.parse import quote

from supa import env, request

E = env()
URL, ANON, SERVICE = E.get("SUPABASE_URL"), E.get("SUPABASE_PUBLISHABLE_KEY"), E.get("SUPABASE_SECRET_KEY")
REST, AUTH = f"{URL}/rest/v1", f"{URL}/auth/v1"
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'OK  ' if ok else 'NO  '} {name}" + (f"  ({detail})" if detail and not ok else ""))


def create_user(tag):
    email = f"swell-test-{tag}-{secrets.token_hex(4)}@example.com"
    password = secrets.token_urlsafe(16)
    code, u = request("POST", f"{AUTH}/admin/users", SERVICE, body={"email": email, "password": password, "email_confirm": True})
    if code >= 300:
        sys.exit(f"Non riesco a creare l'utente di prova: {code} {u}")
    code, t = request("POST", f"{AUTH}/token?grant_type=password", ANON, body={"email": email, "password": password})
    if code >= 300:
        sys.exit(f"Non riesco a entrare con l'utente di prova: {code} {t}")
    return u["id"], t["access_token"]


def main():
    if not (URL and ANON and SERVICE):
        sys.exit("Mancano SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY o SUPABASE_SECRET_KEY in .env (vedi .env.example).")
    marker = "test_rls_" + secrets.token_hex(4)   # senza spazi: finisce nei filtri dell'URL
    a_id, a_tok = create_user("a")
    b_id, b_tok = create_user("b")
    try:
        # profili e preferiti propri
        for uid, tok, ap, zone in ((a_id, a_tok, "GOA", "usa-graters"), (b_id, b_tok, "MXP", "indonesia-medewi")):
            c, r = request("POST", f"{REST}/swell_profiles", ANON, tok, {"id": uid, "home_airport": ap, "surf_level": "intermedio"})
            check(f"utente crea il proprio profilo ({ap})", c == 201, f"{c} {r}")
            c, r = request("POST", f"{REST}/swell_favorites", ANON, tok, {"user_id": uid, "zone_id": zone})
            check(f"utente aggiunge un proprio preferito ({zone})", c == 201, f"{c} {r}")

        c, r = request("GET", f"{REST}/swell_favorites?select=user_id,zone_id", ANON, a_tok)
        check("A vede solo i propri preferiti", c == 200 and [x["zone_id"] for x in r] == ["usa-graters"], f"{c} {r}")
        c, r = request("GET", f"{REST}/swell_favorites?select=user_id,zone_id", ANON, b_tok)
        check("B vede solo i propri preferiti", c == 200 and [x["zone_id"] for x in r] == ["indonesia-medewi"], f"{c} {r}")
        c, r = request("GET", f"{REST}/swell_profiles?select=id", ANON, a_tok)
        check("A vede solo il proprio profilo", c == 200 and [x["id"] for x in r] == [a_id], f"{c} {r}")
        c, r = request("POST", f"{REST}/swell_favorites", ANON, a_tok, {"user_id": b_id, "zone_id": "france-le-penon"})
        check("A non può aggiungere preferiti a nome di B", c in (401, 403), f"{c} {r}")
        c, r = request("PATCH", f"{REST}/swell_favorites?user_id=eq.{b_id}", ANON, a_tok, {"note": "manomessa"}, "return=representation")
        check("A non può modificare i preferiti di B", c == 200 and r == [], f"{c} {r}")
        c, r = request("DELETE", f"{REST}/swell_favorites?user_id=eq.{b_id}", ANON, a_tok, prefer="return=representation")
        check("A non può cancellare i preferiti di B", c == 200 and r == [], f"{c} {r}")
        c, r = request("PATCH", f"{REST}/swell_profiles?id=eq.{b_id}", ANON, a_tok, {"surf_level": "esperto"}, "return=representation")
        check("A non può modificare il profilo di B", c == 200 and r == [], f"{c} {r}")
        c, r = request("GET", f"{REST}/swell_favorites?select=zone_id", ANON)
        check("senza login non si vedono preferiti", c in (200, 401, 403) and not (c == 200 and r), f"{c} {r}")

        # segnalazioni
        fb = {"kind": "bug", "message": marker, "app_state": {"settimana": 1}, "page": "test", "user_agent": "test_rls"}
        c, r = request("POST", f"{REST}/swell_feedback", ANON, body=fb)
        check("segnalazione anonima accettata", c == 201, f"{c} {r}")
        c, r = request("POST", f"{REST}/swell_feedback", ANON, a_tok, {**fb, "user_id": a_id})
        check("segnalazione di un utente col proprio id accettata", c == 201, f"{c} {r}")
        c, r = request("GET", f"{REST}/swell_feedback?select=id", ANON)
        check("con la chiave anon le segnalazioni non si leggono", c in (401, 403) or (c == 200 and r == []), f"{c} {r}")
        c, r = request("GET", f"{REST}/swell_feedback?select=id", ANON, a_tok)
        check("da utente le segnalazioni non si leggono", c in (401, 403) or (c == 200 and r == []), f"{c} {r}")
        c, r = request("POST", f"{REST}/swell_feedback", ANON, body={**fb, "user_id": b_id})
        check("non si segnala a nome di un altro utente", c in (401, 403), f"{c} {r}")
        c, r = request("POST", f"{REST}/swell_feedback", ANON, body={**fb, "status": "risolta"})
        check("non si inserisce una segnalazione già risolta", c in (401, 403), f"{c} {r}")
        c, r = request("PATCH", f"{REST}/swell_feedback?message=eq.{quote(marker)}", ANON, body={"status": "letta"}, prefer="return=representation")
        check("con la chiave anon non si cambia lo stato", c in (401, 403) or (c == 200 and r == []), f"{c} {r}")
        c, r = request("GET", f"{REST}/swell_feedback?message=eq.{quote(marker)}&select=id,user_id", SERVICE)
        check("con la chiave di servizio le segnalazioni di prova si leggono (2)", c == 200 and len(r) == 2, f"{c} {r}")
    finally:
        request("DELETE", f"{REST}/swell_feedback?message=eq.{quote(marker)}", SERVICE)
        for uid in (a_id, b_id):   # profili e preferiti se ne vanno in cascata
            request("DELETE", f"{AUTH}/admin/users/{uid}", SERVICE)
        print("utenti e righe di prova cancellati")
    print(f"\n{sum(results)}/{len(results)} controlli superati")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

"""Accesso minimo alle API REST di Supabase per gli script (solo libreria standard). Legge .env."""
import json, os, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def env():
    """Variabili da .env (fuori da git), con precedenza a quelle già nell'ambiente."""
    vals = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    vals.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE_")})
    # nomi nuovi di Supabase, con i vecchi ancora validi
    vals.setdefault("SUPABASE_PUBLISHABLE_KEY", vals.get("SUPABASE_ANON_KEY", ""))
    vals.setdefault("SUPABASE_SECRET_KEY", vals.get("SUPABASE_SERVICE_ROLE_KEY", ""))
    return vals


def request(method, url, key, token=None, body=None, prefer=None):
    """Ritorna (codice HTTP, JSON o testo). Non solleva su 4xx: i test devono vedere i rifiuti."""
    headers = {"apikey": key, "Content-Type": "application/json"}
    # le chiavi nuove (sb_publishable_..., sb_secret_...) vanno solo in apikey; in Authorization
    # va il token dell'utente, oppure la chiave se è del vecchio tipo JWT (anon / service_role)
    bearer = token or (key if key.startswith("eyJ") else None)
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw

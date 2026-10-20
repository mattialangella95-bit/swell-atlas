#!/bin/zsh
# Doppio clic dal Finder: avvia il sito in locale su http://localhost:8000 e lo apre nel browser.
# (Aprire index.html direttamente con file:// non funziona: il browser blocca i file JavaScript.)
# Per spegnere il server chiudi questa finestra del Terminale o premi Ctrl-C.
cd "$(dirname "$0")"
if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Il server è già acceso su http://localhost:8000"
  open "http://localhost:8000/"
else
  echo "Swell Atlas in locale su http://localhost:8000 (chiudi questa finestra per spegnerlo)"
  (sleep 1; open "http://localhost:8000/") &
  exec python3 -m http.server 8000 --bind 127.0.0.1
fi

#!/usr/bin/env bash
# Start the intake desk: API + web/ on 127.0.0.1:8788
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    export "$line"
  done < .env
fi

if [[ -z "${XAI_API_KEY:-}" ]]; then
  echo "XAI_API_KEY is missing. Put it in $ROOT/.env" >&2
  exit 1
fi

PY=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
if [[ -z "$PY" ]]; then
  echo "Python 3 not found on PATH." >&2
  exit 1
fi

export CLAIMDESK_ROOT="$ROOT"
HOST="${CLAIMDESK_HOST:-127.0.0.1}"
PORT="${CLAIMDESK_PORT:-8788}"
URL="http://${HOST}:${PORT}/clerk.html"

if command -v lsof >/dev/null 2>&1; then
  old="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN || true)"
  if [[ -n "$old" ]]; then
    kill $old 2>/dev/null || true
    sleep 0.3
  fi
fi

echo "Intake desk → $URL"
if command -v xdg-open >/dev/null 2>&1; then
  (sleep 1; xdg-open "$URL") >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  (sleep 1; open "$URL") >/dev/null 2>&1 &
elif command -v cmd.exe >/dev/null 2>&1; then
  (sleep 1; cmd.exe /c start "" "$URL") >/dev/null 2>&1 &
fi

exec "$PY" -m backend.serve

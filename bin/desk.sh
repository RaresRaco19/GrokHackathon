#!/usr/bin/env bash
# Start the local claim-intake desk.
# If something is already listening on the port, stop it first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8788}"
URL="http://127.0.0.1:${PORT}/"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to start the web desk." >&2
  exit 1
fi

listen_pids() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true
}

stop_existing() {
  local pids
  pids="$(listen_pids)"
  if [[ -z "${pids}" ]]; then
    return 0
  fi
  echo "Stopping existing process on port ${PORT}: $(echo "${pids}" | tr '\n' ' ')"
  # shellcheck disable=SC2086
  kill ${pids} 2>/dev/null || true
  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    pids="$(listen_pids)"
    if [[ -z "${pids}" ]]; then
      return 0
    fi
    sleep 0.2
  done
  echo "Forcing stop: $(echo "${pids}" | tr '\n' ' ')"
  # shellcheck disable=SC2086
  kill -9 ${pids} 2>/dev/null || true
  sleep 0.2
}

stop_existing

echo "Claim intake desk"
echo "  ${URL}"
echo "  CL-03 open · CL-04 refuse · CL-08 hold for photos"
echo "  Ctrl-C to stop"

(
  sleep 0.4
  if command -v open >/dev/null 2>&1; then
    open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL"
  fi
) >/dev/null 2>&1 &

exec python3 python/serve_desk.py --port "$PORT" --bind 127.0.0.1

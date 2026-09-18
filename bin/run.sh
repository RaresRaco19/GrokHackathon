#!/usr/bin/env bash
# Repeatable desk runner. All lab cases live here.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DECIDE=(python3 python/decide.py)
JSON=0
CASE="all"

usage() {
  cat <<'EOF'
Usage: bin/run.sh [case] [--json]

Cases:
  all        CL-03, CL-04, CL-08, then payout advice (default)
  CL-03      open / PX-GLASS
  CL-04      refuse / PX-FLOOD
  CL-08      hold / PX-COLLISION
  advice     refuse / PX-NO-PAY
  test       Golden tests (python3 -m unittest python.test_desk)
  mcp        lookup_rule for flood and a made-up rule

  --json     Machine-readable output (coverage and advice cases only)

Examples:
  bin/run.sh
  bin/run.sh CL-04
  bin/run.sh advice --json
  bin/run.sh test
  bin/run.sh mcp
EOF
}

run_decide() {
  if [[ "$JSON" -eq 1 ]]; then
    "${DECIDE[@]}" --json "$@"
  else
    "${DECIDE[@]}" "$@"
  fi
}

run_advice() {
  run_decide --advice "will we pay?"
}

run_mcp() {
  local out
  out=$(
    printf '%s\n' \
      '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
      '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"lookup_rule","arguments":{"query":"flood"}}}' \
      '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"lookup_rule","arguments":{"query":"made-up-rule"}}}' \
      | python3 python/rules_mcp.py
  )
  printf '%s\n' "$out"
  printf '%s\n' "$out" | python3 -c '
import json, sys
rows = [json.loads(line) for line in sys.stdin if line.strip()]
by_id = {row["id"]: row for row in rows if "id" in row}
hit = by_id[2]["result"]["content"][0]["text"]
first = hit.splitlines()[0] if hit else ""
if not first.startswith("PX-FLOOD"):
    raise SystemExit("mcp: expected a line starting PX-FLOOD, got %r" % first)
miss = by_id[3]["result"]["content"][0]["text"]
if "No rule line matched" not in miss or "made-up-rule" not in miss:
    raise SystemExit("mcp: expected made-up-rule miss, got %r" % miss)
'
}

run_all() {
  if [[ "$JSON" -eq 1 ]]; then
    "${DECIDE[@]}" --json
    "${DECIDE[@]}" --json --advice "will we pay?"
    return
  fi
  echo "=== CL-03  open / PX-GLASS ==="
  run_decide CL-03
  echo
  echo "=== CL-04  refuse / PX-FLOOD ==="
  run_decide CL-04
  echo
  echo "=== CL-08  hold / PX-COLLISION ==="
  run_decide CL-08
  echo
  echo "=== advice  refuse / PX-NO-PAY ==="
  run_advice
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --json) JSON=1 ;;
    all|CL-03|CL-04|CL-08|advice|test|mcp) CASE="$arg" ;;
    *)
      echo "Unknown case: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$CASE" in
  all) run_all ;;
  CL-03|CL-04|CL-08) run_decide "$CASE" ;;
  advice) run_advice ;;
  test)
    if [[ "$JSON" -eq 1 ]]; then
      echo "test does not support --json" >&2
      exit 1
    fi
    python3 -m unittest python.test_desk
    ;;
  mcp)
    if [[ "$JSON" -eq 1 ]]; then
      echo "mcp does not support --json" >&2
      exit 1
    fi
    run_mcp
    ;;
esac

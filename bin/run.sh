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

  --json     Machine-readable output (coverage and advice cases only)

Examples:
  bin/run.sh
  bin/run.sh CL-04
  bin/run.sh advice --json
  bin/run.sh test
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
    all|CL-03|CL-04|CL-08|advice|test) CASE="$arg" ;;
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
esac

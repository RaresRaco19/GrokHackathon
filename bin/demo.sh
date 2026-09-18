#!/usr/bin/env bash
# Laptop walkthrough: engine + tests + MCP. No website. No second engine.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mcp_lookup() {
  local query="$1"
  python3 -c 'import json,sys; print(json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"lookup_rule","arguments":{"query":sys.argv[1]}}}))' "$query" \
    | python3 python/rules_mcp.py \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["content"][0]["text"])'
}

echo "=== CL-03  open / PX-GLASS ==="
python3 python/decide.py CL-03

echo
echo "=== CL-04  refuse / PX-FLOOD ==="
cl04="$(python3 python/decide.py CL-04)"
printf '%s\n' "$cl04"
if ! printf '%s\n' "$cl04" | grep -q refuse; then
  echo "CL-04 must refuse" >&2
  exit 1
fi

echo
echo "=== advice  refuse / PX-NO-PAY ==="
python3 python/decide.py --advice "will we pay?"

echo
echo "=== unittest ==="
python3 -m unittest python.test_desk

echo
echo "=== MCP lookup flood (hit) ==="
hit="$(mcp_lookup flood)"
printf '%s\n' "$hit"
if ! printf '%s\n' "$hit" | grep -q PX-FLOOD; then
  echo "MCP flood hit must contain PX-FLOOD" >&2
  exit 1
fi

echo
echo "=== MCP lookup made-up-rule (miss) ==="
miss="$(mcp_lookup made-up-rule)"
printf '%s\n' "$miss"
if printf '%s\n' "$miss" | grep -q 'PX-'; then
  echo "MCP miss must not cite a rule" >&2
  exit 1
fi

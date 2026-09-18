#!/usr/bin/env python3
"""Local MCP stub: lookup_rule / list_rules against a markdown file in this folder."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Pin the kit rule book. Do not pick AGENTS.md / PLAN.md / README.md
# just because they are also markdown in the participant folder.
PREFERRED = (
    "payer_rules.md",
    "dispatch_rules.md",
    "rights_rules.md",
    "policy-excerpt.md",
)
SKIP = {"README.md", "AGENTS.md", "PLAN.md"}
RULE_FILE = next((ROOT / name for name in PREFERRED if (ROOT / name).exists()), None)
if RULE_FILE is None:
    RULE_FILE = next(
        (p for p in ROOT.iterdir() if p.suffix == ".md" and p.name not in SKIP),
        ROOT / "payer_rules.md",
    )


def rules_text() -> str:
    return RULE_FILE.read_text(encoding="utf-8") if RULE_FILE.exists() else ""


def handle(req: dict) -> dict:
    method = req.get("method")
    rid = req.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "rules", "version": "0.1"},
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "tools": [
                    {
                        "name": "list_rules",
                        "description": "List rule headings from the local rule file.",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "lookup_rule",
                        "description": "Return passages that mention a query string.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    },
                ]
            },
        }
    if method == "tools/call":
        name = (req.get("params") or {}).get("name")
        args = (req.get("params") or {}).get("arguments") or {}
        text = rules_text()
        if name == "list_rules":
            lines = [ln[2:].strip() for ln in text.splitlines() if ln.startswith("#")]
            body = "\n".join(lines) or text[:500]
        else:
            q = str(args.get("query", "")).lower()
            hits = [ln for ln in text.splitlines() if q and q in ln.lower()]
            # Do not dump the whole rule book on a miss — that lets a
            # later AGENTS.md/PLAN.md line or an unrelated rule look cited.
            body = "\n".join(hits) if hits else f"No rule line matched {q!r}."
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {"content": [{"type": "text", "text": body}]},
        }
    if method == "notifications/initialized":
        return {}
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": "Unknown method"},
    }


def main() -> None:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue
        out = handle(req)
        if out:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

"""Rerunnable CLI: all | CL-03 | CL-04 | CL-08 | advice | mcp | test."""
from __future__ import annotations

import sys
import unittest

from backend.agent import AgentError
from backend.assess import assess, load_reports
from backend.mcp_client import RulesMcp


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else "all"
    if cmd == "test":
        suite = unittest.defaultTestLoader.loadTestsFromNames(
            ["backend.test_assess", "backend.test_serve"]
        )
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    with RulesMcp() as client:
        if cmd == "mcp":
            hit = client.lookup_rule("flood")
            miss = client.lookup_rule("made-up-rule")
            sys.stdout.write(f"hit {hit}\nmiss {miss}\n")
            return 0 if hit.startswith("PX-FLOOD.") else 1
        try:
            if cmd == "advice":
                row = assess(question="will we pay?", client=client)
                sys.stdout.write(_format(row) + "\n")
                return 0
            if cmd == "all":
                for report_id in load_reports():
                    sys.stdout.write(_format(assess(report_id=report_id, client=client)) + "\n")
                return 0
            row = assess(report_id=cmd, client=client)
            sys.stdout.write(_format(row) + "\n")
            return 0
        except AgentError as exc:
            sys.stderr.write(f"{exc.message}\n")
            return 2


def _format(row: dict) -> str:
    return f"{row['id']} {row['decision']}\n{row['quote']}"


if __name__ == "__main__":
    raise SystemExit(main())

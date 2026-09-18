"""Load FNOL rows and run the Grok agent. Python does not decide coverage."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.agent import AgentError, LlmSession, run_agent
from backend.mcp_client import RulesMcp
from backend.paths import repo_root

REQUIRED = ("id", "peril", "photos", "cover")


def load_reports(root: Path | None = None) -> dict[str, dict[str, Any]]:
    path = (root or repo_root()) / "fnol.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("fnol.json entries must be objects")
        missing = [key for key in REQUIRED if key not in row]
        if missing:
            raise ValueError(f"report missing keys {missing}: {row!r}")
        out[str(row["id"]).upper()] = row
    return out


def assess(
    report_id: str | None = None,
    question: str | None = None,
    report: dict[str, Any] | None = None,
    client: RulesMcp | None = None,
    llm: LlmSession | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    own = client is None
    if own:
        client = RulesMcp(root=root)
        client.start()
    try:
        user_text = _user_text(report_id, question, report, root)
        return run_agent(user_text, client, llm=llm)
    finally:
        if own and client is not None:
            client.close()


def _user_text(
    report_id: str | None,
    question: str | None,
    report: dict[str, Any] | None,
    root: Path | None,
) -> str:
    parts: list[str] = []
    if report is None and report_id:
        reports = load_reports(root)
        report = reports.get(report_id.upper())
        if report is None:
            parts.append(f"Unknown report id {report_id}.")
    if report is not None:
        parts.append("Assess this damage report. Return JSON only.")
        parts.append(json.dumps(report, default=str))
    if question:
        parts.append("Client question:")
        parts.append(question.strip())
    if not parts:
        raise AgentError("id or question required")
    return "\n".join(parts)

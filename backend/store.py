"""Confirm / undo / JSONL log. No amount, payout, or $ keys."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.paths import var_dir

FORBIDDEN_KEY = re.compile(r"amount|payout|\$", re.I)


def state_path() -> Path:
    return var_dir() / "desk_state.json"


def log_path() -> Path:
    return var_dir() / "desk.jsonl"


def reset_session() -> None:
    """Drop cached assessments, claim numbers, and the log. Called on process start."""
    folder = var_dir()
    folder.mkdir(parents=True, exist_ok=True)
    for path in (state_path(), log_path()):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def ensure_state(ids: list[str]) -> dict[str, Any]:
    state = load_state()
    changed = False
    for report_id in ids:
        key = report_id.upper()
        if key not in state:
            state[key] = {
                "send_state": "draft",
                "claim_number": None,
                "refuse_logged": False,
                "decision": None,
            }
            changed = True
        else:
            row = state[key]
            row.setdefault("send_state", "draft")
            row.setdefault("claim_number", None)
            row.setdefault("refuse_logged", False)
            row.setdefault("decision", None)
    if changed:
        save_state(state)
    return state


def item_state(report_id: str) -> dict[str, Any]:
    state = ensure_state([report_id])
    return state[report_id.upper()]


def save_decision(report_id: str, decision: dict[str, Any]) -> None:
    state = ensure_state([report_id])
    row = state[report_id.upper()]
    row["decision"] = {
        "id": decision.get("id"),
        "decision": decision.get("decision"),
        "display": decision.get("display"),
        "rule_id": decision.get("rule_id"),
        "quote": decision.get("quote"),
        "mcp": decision.get("mcp"),
    }
    save_state(state)


def cached_decision(report_id: str) -> dict[str, Any] | None:
    row = item_state(report_id).get("decision")
    return row if isinstance(row, dict) else None


def log_event(event: str, **fields: Any) -> None:
    row = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "event": event}
    for key, value in fields.items():
        if FORBIDDEN_KEY.search(str(key)):
            continue
        row[key] = value
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def read_log() -> list[dict[str, Any]]:
    path = log_path()
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append({k: v for k, v in item.items() if not FORBIDDEN_KEY.search(str(k))})
    return rows


def log_refuse_once(report_id: str, decision: dict[str, Any]) -> None:
    state = ensure_state([report_id])
    row = state[report_id.upper()]
    if row.get("refuse_logged"):
        return
    log_event(
        "refuse",
        id=report_id,
        decision=decision.get("decision"),
        rule_id=decision.get("rule_id"),
    )
    row["refuse_logged"] = True
    save_state(state)


def confirm(report_id: str, decision: str) -> dict[str, Any]:
    if decision != "open":
        error = "refuse is not sent" if decision == "refuse" else f"{decision} is not sent"
        return {"ok": False, "error": error, "status": 400}
    state = ensure_state([report_id])
    row = state[report_id.upper()]
    if row.get("send_state") == "sent" and row.get("claim_number"):
        return {
            "ok": True,
            "id": report_id,
            "send_state": "sent",
            "claim_number": row["claim_number"],
        }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    claim_number = f"FNOL-{report_id}-{stamp}"
    row["send_state"] = "sent"
    row["claim_number"] = claim_number
    save_state(state)
    log_event("confirm", id=report_id, decision=decision, claim_number=claim_number)
    return {
        "ok": True,
        "id": report_id,
        "send_state": "sent",
        "claim_number": claim_number,
    }


def undo(report_id: str) -> dict[str, Any]:
    state = ensure_state([report_id])
    row = state[report_id.upper()]
    row["send_state"] = "draft"
    row["claim_number"] = None
    save_state(state)
    log_event("undo", id=report_id)
    return {
        "ok": True,
        "id": report_id,
        "send_state": "draft",
        "claim_number": None,
    }

#!/usr/bin/env python3
"""Initialize FNOL agent state, tracing, and permissions at start.

Grok has no AgentStart event. This hook runs on SessionStart (main agent)
and SubagentStart (child agents). Side effects only: SessionStart stdout is
ignored by Grok, so the briefing lives on disk under .grok/hooks/.state/.

Run `python3 agent_start.py --self-test`.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")

# Live-ops policy judges ask for: who clicks, how you undo, what goes in the log.
PERMISSIONS: dict[str, Any] = {
    "human_must_click_before": [
        "Writing an Accept / Refuse / Need photos decision (PreToolUse ask).",
        "Sending a claim outcome off-box (mail, curl, webhook) — not wired in this demo.",
    ],
    "deny": [
        "Edits or shell mutation of policy-excerpt.md, payer/dispatch/rights_rules.md, rules_mcp.py.",
        "Language that promises a payout or names a settlement amount (PX-NO-PAY).",
    ],
    "allow": [
        "Read-only rules MCP: rules__list_rules, rules__lookup_rule.",
        "Reading fnol.json and the rule book.",
    ],
    "undo": (
        "Reject the permission prompt to skip the write. "
        "File snapshots land in .grok/hooks/.state/<session>/undo/ before an approved overwrite."
    ),
    "log": ".grok/hooks/.state/audit.jsonl and .grok/hooks/.state/<session>/trace.jsonl",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_root(event: dict[str, Any] | None = None) -> Path:
    event = event or {}
    for key in ("workspaceRoot", "workspace_root"):
        value = event.get(key)
        if value:
            return Path(value)
    env = os.environ.get("GROK_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    cwd = event.get("cwd")
    if cwd:
        return Path(cwd)
    return Path.cwd()


def safe_id(value: str, fallback: str) -> str:
    cleaned = SAFE_ID.sub("_", value or "").strip("._")
    return cleaned or fallback


def state_dir(root: Path) -> Path:
    path = root / ".grok" / "hooks" / ".state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_dir(root: Path, session_id: str) -> Path:
    path = state_dir(root) / safe_id(session_id, "nosession")
    path.mkdir(parents=True, exist_ok=True)
    (path / "undo").mkdir(exist_ok=True)
    (path / "subagents").mkdir(exist_ok=True)
    return path


def event_name(event: dict[str, Any]) -> str:
    raw = (
        event.get("hook_event_name")
        or event.get("hookEventName")
        or os.environ.get("GROK_HOOK_EVENT")
        or ""
    )
    raw = str(raw).replace("-", "_")
    if raw and "_" not in raw and raw != raw.lower():
        raw = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    return raw.lower()


def session_id_of(event: dict[str, Any]) -> str:
    return str(
        event.get("sessionId")
        or event.get("session_id")
        or os.environ.get("GROK_SESSION_ID")
        or ""
    )


def permission_mode(event: dict[str, Any]) -> str:
    return str(event.get("permissionMode") or event.get("permission_mode") or "default")


def start_source(event: dict[str, Any]) -> str:
    return str(
        event.get("source")
        or event.get("startSource")
        or event.get("start_source")
        or "startup"
    )


def subagent_type(event: dict[str, Any]) -> str | None:
    value = event.get("subagentType") or event.get("subagent_type")
    return str(value) if value else None


def git_head(root: Path) -> str | None:
    head = root / ".git" / "HEAD"
    if not head.exists():
        return None
    try:
        text = head.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if text.startswith("ref:"):
        ref = root / ".git" / text.split(":", 1)[1].strip()
        try:
            return ref.read_text(encoding="utf-8").strip()[:40] or None
        except OSError:
            return text
    return text[:40]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def emit(payload: dict[str, Any] | None = None) -> int:
    if payload:
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()
    return 0


def briefing(state: dict[str, Any]) -> str:
    paths = state.get("paths") or {}
    return (
        "FNOL agent bootstrap complete.\n"
        f"- State: {paths.get('state')}\n"
        f"- Tracing: {paths.get('audit')} and {paths.get('trace')}\n"
        "- Permissions: a human must approve writing a claims decision; "
        "the rule book is read-only; never promise a payout (PX-NO-PAY). "
        "Reject the permission prompt to undo. "
        "Look up rules with rules__list_rules / rules__lookup_rule."
    )


def init_permissions(folder: Path, event: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "initialized_at": _now(),
        "sessionId": session_id_of(event),
        "permissionMode": permission_mode(event),
        "policy": PERMISSIONS,
    }
    write_json(folder / "permissions.json", payload)
    return payload


def init_state(folder: Path, event: dict[str, Any], *, kind: str) -> dict[str, Any]:
    existing = read_json(folder / "bootstrap.json")
    payload = {
        "initialized_at": existing.get("initialized_at") or _now(),
        "updated_at": _now(),
        "kind": kind,
        "sessionId": session_id_of(event),
        "source": start_source(event),
        "permissionMode": permission_mode(event),
        "subagentType": subagent_type(event),
        "cwd": event.get("cwd"),
        "workspaceRoot": str(workspace_root(event)),
        "gitHead": git_head(workspace_root(event)),
        "paths": {
            "state": str(folder / "bootstrap.json"),
            "trace": str(folder / "trace.jsonl"),
            "permissions": str(folder / "permissions.json"),
            "undo": str(folder / "undo"),
            "audit": str(state_dir(workspace_root(event)) / "audit.jsonl"),
        },
    }
    if existing.get("initialized_at") and start_source(event) == "resume":
        payload["resumed_at"] = _now()
        payload["initialized_at"] = existing["initialized_at"]
    write_json(folder / "bootstrap.json", payload)
    return payload


def init_tracing(
    folder: Path,
    event: dict[str, Any],
    *,
    kind: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "ts": _now(),
        "event": "agent_start",
        "phase": "initialize",
        "kind": kind,
        "sessionId": session_id_of(event),
        "source": start_source(event),
        "permissionMode": permission_mode(event),
        "subagentType": subagent_type(event),
        "gitHead": state.get("gitHead"),
    }
    append_jsonl(folder / "trace.jsonl", row)
    append_jsonl(state_dir(workspace_root(event)) / "audit.jsonl", row)
    return row


def handle_start(event: dict[str, Any], *, kind: str) -> int:
    root = workspace_root(event)
    session = session_id_of(event)
    folder = session_dir(root, session)
    if kind == "subagent":
        child = safe_id(
            str(event.get("agentId") or event.get("agent_id") or subagent_type(event) or "child"),
            "child",
        )
        folder = folder / "subagents" / child
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "undo").mkdir(exist_ok=True)

    state = init_state(folder, event, kind=kind)
    permissions = init_permissions(folder, event)
    init_tracing(folder, event, kind=kind, state=state)

    sys.stderr.write(
        "agent_start: "
        f"kind={kind} session={session or 'nosession'} "
        f"source={state.get('source')} permissionMode={permissions.get('permissionMode')}\n"
    )
    hook_event = "SessionStart" if kind == "session" else "SubagentStart"
    return emit(
        {
            "hookSpecificOutput": {
                "hookEventName": hook_event,
                "additionalContext": briefing(state),
            }
        }
    )


HANDLERS = {
    "session_start": lambda event: handle_start(event, kind="session"),
    "subagent_start": lambda event: handle_start(event, kind="subagent"),
    "agent_start": lambda event: handle_start(event, kind="session"),
}


def dispatch(event: dict[str, Any]) -> int:
    handler = HANDLERS.get(event_name(event))
    if handler is None:
        return emit()
    return handler(event)


def read_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"agent_start: invalid JSON on stdin: {exc}\n")
        return {}
    return data if isinstance(data, dict) else {}


class AgentStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["GROK_WORKSPACE_ROOT"] = str(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _event(self, name: str, **extra: Any) -> dict[str, Any]:
        payload = {
            "hook_event_name": name,
            "sessionId": "sess-1",
            "workspaceRoot": str(self.root),
            "cwd": str(self.root),
            "permissionMode": "default",
            "source": "startup",
        }
        payload.update(extra)
        return payload

    def test_session_start_writes_state_trace_permissions(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        buf = StringIO()
        with redirect_stdout(buf):
            code = handle_start(self._event("SessionStart"), kind="session")
        self.assertEqual(code, 0)
        folder = session_dir(self.root, "sess-1")
        bootstrap = read_json(folder / "bootstrap.json")
        permissions = read_json(folder / "permissions.json")
        trace = (folder / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
        audit = (state_dir(self.root) / "audit.jsonl").read_text(encoding="utf-8")
        self.assertEqual(bootstrap["kind"], "session")
        self.assertEqual(bootstrap["permissionMode"], "default")
        self.assertTrue((folder / "undo").is_dir())
        self.assertIn("human_must_click_before", permissions["policy"])
        self.assertEqual(len(trace), 1)
        self.assertIn("agent_start", audit)
        out = json.loads(buf.getvalue())
        self.assertIn(str(folder / "bootstrap.json"), out["hookSpecificOutput"]["additionalContext"])

    def test_resume_appends_trace_keeps_initialized_at(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        with redirect_stdout(StringIO()):
            first = handle_start(self._event("SessionStart"), kind="session")
            self.assertEqual(first, 0)
            folder = session_dir(self.root, "sess-1")
            original = read_json(folder / "bootstrap.json")["initialized_at"]
            handle_start(self._event("SessionStart", source="resume"), kind="session")
        bootstrap = read_json(folder / "bootstrap.json")
        lines = (folder / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(bootstrap["initialized_at"], original)
        self.assertIn("resumed_at", bootstrap)
        self.assertEqual(len(lines), 2)

    def test_subagent_start_does_not_clobber_session_bootstrap(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO

        with redirect_stdout(StringIO()):
            handle_start(self._event("SessionStart"), kind="session")
            handle_start(
                self._event("SubagentStart", subagentType="explore", agentId="child-9"),
                kind="subagent",
            )
        session_folder = session_dir(self.root, "sess-1")
        child = read_json(session_folder / "subagents" / "child-9" / "bootstrap.json")
        parent = read_json(session_folder / "bootstrap.json")
        self.assertEqual(parent["kind"], "session")
        self.assertEqual(child["kind"], "subagent")
        self.assertEqual(child["subagentType"], "explore")


def main(argv: list[str]) -> int:
    if argv and argv[0] in {"--self-test", "--test"}:
        result = unittest.main(argv=["agent_start.py"], exit=False, verbosity=2)
        return 0 if result.result.wasSuccessful() else 1
    event = read_event()
    try:
        return dispatch(event)
    except Exception as exc:  # noqa: BLE001 — hooks must fail open
        sys.stderr.write(f"agent_start: {type(exc).__name__}: {exc}\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

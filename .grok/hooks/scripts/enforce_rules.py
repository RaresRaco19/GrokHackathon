#!/usr/bin/env python3
"""Enforce FNOL decisions against the local rules MCP.

Grok calls this on session, prompt, tool, and stop events (stdin JSON).
Claims answers must look up rules via MCP, quote a real PX-* id, and
never promise a payout. Run `python3 enforce_rules.py --self-test`.
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

PREFERRED_RULES = (
    "payer_rules.md",
    "dispatch_rules.md",
    "rights_rules.md",
    "policy-excerpt.md",
)
SKIP_MD = {"README.md", "AGENTS.md", "PLAN.md"}
PROTECTED = {
    "policy-excerpt.md",
    "payer_rules.md",
    "dispatch_rules.md",
    "rights_rules.md",
    "rules_mcp.py",
}
RULE_ID_RE = re.compile(r"\bPX-[A-Z0-9-]+\b", re.I)
CLAIMS_RE = re.compile(
    r"\b(fnol|first notice of loss|claim(?:s|ant)?|peril|intake|"
    r"px-(?:glass|flood|collision|no-pay)|cl-0[0-9]+|"
    r"glass breakage|policy excerpt|need photos)\b",
    re.I,
)
DECISION_RE = re.compile(
    r"\b(accept(?:ed|ing)?(?: for intake)?|refuse(?:d|al)?|need photos)\b",
    re.I,
)
PAYOUT_PHRASE_RE = re.compile(
    r"\bwe(?:['’]ll| will) pay\b|\b(pay you|payout of|settlement (?:of|amount))\b",
    re.I,
)
MONEY_RE = re.compile(r"[$£€]\s*\d[\d,]*(?:\.\d+)?")
OFF_SCOPE_RE = re.compile(
    r"\b(weather forecast|recipe|stock tip|write a poem|tell a joke|"
    r"translate this|homework)\b",
    re.I,
)


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


def rule_file(root: Path) -> Path:
    for name in PREFERRED_RULES:
        path = root / name
        if path.exists():
            return path
    for path in sorted(root.glob("*.md")):
        if path.name not in SKIP_MD:
            return path
    return root / "policy-excerpt.md"


def rule_text(root: Path) -> str:
    path = rule_file(root)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def known_rule_ids(root: Path) -> set[str]:
    return {match.group(0).upper() for match in RULE_ID_RE.finditer(rule_text(root))}


def state_dir(root: Path) -> Path:
    path = root / ".grok" / "hooks" / ".state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_path(root: Path, session_id: str, prompt_id: str) -> Path:
    safe_session = re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "nosession")
    safe_prompt = re.sub(r"[^A-Za-z0-9._-]", "_", prompt_id or "noprompt")
    folder = state_dir(root) / safe_session
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{safe_prompt}.json"


def load_state(root: Path, session_id: str, prompt_id: str) -> dict[str, Any]:
    path = state_path(root, session_id, prompt_id)
    if not path.exists():
        return {
            "prompt": "",
            "rules_calls": [],
            "is_claims": False,
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"prompt": "", "rules_calls": [], "is_claims": False}


def save_state(root: Path, session_id: str, prompt_id: str, state: dict[str, Any]) -> None:
    path = state_path(root, session_id, prompt_id)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def audit(root: Path, row: dict[str, Any]) -> None:
    path = state_dir(root) / "audit.jsonl"
    row = {"ts": _now(), **row}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def emit(payload: dict[str, Any] | None = None) -> int:
    if payload:
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()
    return 0


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


def ids(event: dict[str, Any]) -> tuple[str, str]:
    session = str(event.get("sessionId") or event.get("session_id") or os.environ.get("GROK_SESSION_ID") or "")
    prompt = str(event.get("promptId") or event.get("prompt_id") or "")
    return session, prompt


def tool_name(event: dict[str, Any]) -> str:
    return str(event.get("toolName") or event.get("tool_name") or "")


def tool_input(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("toolInput") or event.get("tool_input") or {}
    return value if isinstance(value, dict) else {}


def text_blob(*parts: Any) -> str:
    chunks: list[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, (dict, list)):
            chunks.append(json.dumps(part))
        else:
            chunks.append(str(part))
    return "\n".join(chunks)


def is_claims_work(*parts: Any) -> bool:
    return bool(CLAIMS_RE.search(text_blob(*parts)))


def is_off_scope(text: str) -> bool:
    return bool(OFF_SCOPE_RE.search(text)) and not is_claims_work(text)


def cited_rule_ids(text: str) -> set[str]:
    return {match.group(0).upper() for match in RULE_ID_RE.finditer(text)}


def payout_promise(text: str) -> bool:
    lower = text.lower()
    if PAYOUT_PHRASE_RE.search(text):
        if re.search(
            r"(never write|do not (?:write|promise)|must not|px-no-pay).{0,60}we(?:['’]ll| will) pay",
            lower,
        ) or re.search(
            r"we(?:['’]ll| will) pay.{0,60}(never|do not|must not|forbidden|excluded)",
            lower,
        ):
            return False
        return True
    if MONEY_RE.search(text) and re.search(r"\b(pay|payout|settle|settlement|indemnif)", lower):
        return True
    return False


def invented_ids(text: str, root: Path) -> set[str]:
    return cited_rule_ids(text) - known_rule_ids(root)


def decision_kind(text: str) -> str | None:
    """First decision verb in the answer, so a quoted rule cannot override it."""
    for match in re.finditer(
        r"\bneed photos\b|\bhold(?: for photos)?\b|\brefuse(?:d|al)?\b|\baccept(?:ed|ing)?\b|\bopen\b",
        text,
        re.I,
    ):
        token = match.group(0).lower()
        if token.startswith("need") or token.startswith("hold"):
            return "need_photos"
        if token.startswith("refuse"):
            return "refuse"
        return "accept"
    return None


def mentioned_claim(text: str) -> str | None:
    match = re.search(r"\bCL-\d+\b", text, re.I)
    return match.group(0).upper() if match else None


def load_claims(root: Path) -> dict[str, Any]:
    path = root / "fnol.json"
    if not path.exists():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(row.get("id", "")).upper(): row for row in rows if isinstance(row, dict)}


def expected_decision(claim: dict[str, Any]) -> tuple[str, str]:
    peril = str(claim.get("peril", "")).lower()
    photos = bool(claim.get("photos"))
    cover = str(claim.get("cover", "")).upper()
    if peril == "flood":
        return "refuse", cover or "PX-FLOOD"
    if peril == "collision" and not photos:
        return "need_photos", cover or "PX-COLLISION"
    if peril == "glass":
        return "accept", cover or "PX-GLASS"
    if photos:
        return "accept", cover
    return "need_photos", cover


def mcp_tool_from_event(event: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    name = tool_name(event)
    payload = tool_input(event)
    if name in {"use_tool", "CallMcpTool"}:
        inner_name = str(payload.get("tool_name") or payload.get("toolName") or "")
        inner = payload.get("tool_input") or payload.get("toolInput") or payload.get("arguments") or {}
        if not isinstance(inner, dict):
            inner = {}
        return inner_name, inner
    return name, payload


def is_rules_mcp(name: str) -> bool:
    return name.startswith("rules__") or name in {"list_rules", "lookup_rule"}


def file_path_from_input(payload: dict[str, Any]) -> str:
    for key in ("file_path", "filePath", "path", "target_file"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def write_body(payload: dict[str, Any]) -> str:
    parts = [
        payload.get("content"),
        payload.get("new_string"),
        payload.get("newString"),
        payload.get("contents"),
    ]
    return text_blob(*parts)


def handle_session_start(event: dict[str, Any]) -> int:
    root = workspace_root(event)
    state_dir(root)
    audit(root, {"event": "session_start", "sessionId": ids(event)[0]})
    return emit()


def handle_user_prompt(event: dict[str, Any]) -> int:
    root = workspace_root(event)
    session_id, prompt_id = ids(event)
    prompt = str(event.get("prompt") or event.get("userPrompt") or event.get("text") or "")
    state = load_state(root, session_id, prompt_id)
    state["prompt"] = prompt
    state["is_claims"] = is_claims_work(prompt)
    state["is_off_scope"] = is_off_scope(prompt)
    save_state(root, session_id, prompt_id, state)
    audit(
        root,
        {
            "event": "user_prompt",
            "sessionId": session_id,
            "promptId": prompt_id,
            "is_claims": state["is_claims"],
            "is_off_scope": state["is_off_scope"],
        },
    )
    return emit()


def handle_post_tool(event: dict[str, Any]) -> int:
    root = workspace_root(event)
    session_id, prompt_id = ids(event)
    name, payload = mcp_tool_from_event(event)
    if not is_rules_mcp(name):
        return emit()
    state = load_state(root, session_id, prompt_id)
    state.setdefault("rules_calls", [])
    state["rules_calls"].append(
        {
            "tool": name,
            "query": payload.get("query"),
            "ts": _now(),
        }
    )
    save_state(root, session_id, prompt_id, state)
    audit(
        root,
        {
            "event": "rules_mcp",
            "sessionId": session_id,
            "promptId": prompt_id,
            "tool": name,
            "query": payload.get("query"),
        },
    )
    return emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    "Quote the returned PX-* rule text verbatim in the decision. "
                    "Do not invent rule IDs. Do not write “we will pay” or a settlement amount (PX-NO-PAY)."
                ),
            }
        }
    )


def handle_pre_tool(event: dict[str, Any]) -> int:
    root = workspace_root(event)
    payload = tool_input(event)
    path = file_path_from_input(payload)
    name = Path(path).name if path else ""
    body = write_body(payload)
    command = str(payload.get("command") or "")
    combined = text_blob(path, body, command)

    protected_hit = name in PROTECTED or Path(path).name in PROTECTED
    extra_rule_book = bool(name) and name.lower().endswith("rules.md")
    if command and re.search(r"\b(rm|mv|sed|truncate)\b", command):
        protected_hit = protected_hit or any(item in command for item in PROTECTED)
        extra_rule_book = extra_rule_book or bool(re.search(r"[^\s/\\]+rules\.md", command, re.I))
    if extra_rule_book:
        audit(root, {"event": "deny_extra_rules", "path": path, "tool": tool_name(event)})
        return emit(
            {
                "decision": "deny",
                "reason": (
                    "Extra rule books are blocked. The only rule source is "
                    "policy-excerpt.md via the rules MCP (rules__lookup_rule)."
                ),
            }
        )
    if protected_hit:
        label = name or "the rule book"
        audit(root, {"event": "deny_protected", "path": path, "tool": tool_name(event)})
        return emit(
            {
                "decision": "deny",
                "reason": (
                    f"{label} is read-only. Look up rules with the rules MCP "
                    "(rules__list_rules / rules__lookup_rule) instead of editing the rule book."
                ),
            }
        )

    if payout_promise(combined):
        audit(root, {"event": "deny_payout", "path": path, "tool": tool_name(event)})
        return emit(
            {
                "decision": "deny",
                "reason": (
                    "PX-NO-PAY: never write “we will pay” or name a settlement amount. "
                    "Call rules__lookup_rule with query PX-NO-PAY and quote that rule."
                ),
            }
        )

    if body and is_claims_work(body) and decision_kind(body):
        audit(root, {"event": "ask_decision_write", "path": path, "tool": tool_name(event)})
        return emit(
            {
                "decision": "ask",
                "reason": (
                    "Human approval required before writing a claims decision. "
                    "Confirm the quoted PX-* rule, then approve. Reject to undo."
                ),
            }
        )
    return emit({"decision": "allow"})


def stop_reason(event: dict[str, Any], root: Path) -> str | None:
    if str(event.get("reason") or "end_turn") != "end_turn":
        return None
    if event.get("subagentType") or event.get("subagent_type"):
        return None

    session_id, prompt_id = ids(event)
    state = load_state(root, session_id, prompt_id)
    answer = str(event.get("lastAssistantMessage") or event.get("last_assistant_message") or "")
    prompt = str(state.get("prompt") or "")
    blob = text_blob(prompt, answer)
    claims = is_claims_work(blob) or bool(state.get("is_claims"))
    off_scope = bool(state.get("is_off_scope")) or is_off_scope(prompt)
    kind = decision_kind(answer)
    calls = state.get("rules_calls") or []

    if off_scope and (kind or payout_promise(answer)):
        return (
            "This prompt is off-scope for FNOL intake. Turn it down. "
            "Do not Accept/Refuse a claim or invent a policy rule."
        )
    if not claims and not kind:
        return None

    if payout_promise(answer):
        return (
            "PX-NO-PAY forbids promising payment or naming a settlement amount. "
            "Remove that language and quote PX-NO-PAY from the rules MCP."
        )

    fake = invented_ids(answer, root)
    if fake:
        known = ", ".join(sorted(known_rule_ids(root))) or "(none found)"
        return (
            f"Made-up rules fail. {', '.join(sorted(fake))} is not in the rule book. "
            f"Call rules__lookup_rule and quote a real id ({known})."
        )

    if not calls:
        return (
            "You must consult the rules MCP before finishing a claims decision. "
            "1) search_tool query=\"rules\"  "
            "2) use_tool tool_name=\"rules__list_rules\" or rules__lookup_rule "
            "(query e.g. flood / glass / collision / PX-NO-PAY)  "
            "3) Quote the returned PX-* text verbatim. Invented rules fail."
        )

    if kind and not (cited_rule_ids(answer) & known_rule_ids(root)):
        return (
            "You looked up rules but did not quote a real PX-* id from the MCP result. "
            "Quote the returned rule text verbatim (for example PX-FLOOD. Flood is excluded. Return Refuse and quote this rule.)."
        )

    claims_by_id = load_claims(root)
    claim_id = mentioned_claim(blob)
    if claim_id and claim_id in claims_by_id and kind:
        expected, cover = expected_decision(claims_by_id[claim_id])
        if kind != expected:
            label = {"accept": "Accept", "refuse": "Refuse", "need_photos": "Need photos"}[expected]
            return (
                f"{claim_id} must return {label} and quote {cover}. "
                "Call rules__lookup_rule for that cover and quote the passage; do not invent a different outcome."
            )
        if cover and cover not in cited_rule_ids(answer):
            return f"Quote {cover} from the rules MCP for {claim_id}."

    lower = answer.lower()
    if re.search(r"\bflood\b", lower) and kind == "accept":
        return "PX-FLOOD: Flood is excluded. Return Refuse and quote this rule."
    if re.search(r"\bcollision\b", lower) and re.search(r"\b(no |without |missing )photo", lower) and kind == "accept":
        return "PX-COLLISION: Collision needs photos. If photos are missing, return Need photos."
    return None


def handle_stop(event: dict[str, Any]) -> int:
    root = workspace_root(event)
    reason = stop_reason(event, root)
    session_id, prompt_id = ids(event)
    if not reason:
        audit(root, {"event": "stop_allow", "sessionId": session_id, "promptId": prompt_id})
        return emit()
    audit(root, {"event": "stop_block", "sessionId": session_id, "promptId": prompt_id, "reason": reason})
    return emit({"decision": "block", "reason": reason})


HANDLERS = {
    "session_start": handle_session_start,
    "user_prompt_submit": handle_user_prompt,
    "post_tool_use": handle_post_tool,
    "pre_tool_use": handle_pre_tool,
    "stop": handle_stop,
}


def dispatch(event: dict[str, Any]) -> int:
    name = event_name(event)
    handler = HANDLERS.get(name)
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
        sys.stderr.write(f"enforce_rules: invalid JSON on stdin: {exc}\n")
        return {}
    return data if isinstance(data, dict) else {}


class EnforceRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "policy-excerpt.md").write_text(
            "# Policy excerpt\n\n"
            "PX-GLASS. Glass breakage is in force when photos are on the file. Accept for intake. Do not promise a payout.\n\n"
            "PX-FLOOD. Flood is excluded. Return Refuse and quote this rule.\n\n"
            "PX-COLLISION. Collision needs photos. If photos are missing, return Need photos.\n\n"
            "PX-NO-PAY. Never write “we will pay” or name a settlement amount.\n",
            encoding="utf-8",
        )
        (self.root / "fnol.json").write_text(
            json.dumps(
                [
                    {"id": "CL-03", "peril": "glass", "photos": True, "cover": "PX-GLASS"},
                    {"id": "CL-04", "peril": "flood", "photos": True, "cover": "PX-FLOOD"},
                    {"id": "CL-08", "peril": "collision", "photos": False, "cover": "PX-COLLISION"},
                ]
            ),
            encoding="utf-8",
        )
        os.environ["GROK_WORKSPACE_ROOT"] = str(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _stop(self, prompt: str, answer: str, calls: list[dict[str, Any]] | None = None) -> str | None:
        save_state(
            self.root,
            "s",
            "p",
            {"prompt": prompt, "rules_calls": calls or [], "is_claims": is_claims_work(prompt)},
        )
        return stop_reason(
            {
                "reason": "end_turn",
                "sessionId": "s",
                "promptId": "p",
                "lastAssistantMessage": answer,
                "workspaceRoot": str(self.root),
            },
            self.root,
        )

    def test_blocks_stop_without_mcp(self) -> None:
        reason = self._stop("Intake CL-03 glass with photos", "Accept for intake.")
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("rules MCP", reason)

    def test_allows_glass_pass_when_quoted(self) -> None:
        reason = self._stop(
            "Intake CL-03 glass with photos",
            "Accept for intake. PX-GLASS. Glass breakage is in force when photos are on the file. Accept for intake. Do not promise a payout.",
            calls=[{"tool": "rules__lookup_rule", "query": "glass"}],
        )
        self.assertIsNone(reason)

    def test_allows_glass_open_alias(self) -> None:
        reason = self._stop(
            "Intake CL-03 glass with photos",
            "open. PX-GLASS. Glass breakage is in force when photos are on the file. Accept for intake. Do not promise a payout.",
            calls=[{"tool": "rules__lookup_rule", "query": "PX-GLASS"}],
        )
        self.assertIsNone(reason)

    def test_blocks_flood_accept(self) -> None:
        reason = self._stop(
            "Intake CL-04 flood",
            "Accept. PX-FLOOD. Flood is excluded. Return Refuse and quote this rule.",
            calls=[{"tool": "rules__lookup_rule", "query": "flood"}],
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("Refuse", reason)

    def test_blocks_payout_promise(self) -> None:
        reason = self._stop(
            "Intake CL-03",
            "Accept. PX-GLASS. We will pay $500.",
            calls=[{"tool": "rules__lookup_rule", "query": "glass"}],
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("PX-NO-PAY", reason)

    def test_blocks_invented_rule(self) -> None:
        reason = self._stop(
            "Intake CL-03",
            "Accept. PX-MAGIC. Everything is covered.",
            calls=[{"tool": "rules__list_rules"}],
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("Made-up", reason)

    def test_denies_editing_rule_book(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            code = handle_pre_tool(
                {
                    "hook_event_name": "PreToolUse",
                    "workspaceRoot": str(self.root),
                    "toolName": "write",
                    "toolInput": {"file_path": str(self.root / "policy-excerpt.md"), "content": "nope"},
                }
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue())["decision"], "deny")

    def test_records_mcp_call(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        with redirect_stdout(StringIO()):
            handle_post_tool(
                {
                    "hook_event_name": "PostToolUse",
                    "workspaceRoot": str(self.root),
                    "sessionId": "s",
                    "promptId": "p",
                    "toolName": "rules__lookup_rule",
                    "toolInput": {"query": "flood"},
                }
            )
        state = load_state(self.root, "s", "p")
        self.assertEqual(state["rules_calls"][0]["tool"], "rules__lookup_rule")

    def test_allows_flood_refuse_when_quoted(self) -> None:
        reason = self._stop(
            "Intake CL-04 flood",
            "Refuse. PX-FLOOD. Flood is excluded. Return Refuse and quote this rule.",
            calls=[{"tool": "rules__lookup_rule", "query": "flood"}],
        )
        self.assertIsNone(reason)

    def test_blocks_collision_accept_without_photos(self) -> None:
        reason = self._stop(
            "Intake CL-08 collision, photos missing",
            "Accept. PX-COLLISION. Collision needs photos. If photos are missing, return Need photos.",
            calls=[{"tool": "rules__lookup_rule", "query": "collision"}],
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("Need photos", reason)

    def test_allows_collision_hold_alias(self) -> None:
        reason = self._stop(
            "Intake CL-08 collision, photos missing",
            "hold. PX-COLLISION. Collision needs photos. If photos are missing, return Need photos.",
            calls=[{"tool": "rules__lookup_rule", "query": "PX-COLLISION"}],
        )
        self.assertIsNone(reason)

    def test_denies_extra_rule_book(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            code = handle_pre_tool(
                {
                    "hook_event_name": "PreToolUse",
                    "workspaceRoot": str(self.root),
                    "toolName": "write",
                    "toolInput": {"file_path": str(self.root / "extra_rules.md"), "content": "PX-FAKE. no"},
                }
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue())["decision"], "deny")


def main(argv: list[str]) -> int:
    if argv and argv[0] in {"--self-test", "--test"}:
        result = unittest.main(argv=["enforce_rules.py"], exit=False, verbosity=2)
        return 0 if result.result.wasSuccessful() else 1
    event = read_event()
    try:
        return dispatch(event)
    except Exception as exc:  # noqa: BLE001 — hooks must fail open, never crash the turn
        sys.stderr.write(f"enforce_rules: {type(exc).__name__}: {exc}\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

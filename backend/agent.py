"""Grok assesses inquiries. Local MCP runs only when the model calls a tool."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from pathlib import Path

from backend.mcp_client import RulesMcp
from backend.paths import repo_root

MODEL = "grok-4.6"
MAX_TURNS = 6
DECISIONS = {"open", "hold", "refuse"}
RULE_ID_RE = re.compile(r"\b(PX-[A-Z0-9-]+)\b", re.I)
MONEY_RE = re.compile(r"[$£€]\s*\d")
WE_WILL_PAY_RE = re.compile(r"\bwe(?:['’]ll| will) pay\b", re.I)

LOOKUP_PARAMS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Cover id (PX-GLASS, PX-FLOOD, PX-COLLISION, PX-NO-PAY) or peril (glass, flood, collision).",
        }
    },
    "required": ["query"],
}


class AgentError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LlmTurn:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LlmSession(Protocol):
    def start(self, system_prompt: str, user_text: str) -> None: ...
    def complete(self, tool_choice: str) -> LlmTurn: ...
    def remember_turn(self) -> None: ...
    def add_tool_result(self, call: ToolCall, output: str) -> None: ...
    def add_user(self, text: str) -> None: ...


def load_dotenv() -> None:
    path = repo_root() / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def system_prompt() -> str:
    path = Path(__file__).resolve().parent / "system_prompt.md"
    return path.read_text(encoding="utf-8").strip()


def run_agent(
    user_text: str,
    mcp: RulesMcp,
    llm: LlmSession | None = None,
) -> dict[str, Any]:
    session: LlmSession = llm or XaiSession()
    session.start(system_prompt(), user_text)
    calls: list[dict[str, Any]] = []
    last_error = "no decision"
    for turn in range(MAX_TURNS):
        choice = "required" if not calls else "auto"
        try:
            result = session.complete(tool_choice=choice)
        except AgentError as exc:
            raise AgentError(last_error if last_error != "no decision" else exc.message) from exc
        if result.tool_calls:
            session.remember_turn()
            for call in result.tool_calls:
                output = _execute_tool(mcp, call)
                calls.append(
                    {
                        "tool": call.name,
                        "query": call.arguments.get("query"),
                        "text": output,
                    }
                )
                session.add_tool_result(call, output)
            continue
        try:
            payload = parse_decision(result.text)
        except AgentError as exc:
            last_error = exc.message
            session.add_user(f"Validator rejected: {exc.message}. Call lookup_rule if you have not, then return JSON only.")
            continue
        error = validate(payload, calls)
        if error:
            last_error = error
            session.add_user(f"Validator rejected: {error}. Call lookup_rule if needed, quote MCP verbatim, return JSON only.")
            continue
        return finalize(payload, calls)
    raise AgentError(last_error)


def _execute_tool(mcp: RulesMcp, call: ToolCall) -> str:
    if call.name in {"lookup_rule", "rules__lookup_rule"}:
        query = str(call.arguments.get("query") or "")
        return mcp.lookup_rule(query)
    if call.name in {"list_rules", "rules__list_rules"}:
        return mcp.list_rules()
    return f"Unknown tool {call.name!r}."


def parse_decision(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise AgentError("empty model output")
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    blob = match.group(1) if match else raw
    if not blob.startswith("{"):
        start, end = blob.find("{"), blob.rfind("}")
        if start == -1 or end == -1:
            raise AgentError("model output was not JSON")
        blob = blob[start : end + 1]
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise AgentError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AgentError("JSON root must be an object")
    return data


def validate(payload: dict[str, Any], calls: list[dict[str, Any]]) -> str | None:
    lookups = [row for row in calls if row.get("tool") in {"lookup_rule", "rules__lookup_rule"}]
    if not lookups:
        return "You must call lookup_rule before deciding."
    decision = payload.get("decision")
    if decision not in DECISIONS:
        return "decision must be open, hold, or refuse."
    quote = str(payload.get("quote") or "").strip()
    if not quote:
        return "quote is required."
    sources = [str(row.get("text") or "") for row in lookups]
    if not any(quote in source or source in quote for source in sources):
        return "quote must be a verbatim MCP lookup_rule result."
    rule_id = payload.get("rule_id")
    if rule_id not in (None, "null"):
        rid = str(rule_id).upper()
        known = {m.group(1).upper() for source in sources for m in RULE_ID_RE.finditer(source)}
        if rid not in known:
            return f"{rid} is not in the MCP result. Do not invent rule ids."
    blob = json.dumps({k: v for k, v in payload.items() if k != "quote"})
    if MONEY_RE.search(blob) or WE_WILL_PAY_RE.search(blob):
        return "PX-NO-PAY: do not name a payout or settlement amount."
    return None


def finalize(payload: dict[str, Any], calls: list[dict[str, Any]]) -> dict[str, Any]:
    lookups = [row for row in calls if row.get("tool") in {"lookup_rule", "rules__lookup_rule"}]
    quote = str(payload.get("quote") or "").strip()
    used = next((row for row in reversed(lookups) if quote in str(row.get("text") or "") or str(row.get("text") or "") in quote), lookups[-1])
    rule_id = payload.get("rule_id")
    if rule_id in (None, "null", ""):
        rule_id = None
    else:
        rule_id = str(rule_id).upper()
    decision = str(payload["decision"])
    return {
        "id": str(payload.get("id") or "question"),
        "decision": decision,
        "display": "hold for photos" if decision == "hold" else decision,
        "rule_id": rule_id,
        "quote": quote,
        "mcp": {"tool": "lookup_rule", "query": used.get("query")},
        "send_state": "draft",
    }


class ScriptedLlm:
    """Test double: scripted turns, real MCP still executes in run_agent."""

    def __init__(self, script: list[LlmTurn | Callable[[list[dict[str, Any]]], LlmTurn]]) -> None:
        self.script = list(script)
        self.index = 0
        self.outputs: list[dict[str, Any]] = []

    def start(self, system_prompt: str, user_text: str) -> None:
        self.system_prompt = system_prompt
        self.user_text = user_text

    def complete(self, tool_choice: str) -> LlmTurn:
        if self.index >= len(self.script):
            raise AgentError("scripted LLM exhausted")
        step = self.script[self.index]
        self.index += 1
        if callable(step):
            return step(self.outputs)
        return step

    def remember_turn(self) -> None:
        return

    def add_tool_result(self, call: ToolCall, output: str) -> None:
        self.outputs.append({"tool": call.name, "query": call.arguments.get("query"), "text": output})

    def add_user(self, text: str) -> None:
        return


class XaiSession:
    """Live Grok via SpaceXAI. Tool calls run in-process against rules_mcp.py."""

    def __init__(self) -> None:
        self._chat = None
        self._last = None

    def start(self, system_prompt: str, user_text: str) -> None:
        load_dotenv()
        key = os.environ.get("XAI_API_KEY")
        if not key:
            raise AgentError("XAI_API_KEY is missing. Set it in the environment or a gitignored .env")
        from xai_sdk import Client
        from xai_sdk.chat import system, tool, user

        tools = [
            tool(
                name="lookup_rule",
                description="Return passages from the policy excerpt that mention a query. Call this before every intake decision.",
                parameters=LOOKUP_PARAMS,
            ),
            tool(
                name="list_rules",
                description="List rule headings from the local policy excerpt.",
                parameters={"type": "object", "properties": {}},
            ),
        ]
        client = Client(api_key=key)
        self._chat = client.chat.create(
            model=MODEL,
            tools=tools,
            tool_choice="required",
            temperature=0,
            reasoning_effort="low",
        )
        self._chat.append(system(system_prompt))
        self._chat.append(user(user_text))

    def complete(self, tool_choice: str) -> LlmTurn:
        self._set_tool_choice(tool_choice)
        self._last = self._chat.sample()
        calls = []
        for tc in self._last.tool_calls:
            raw_args = tc.function.arguments
            if isinstance(raw_args, str) and raw_args:
                args = json.loads(raw_args)
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}
            calls.append(ToolCall(id=str(tc.id), name=tc.function.name, arguments=args))
        return LlmTurn(text=self._last.content or "", tool_calls=calls)

    def remember_turn(self) -> None:
        if self._last is not None:
            self._chat.append(self._last)

    def add_tool_result(self, call: ToolCall, output: str) -> None:
        from xai_sdk.chat import tool_result

        self._chat.append(tool_result(output, tool_call_id=call.id or None))

    def add_user(self, text: str) -> None:
        from xai_sdk.chat import user

        self._set_tool_choice("auto")
        self._chat.append(user(text))

    def _set_tool_choice(self, mode: str) -> None:
        from xai_sdk.proto import chat_pb2

        mapping = {
            "auto": chat_pb2.ToolMode.TOOL_MODE_AUTO,
            "none": chat_pb2.ToolMode.TOOL_MODE_NONE,
            "required": chat_pb2.ToolMode.TOOL_MODE_REQUIRED,
        }
        self._chat._proto.tool_choice.CopyFrom(chat_pb2.ToolChoice(mode=mapping[mode]))

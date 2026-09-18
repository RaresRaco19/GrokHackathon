"""JSON API for the colleague frontend. No HTML. Bind 127.0.0.1:8788."""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from backend.agent import AgentError, LlmSession
from backend.assess import assess, load_reports
from backend.mcp_client import RulesMcp
from backend.store import (
    cached_decision,
    confirm,
    ensure_state,
    item_state,
    log_event,
    log_refuse_once,
    read_log,
    save_decision,
    undo,
)

HOST = "127.0.0.1"
PORT = 8788


class DeskApp:
    def __init__(self, llm: LlmSession | None = None) -> None:
        self.client = RulesMcp()
        self.client.start()
        self.llm = llm

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict[str, Any]:
        listing = self.client.list_rules()
        return {"ok": True, "mcp": "ok", "rules": listing}

    def queue(self) -> list[dict[str, Any]]:
        reports = load_reports()
        ensure_state(list(reports))
        items = []
        for report_id, report in reports.items():
            saved = item_state(report_id)
            decision = saved.get("decision") if isinstance(saved.get("decision"), dict) else None
            if decision:
                items.append(_merge(report, decision, saved))
            else:
                item = dict(report)
                item.update(
                    {
                        "decision": None,
                        "needs_assess": True,
                        "send_state": saved.get("send_state") or "draft",
                        "claim_number": saved.get("claim_number"),
                        "can_confirm": False,
                        "can_undo": saved.get("send_state") == "sent",
                    }
                )
                items.append(item)
        return items

    def _assess(self, report_id: str | None, question: str | None) -> dict[str, Any]:
        return assess(
            report_id=report_id,
            question=question,
            client=self.client,
            llm=self.llm,
        )

    def assess_request(self, body: dict[str, Any]) -> dict[str, Any]:
        report_id = body.get("id")
        question = body.get("question")
        if not report_id and not question:
            return {"error": "id or question required", "status": 400}
        try:
            decision = self._assess(
                str(report_id) if report_id else None,
                str(question) if question else None,
            )
        except AgentError as exc:
            return {"error": exc.message, "status": 502}
        if report_id:
            save_decision(str(report_id), decision)
        if decision["decision"] == "refuse":
            log_refuse_once(str(decision["id"]), decision)
        else:
            log_event(
                "assess",
                id=decision["id"],
                decision=decision["decision"],
                rule_id=decision["rule_id"],
            )
        if report_id:
            return _merge(
                load_reports().get(str(report_id).upper(), {}),
                decision,
                item_state(str(report_id)),
            )
        return decision

    def confirm_request(self, body: dict[str, Any]) -> dict[str, Any]:
        report_id = str(body.get("id") or "")
        if not report_id:
            return {"error": "id required", "status": 400}
        decision = cached_decision(report_id)
        if decision is None:
            try:
                decision = self._assess(report_id, None)
            except AgentError as exc:
                return {"error": exc.message, "status": 502}
            save_decision(report_id, decision)
        result = confirm(report_id, str(decision.get("decision")))
        if not result.get("ok"):
            return result
        report = load_reports().get(report_id.upper(), {})
        return _merge(report, decision, item_state(report_id))

    def undo_request(self, body: dict[str, Any]) -> dict[str, Any]:
        report_id = str(body.get("id") or "")
        if not report_id:
            return {"error": "id required", "status": 400}
        undo(report_id)
        decision = cached_decision(report_id) or {}
        report = load_reports().get(report_id.upper(), {})
        return _merge(report, decision, item_state(report_id))


def _merge(report: dict[str, Any], decision: dict[str, Any], saved: dict[str, Any]) -> dict[str, Any]:
    item = dict(report)
    item.update(decision)
    send_state = saved.get("send_state") or "draft"
    item["send_state"] = send_state
    item["claim_number"] = saved.get("claim_number")
    item["can_confirm"] = item.get("decision") == "open" and send_state == "draft"
    item["can_undo"] = send_state == "sent"
    return item


def make_handler(app: DeskApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send(204, b"", content_type=None)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/health":
                self._json(200, app.health())
                return
            if path == "/api/queue":
                self._json(200, {"items": app.queue()})
                return
            if path == "/api/log":
                self._json(200, {"events": read_log()})
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            body = self._body()
            if body is None:
                self._json(400, {"error": "invalid json"})
                return
            if path == "/api/assess":
                result = app.assess_request(body)
            elif path == "/api/confirm":
                result = app.confirm_request(body)
            elif path == "/api/undo":
                result = app.undo_request(body)
            else:
                self._json(404, {"error": "not found"})
                return
            status = int(result.pop("status", 200)) if isinstance(result, dict) else 200
            if isinstance(result, dict) and "error" in result and status == 200:
                status = 400
            self._json(status, result)

        def _body(self) -> dict[str, Any] | None:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            if not raw:
                return {}
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return None
            return data if isinstance(data, dict) else None

        def _json(self, status: int, payload: Any) -> None:
            blob = json.dumps(payload).encode("utf-8")
            self._send(status, blob, content_type="application/json")

        def _send(self, status: int, body: bytes, content_type: str | None) -> None:
            self.send_response(status)
            if content_type:
                self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            if status != 204:
                self.wfile.write(body)

    return Handler


def make_server(host: str = HOST, port: int = PORT, app: DeskApp | None = None) -> tuple[ThreadingHTTPServer, DeskApp]:
    owned = app or DeskApp()
    server = ThreadingHTTPServer((host, port), make_handler(owned))
    return server, owned


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    host = os.environ.get("CLAIMDESK_HOST", HOST)
    port = int(args[0] if args else os.environ.get("CLAIMDESK_PORT", PORT))
    server, app = make_server(host, port)
    bound = server.server_address[1]
    sys.stdout.write(f"claim desk API on http://{host}:{bound}\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

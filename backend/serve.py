"""JSON API + static web/ for the intake desk. Bind 127.0.0.1:8788."""
from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from backend.agent import AgentError, LlmSession
from backend.assess import assess, load_reports
from backend.mcp_client import RulesMcp
from backend.paths import repo_root
from backend.vision import check_photo
from backend.store import (
    cached_decision,
    confirm,
    ensure_state,
    item_state,
    log_event,
    log_refuse_once,
    read_log,
    reset_session,
    save_decision,
    save_upload,
    stored_file,
    undo,
    attach_file_check,
)

PHOTO = {
    "glass": (
        "assets/glass.jpg",
        "Spiderweb crack across a car windshield, viewed from the passenger seat.",
    ),
    "flood": (
        "assets/flood.jpg",
        "Silver sedan in knee-deep floodwater on a residential street.",
    ),
    "collision": (
        "assets/collision.jpg",
        "Silver hatchback with a crumpled rear bumper in an empty parking lot.",
    ),
}
LOG_EVENT = {
    "refuse": "refuse_logged",
    "confirm": "confirmed",
    "undo": "undone",
    "upload": "upload",
    "photo_check": "photo_check",
}
POLICY_IDS = ("PX-GLASS", "PX-FLOOD", "PX-COLLISION", "PX-NO-PAY")

HOST = "127.0.0.1"
PORT = 8788


class DeskApp:
    def __init__(
        self,
        llm: LlmSession | None = None,
        *,
        keep_state: bool = False,
        vision: Any | None = None,
    ) -> None:
        if not keep_state:
            reset_session()
        self.client = RulesMcp()
        self.client.start()
        self.llm = llm
        self.vision = vision
        self._policy: list[dict[str, str]] | None = None

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict[str, Any]:
        listing = self.client.list_rules()
        return {"ok": True, "mcp": "ok", "rules": listing}

    def policy(self) -> list[dict[str, str]]:
        if self._policy is None:
            rows = []
            for rule_id in POLICY_IDS:
                rows.append({"id": rule_id, "text": self.client.lookup_rule(rule_id)})
            self._policy = rows
        return self._policy

    def public_log(self) -> list[dict[str, Any]]:
        out = []
        for row in read_log():
            event = str(row.get("event") or "")
            out.append(
                {
                    "ts": row.get("ts"),
                    "id": row.get("id"),
                    "event": LOG_EVENT.get(event, event),
                    "detail": row.get("rule_id") or row.get("claim_number") or row.get("decision") or "",
                }
            )
        return out

    def queue(self) -> list[dict[str, Any]]:
        reports = load_reports()
        ensure_state(list(reports))
        items = []
        for report_id, report in reports.items():
            saved = item_state(report_id)
            decision = saved.get("decision") if isinstance(saved.get("decision"), dict) else None
            if decision:
                item = _merge(report, decision, saved)
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
            items.append(_decorate(item, saved))
        return items

    def queue_payload(self) -> dict[str, Any]:
        rows = self.queue()
        return {
            "items": rows,
            "reports": rows,
            "policy": self.policy(),
            "log": self.public_log(),
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def _report_for_assess(self, report_id: str | None) -> dict[str, Any] | None:
        if not report_id:
            return None
        reports = load_reports()
        report = reports.get(str(report_id).upper())
        if report is None:
            return None
        row = dict(report)
        if item_state(str(report_id)).get("photos_on_file"):
            row["photos"] = True
        return row

    def _assess(self, report_id: str | None, question: str | None) -> dict[str, Any]:
        return assess(
            report_id=report_id,
            question=question,
            report=self._report_for_assess(report_id),
            client=self.client,
            llm=self.llm,
        )

    def upload_request(self, content_type: str, raw: bytes) -> dict[str, Any]:
        fields, files = parse_multipart(content_type, raw)
        report_id = str(fields.get("id") or "")
        if not report_id:
            return {"error": "id required", "status": 400}
        if report_id.upper() not in load_reports():
            return {"error": "unknown report", "status": 400}
        if not files:
            return {"error": "file required", "status": 400}
        _field, filename, content, mime = files[0]
        result = save_upload(report_id, filename, content, mime)
        if not result.get("ok"):
            return result
        record = result["file"]
        if record.get("kind") == "image":
            report = load_reports().get(report_id.upper(), {})
            check = check_photo(
                content,
                record.get("mime") or mime,
                str(report.get("peril") or ""),
                checker=self.vision,
            )
            updated = attach_file_check(report_id, record["stored"], check)
            if updated:
                result["file"] = updated
                record = updated
            log_event(
                "photo_check",
                id=report_id.upper(),
                detail=("MATCH" if check.get("match") is True else "NO MATCH" if check.get("match") is False else "UNCHECKED"),
            )
        saved = item_state(report_id)
        decision = saved.get("decision") if isinstance(saved.get("decision"), dict) else None
        report = load_reports().get(report_id.upper(), {})
        if decision:
            item = _decorate(_merge(report, decision, saved), saved)
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
            item = _decorate(item, saved)
        item["ok"] = True
        item["file"] = result["file"]
        return item

    def file_bytes(self, report_id: str, stored: str) -> tuple[int, bytes, str] | None:
        path = stored_file(report_id, stored)
        if path is None:
            return None
        mime, _ = mimetypes.guess_type(str(path))
        return 200, path.read_bytes(), mime or "application/octet-stream"

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
            saved = item_state(str(report_id))
            return _decorate(
                _merge(
                    load_reports().get(str(report_id).upper(), {}),
                    decision,
                    saved,
                ),
                saved,
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
        saved = item_state(report_id)
        return _decorate(_merge(report, decision, saved), saved)

    def undo_request(self, body: dict[str, Any]) -> dict[str, Any]:
        report_id = str(body.get("id") or "")
        if not report_id:
            return {"error": "id required", "status": 400}
        undo(report_id)
        decision = cached_decision(report_id) or {}
        report = load_reports().get(report_id.upper(), {})
        saved = item_state(report_id)
        return _decorate(_merge(report, decision, saved), saved)


def _merge(report: dict[str, Any], decision: dict[str, Any], saved: dict[str, Any]) -> dict[str, Any]:
    item = dict(report)
    item.update(decision)
    send_state = saved.get("send_state") or "draft"
    item["send_state"] = send_state
    item["claim_number"] = saved.get("claim_number")
    item["can_confirm"] = item.get("decision") == "open" and send_state == "draft"
    item["can_undo"] = send_state == "sent"
    item["needs_assess"] = False
    return item


def parse_multipart(content_type: str, body: bytes) -> tuple[dict[str, str], list[tuple[str, str, bytes, str]]]:
    match = re.search(r"boundary=([^;]+)", content_type or "", re.I)
    if not match:
        return {}, []
    boundary = match.group(1).strip().strip('"').encode("utf-8")
    fields: dict[str, str] = {}
    files: list[tuple[str, str, bytes, str]] = []
    for part in body.split(b"--" + boundary):
        if not part or part.strip() in (b"", b"--"):
            continue
        part = part.lstrip(b"\r\n")
        if b"\r\n\r\n" not in part:
            continue
        head, payload = part.split(b"\r\n\r\n", 1)
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        header = head.decode("utf-8", "replace")
        name_m = re.search(r'name="([^"]+)"', header)
        if not name_m:
            continue
        name = name_m.group(1)
        file_m = re.search(r'filename="([^"]*)"', header)
        type_m = re.search(r"Content-Type:\s*([^\r\n]+)", header, re.I)
        if file_m:
            mime = type_m.group(1).strip() if type_m else "application/octet-stream"
            files.append((name, file_m.group(1), payload, mime))
        else:
            fields[name] = payload.decode("utf-8", "replace")
    return fields, files


def _decorate(item: dict[str, Any], saved: dict[str, Any]) -> dict[str, Any]:
    peril = str(item.get("peril") or "").lower()
    photo, alt = PHOTO.get(peril, ("assets/tray.jpg", "Intake file"))
    item.setdefault("photo", photo)
    item.setdefault("photo_alt", alt)
    item["files"] = list(saved.get("files") or [])
    if saved.get("photos_on_file"):
        item["photos"] = True
    item["received_at"] = saved.get("received_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    send = item.get("send_state")
    if send == "sent":
        item["ui_send_state"] = "numbered"
    elif item.get("decision") == "refuse" and saved.get("refuse_logged"):
        item["ui_send_state"] = "logged"
    else:
        item["ui_send_state"] = "draft"
    return item


def web_root() -> Path:
    return repo_root() / "web"


def static_file(url_path: str) -> tuple[int, bytes, str] | None:
    rel = unquote(url_path.split("?", 1)[0]).lstrip("/")
    if not rel or rel.endswith("/"):
        rel = (rel + "index.html") if rel else "index.html"
    root = web_root().resolve()
    full = (root / rel).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        return None
    if not full.is_file():
        return None
    mime, _ = mimetypes.guess_type(str(full))
    if full.suffix == ".js":
        mime = "text/javascript; charset=utf-8"
    elif full.suffix == ".css":
        mime = "text/css; charset=utf-8"
    elif full.suffix == ".html":
        mime = "text/html; charset=utf-8"
    elif not mime:
        mime = "application/octet-stream"
    return 200, full.read_bytes(), mime


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
                self._json(200, app.queue_payload())
                return
            if path == "/api/log":
                self._json(200, {"events": app.public_log(), "log": app.public_log()})
                return
            if path.startswith("/api/files/"):
                parts = [p for p in path.split("/") if p]
                if len(parts) >= 4:
                    blob = app.file_bytes(parts[2], parts[3])
                    if blob:
                        status, body, mime = blob
                        self._send(status, body, mime)
                        return
                self._json(404, {"error": "not found"})
                return
            static = static_file(path)
            if static:
                status, body, mime = static
                self._send(status, body, mime)
                return
            if path.startswith("/api/"):
                self._json(404, {"error": "not found"})
                return
            self._send(404, b"not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if path == "/api/upload":
                result = app.upload_request(self.headers.get("Content-Type") or "", raw)
            else:
                body = self._json_body(raw)
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

        def _json_body(self, raw: bytes) -> dict[str, Any] | None:
            if not raw:
                return {}
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return None
            return data if isinstance(data, dict) else None

        def _json(self, status: int, payload: Any) -> None:
            blob = json.dumps(payload).encode("utf-8")
            extra = {"Cache-Control": "no-store"}
            self._send(status, blob, content_type="application/json", extra_headers=extra)

        def _send(
            self,
            status: int,
            body: bytes,
            content_type: str | None,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            self.send_response(status)
            if content_type:
                self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            if extra_headers:
                for key, value in extra_headers.items():
                    self.send_header(key, value)
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
    sys.stdout.write(f"claim desk on http://{host}:{bound}/clerk.html\n")
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

#!/usr/bin/env python3
"""Local FNOL desk: HTML in web/, decisions from decide.py + policy-excerpt.md.

GET /api/queue is read-only. Refuse is logged in ensure_state(), not on GET.
Claim numbers use utccompact YYYYMMDDTHHMMSSZ and are minted on open confirm only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WEB = ROOT / "web"
DISPLAY_FILE = HERE / "display.json"

sys.path.insert(0, str(HERE))
import decide  # noqa: E402

_LOCK = threading.Lock()

FORBIDDEN_LOG_KEYS = ("amount", "payout", "$")


def var_dir() -> Path:
    override = os.environ.get("CLAIMDESK_VAR")
    return Path(override) if override else ROOT / "var"


def state_path() -> Path:
    return var_dir() / "desk_state.json"


def log_path() -> Path:
    return var_dir() / "intake-log.jsonl"


def utccompact(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def load_display() -> dict:
    if not DISPLAY_FILE.exists():
        return {}
    return json.loads(DISPLAY_FILE.read_text(encoding="utf-8"))


def _read_state_unlocked() -> dict:
    path = state_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state_unlocked(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _entry(state: dict, report_id: str) -> dict:
    raw = state.get(report_id) or {}
    return {
        "send_state": raw.get("send_state") or "draft",
        "claim_number": raw.get("claim_number"),
        "refuse_logged": bool(raw.get("refuse_logged")),
    }


def _append_log_unlocked(event: dict) -> None:
    for key in event:
        lowered = key.lower()
        if lowered in FORBIDDEN_LOG_KEYS or "$" in key:
            raise ValueError(f"log key not allowed: {key}")
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _find_report(report_id: str) -> dict | None:
    return next((row for row in decide.load_reports() if row["id"] == report_id), None)


def _item(report: dict, result: dict, entry: dict, chrome: dict | None = None) -> dict:
    decision = result["decision"]
    send_state = entry["send_state"]
    item = {
        "id": report["id"],
        "peril": report["peril"],
        "photos": report["photos"],
        "cover": report["cover"],
        "decision": decision,
        "label": "hold for photos" if decision == "hold" else decision,
        "rule_id": result["rule_id"],
        "quoted": result["quoted"],
        "source": result["source"],
        "send_state": send_state,
        "claim_number": entry.get("claim_number"),
        "can_confirm": decision in ("open", "hold") and send_state == "draft",
        "can_undo": send_state in ("sent", "held"),
    }
    for key, value in (chrome or {}).items():
        if value not in (None, ""):
            item[key] = value
    return item


def load_log() -> list[dict]:
    path = log_path()
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text:
            events.append(json.loads(text))
    return events


def ensure_state() -> dict:
    """Materialize var/desk_state.json and log each refuse once. Not used by GET."""
    with _LOCK:
        var_dir().mkdir(parents=True, exist_ok=True)
        state = _read_state_unlocked()
        policy = decide.load_policy()
        for report in decide.load_reports():
            report_id = report["id"]
            entry = _entry(state, report_id)
            result = decide.decide_report(report, policy)
            if result["decision"] == "refuse" and not entry["refuse_logged"]:
                _append_log_unlocked(
                    {
                        "ts": utccompact(),
                        "id": report_id,
                        "decision": "refuse",
                        "quoted": result["quoted"],
                        "event": "refuse",
                    }
                )
                entry["refuse_logged"] = True
            state[report_id] = entry
        _write_state_unlocked(state)
        return state


def queue_payload() -> list[dict]:
    policy = decide.load_policy()
    display = load_display()
    with _LOCK:
        state = _read_state_unlocked()
    out: list[dict] = []
    for report in decide.load_reports():
        result = decide.decide_report(report, policy)
        entry = _entry(state, report["id"])
        out.append(_item(report, result, entry, display.get(report["id"])))
    return out


def ask_payload(question: str) -> dict:
    policy = decide.load_policy()
    result = decide.refuse_off_scope(question or "", policy)
    if result.get("rule_id") == "PX-NO-PAY":
        label = "refuse"
        detail = result.get("message") or result["quoted"]
        decision = "refuse"
    elif result.get("message") == decide.MEDICAL_LEGAL_REFUSAL:
        label = "refuse"
        detail = result["message"]
        decision = "refuse"
    else:
        label = "Off-desk"
        detail = (
            "This desk only decides claim intake. It does not answer that question."
        )
        decision = "Off-desk"
    return {
        "label": label,
        "decision": decision,
        "rule_id": result["rule_id"],
        "quoted": result["quoted"],
        "detail": detail,
        "source": result["source"],
    }


def confirm(report_id: str) -> tuple[int, dict]:
    report_id = (report_id or "").strip()
    if not report_id:
        return 400, {"error": "missing id"}
    ensure_state()
    with _LOCK:
        report = _find_report(report_id)
        if report is None:
            return 400, {"error": "unknown report"}
        policy = decide.load_policy()
        result = decide.decide_report(report, policy)
        if result["decision"] == "refuse":
            return 400, {"error": "refuse is not sent"}
        state = _read_state_unlocked()
        entry = _entry(state, report_id)
        if entry["send_state"] != "draft":
            return 400, {"error": "already confirmed"}
        if result["decision"] == "open":
            entry["send_state"] = "sent"
            entry["claim_number"] = f"FNOL-{report_id}-{utccompact()}"
        elif result["decision"] == "hold":
            entry["send_state"] = "held"
            entry["claim_number"] = None
        else:
            return 400, {"error": "cannot confirm"}
        state[report_id] = entry
        event = {
            "ts": utccompact(),
            "id": report_id,
            "decision": result["decision"],
            "quoted": result["quoted"],
            "event": "confirm",
        }
        if entry.get("claim_number"):
            event["claim_number"] = entry["claim_number"]
        _append_log_unlocked(event)
        _write_state_unlocked(state)
        chrome = load_display().get(report_id)
        return 200, _item(report, result, entry, chrome)


def undo(report_id: str) -> tuple[int, dict]:
    report_id = (report_id or "").strip()
    if not report_id:
        return 400, {"error": "missing id"}
    ensure_state()
    with _LOCK:
        report = _find_report(report_id)
        if report is None:
            return 400, {"error": "unknown report"}
        state = _read_state_unlocked()
        entry = _entry(state, report_id)
        if entry["send_state"] not in ("sent", "held"):
            return 400, {"error": "nothing to undo"}
        previous = entry.get("claim_number")
        entry["send_state"] = "draft"
        entry["claim_number"] = None
        state[report_id] = entry
        policy = decide.load_policy()
        result = decide.decide_report(report, policy)
        event = {
            "ts": utccompact(),
            "id": report_id,
            "decision": result["decision"],
            "quoted": result["quoted"],
            "event": "undo",
        }
        if previous:
            event["claim_number"] = previous
        _append_log_unlocked(event)
        _write_state_unlocked(state)
        chrome = load_display().get(report_id)
        return 200, _item(report, result, entry, chrome)


def health_payload() -> dict:
    return {
        "ok": True,
        "policy": str(decide.POLICY_FILE),
        "reports": str(decide.REPORTS_FILE),
        "engine": "python/decide.py",
    }


class DeskHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> tuple[int, dict] | tuple[int, None]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return 400, None
        if not isinstance(data, dict):
            return 400, None
        return 200, data

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/queue":
            self._json(200, queue_payload())
            return
        if path == "/api/log":
            self._json(200, load_log())
            return
        if path == "/api/health":
            self._json(200, health_payload())
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        status, data = self._read_json()
        if data is None:
            self._json(400, {"error": "invalid JSON"})
            return
        if path == "/api/ask":
            question = str(data.get("question") or "")
            self._json(200, ask_payload(question))
            return
        if path == "/api/confirm":
            code, payload = confirm(str(data.get("id") or ""))
            self._json(code, payload)
            return
        if path == "/api/undo":
            code, payload = undo(str(data.get("id") or ""))
            self._json(code, payload)
            return
        self.send_error(404)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local claim-intake desk.")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args(argv)
    ensure_state()
    server = ThreadingHTTPServer((args.bind, args.port), DeskHandler)
    print("Claim intake desk")
    print(f"  http://{args.bind}:{args.port}/")
    print(f"  engine   {decide.ROOT / 'python' / 'decide.py'}")
    print(f"  policy   {decide.POLICY_FILE}")
    print(f"  reports  {decide.REPORTS_FILE}")
    print("  Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

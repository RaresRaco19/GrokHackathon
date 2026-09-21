#!/usr/bin/env python3
"""Local FNOL desk: HTML in web/, decisions from decide.py + policy-excerpt.md.

GET /api/queue is read-only. Refuse is logged in ensure_state(), not on GET.
Claim numbers use utccompact YYYYMMDDTHHMMSSZ and are minted on open confirm only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WEB = ROOT / "web"
DISPLAY_FILE = HERE / "display.json"

sys.path.insert(0, str(HERE))
import decide  # noqa: E402
import photo_match  # noqa: E402

_LOCK = threading.Lock()

FORBIDDEN_LOG_KEYS = ("amount", "payout", "$")
PHOTO_MAX = 5 * 1024 * 1024
PHOTO_TYPES = {
    b"\xff\xd8\xff": (".jpg", "image/jpeg"),
    b"\x89PNG\r\n\x1a\n": (".png", "image/png"),
    b"GIF87a": (".gif", "image/gif"),
    b"GIF89a": (".gif", "image/gif"),
}


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


def photos_dir() -> Path:
    return var_dir() / "photos"


def _entry(state: dict, report_id: str) -> dict:
    raw = state.get(report_id) or {}
    entry = {
        "send_state": raw.get("send_state") or "draft",
        "claim_number": raw.get("claim_number"),
        "refuse_logged": bool(raw.get("refuse_logged")),
    }
    if "photos" in raw:
        entry["photos"] = bool(raw["photos"])
    if raw.get("photo_name"):
        entry["photo_name"] = raw["photo_name"]
    return entry


def _effective_report(report: dict, entry: dict) -> dict:
    out = dict(report)
    if "photos" in entry:
        out["photos"] = bool(entry["photos"])
    return out


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


def _recompute(report: dict, entry: dict) -> tuple[dict, dict]:
    """Decide from kit + remaining photo overlay. Always the live claim state."""
    effective = _effective_report(report, entry)
    result = decide.decide_report(effective, decide.load_policy())
    return effective, result


def _item(report: dict, result: dict, entry: dict, chrome: dict | None = None) -> dict:
    decision = result["decision"]
    send_state = entry["send_state"]
    photos = bool(report["photos"])
    item = {
        "id": report["id"],
        "peril": report["peril"],
        "photos": photos,
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
        "can_upload": True,
        "can_delete": bool(entry.get("photo_name")),
    }
    if entry.get("photo_name"):
        item["photo_url"] = f"/api/photo/{report['id']}"
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
            result = decide.decide_report(_effective_report(report, entry), policy)
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
        entry = _entry(state, report["id"])
        effective = _effective_report(report, entry)
        result = decide.decide_report(effective, policy)
        out.append(_item(effective, result, entry, display.get(report["id"])))
    return out


def ask_payload(question: str) -> dict:
    policy = decide.load_policy()
    result = decide.ask_against_rules(question or "", policy)
    if result.get("rule_id") == "PX-NO-PAY":
        label = "refuse"
        detail = result.get("message") or result["quoted"]
    elif result.get("message") == decide.MEDICAL_LEGAL_REFUSAL:
        label = "refuse"
        detail = result["message"]
    elif result.get("rule_id"):
        label = "hold for photos" if result["decision"] == "hold" else result["decision"]
        detail = result["quoted"]
    else:
        label = "no match"
        detail = result["quoted"]
    return {
        "label": label,
        "decision": result["decision"],
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
        state = _read_state_unlocked()
        entry = _entry(state, report_id)
        report = _effective_report(report, entry)
        result = decide.decide_report(report, policy)
        if result["decision"] == "refuse":
            return 400, {"error": "refuse is not sent"}
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
        report = _effective_report(report, entry)
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


def _sniff_photo(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return ".webp", "image/webp"
    for magic, meta in PHOTO_TYPES.items():
        if data.startswith(magic):
            return meta
    return None


def attach_photos(report_id: str, filename: str, data: bytes) -> tuple[int, dict]:
    report_id = (report_id or "").strip()
    if not report_id:
        return 400, {"error": "missing id"}
    if not data:
        return 400, {"error": "empty file"}
    if len(data) > PHOTO_MAX:
        return 400, {"error": "file too large"}
    sniffed = _sniff_photo(data)
    if sniffed is None:
        return 400, {"error": "not an image"}
    ext, ctype = sniffed
    report = _find_report(report_id)
    if report is None:
        return 400, {"error": "unknown report"}
    label = photo_match.classify_photo(data, ctype)
    if not photo_match.matches_report(label, report.get("peril", "")):
        return 400, {"error": photo_match.CONTEXT_ERROR}
    ensure_state()
    with _LOCK:
        report = _find_report(report_id)
        if report is None:
            return 400, {"error": "unknown report"}
        folder = photos_dir() / report_id
        folder.mkdir(parents=True, exist_ok=True)
        stored = f"photo{ext}"
        (folder / stored).write_bytes(data)
        state = _read_state_unlocked()
        entry = _entry(state, report_id)
        entry["photos"] = True
        entry["photo_name"] = stored
        # New evidence: clerk must confirm the new open, not a prior hold.
        entry["send_state"] = "draft"
        entry["claim_number"] = None
        report, result = _recompute(report, entry)
        state[report_id] = entry
        _append_log_unlocked(
            {
                "ts": utccompact(),
                "id": report_id,
                "decision": result["decision"],
                "quoted": result["quoted"],
                "event": "photos",
            }
        )
        _write_state_unlocked(state)
        chrome = load_display().get(report_id)
        return 200, _item(report, result, entry, chrome)


def delete_photos(report_id: str) -> tuple[int, dict]:
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
        name = entry.get("photo_name")
        if not name:
            return 400, {"error": "no uploaded photo"}
        folder = photos_dir() / report_id
        path = folder / name
        if path.is_file():
            path.unlink()
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
        entry.pop("photo_name", None)
        entry.pop("photos", None)
        entry["send_state"] = "draft"
        entry["claim_number"] = None
        report, result = _recompute(report, entry)
        state[report_id] = entry
        _append_log_unlocked(
            {
                "ts": utccompact(),
                "id": report_id,
                "decision": result["decision"],
                "quoted": result["quoted"],
                "event": "photos-removed",
            }
        )
        _write_state_unlocked(state)
        chrome = load_display().get(report_id)
        return 200, _item(report, result, entry, chrome)


def photo_bytes(report_id: str) -> tuple[bytes, str] | None:
    with _LOCK:
        entry = _entry(_read_state_unlocked(), report_id)
    name = entry.get("photo_name")
    if not name:
        return None
    path = photos_dir() / report_id / name
    if not path.is_file():
        return None
    data = path.read_bytes()
    sniffed = _sniff_photo(data)
    ctype = sniffed[1] if sniffed else "application/octet-stream"
    return data, ctype


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
        photo_match = re.fullmatch(r"/api/photo/([^/]+)", path)
        if photo_match:
            found = photo_bytes(unquote(photo_match.group(1)))
            if found is None:
                self.send_error(404)
                return
            body, ctype = found
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def _read_multipart_photo(self) -> tuple[str, str, bytes] | tuple[None, None, None]:
        ctype = self.headers.get("Content-Type") or ""
        match = re.search(r"boundary=([^;]+)", ctype)
        if not match:
            return None, None, None
        boundary = match.group(1).strip().strip('"').encode()
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        report_id = ""
        filename = "photo"
        data = b""
        for part in body.split(b"--" + boundary):
            if not part or part in (b"--", b"--\r\n") or part.startswith(b"--"):
                continue
            head, sep, payload = part.partition(b"\r\n\r\n")
            if not sep:
                continue
            payload = payload.rstrip(b"\r\n")
            header = head.decode("utf-8", "replace")
            name_m = re.search(r'name="([^"]+)"', header)
            if not name_m:
                continue
            field = name_m.group(1)
            if field == "id":
                report_id = payload.decode("utf-8", "replace").strip()
            elif field in ("photo", "file"):
                file_m = re.search(r'filename="([^"]*)"', header)
                filename = file_m.group(1) if file_m else "photo"
                data = payload
        if not report_id or not data:
            return None, None, None
        return report_id, filename, data

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/photos":
            report_id, filename, data = self._read_multipart_photo()
            if not report_id:
                self._json(400, {"error": "missing photo"})
                return
            code, payload = attach_photos(report_id, filename, data)
            self._json(code, payload)
            return
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
        if path == "/api/photos/delete":
            code, payload = delete_photos(str(data.get("id") or ""))
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

"""Confirm / undo / JSONL log. No amount, payout, or $ keys."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.paths import var_dir

FORBIDDEN_KEY = re.compile(r"amount|payout|\$", re.I)
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"}
ALLOWED_EXT = IMAGE_EXT | {".pdf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def state_path() -> Path:
    return var_dir() / "desk_state.json"


def log_path() -> Path:
    return var_dir() / "desk.jsonl"


def uploads_root() -> Path:
    path = var_dir() / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_session() -> None:
    """Drop cached assessments, claim numbers, uploads, and the log. Called on process start."""
    folder = var_dir()
    folder.mkdir(parents=True, exist_ok=True)
    for path in (state_path(), log_path()):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    uploads = folder / "uploads"
    if uploads.is_dir():
        shutil.rmtree(uploads, ignore_errors=True)


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
                "files": [],
                "photos_on_file": False,
            }
            changed = True
        else:
            row = state[key]
            row.setdefault("send_state", "draft")
            row.setdefault("claim_number", None)
            row.setdefault("refuse_logged", False)
            row.setdefault("decision", None)
            row.setdefault("files", [])
            row.setdefault("photos_on_file", False)
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


def _safe_filename(name: str) -> str:
    base = Path(name or "file").name
    cleaned = SAFE_NAME.sub("_", base).strip("._")[:80]
    return cleaned or "file"


def save_upload(report_id: str, filename: str, content: bytes, mime: str) -> dict[str, Any]:
    key = report_id.upper()
    if not re.fullmatch(r"CL-\d+", key):
        return {"ok": False, "error": "unknown report", "status": 400}
    if not content:
        return {"ok": False, "error": "empty file", "status": 400}
    if len(content) > MAX_UPLOAD_BYTES:
        return {"ok": False, "error": "file too large", "status": 400}
    original = _safe_filename(filename)
    ext = Path(original).suffix.lower()
    mime = (mime or "").split(";")[0].strip().lower()
    if ext not in ALLOWED_EXT and not mime.startswith("image/") and mime != "application/pdf":
        return {"ok": False, "error": "file type not allowed", "status": 400}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stored = f"{stamp}-{original}"
    folder = uploads_root() / key
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / stored
    dest.write_bytes(content)
    is_image = ext in IMAGE_EXT or mime.startswith("image/")
    record = {
        "name": original,
        "stored": stored,
        "mime": mime or "application/octet-stream",
        "size": len(content),
        "url": f"/api/files/{key}/{stored}",
        "kind": "image" if is_image else "file",
    }
    state = ensure_state([key])
    row = state[key]
    files = list(row.get("files") or [])
    files.append(record)
    row["files"] = files
    if is_image:
        row["photos_on_file"] = True
    save_state(state)
    log_event("upload", id=key, detail=original)
    return {"ok": True, "id": key, "file": record, "files": files, "photos_on_file": bool(row.get("photos_on_file"))}


def stored_file(report_id: str, stored: str) -> Path | None:
    key = report_id.upper()
    name = Path(stored).name
    if name != stored or ".." in stored:
        return None
    path = (uploads_root() / key / name).resolve()
    root = (uploads_root() / key).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.is_file() else None


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

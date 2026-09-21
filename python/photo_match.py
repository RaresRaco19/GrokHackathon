"""Classify an FNOL photo as glass, flood, collision, or other.

Uses SpaceXAI vision (XAI_API_KEY, repo .env, or Grok login token).
Tests can pin a label with CLAIMDESK_PHOTO_LABEL.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

LABELS = ("glass", "flood", "collision")
CONTEXT_ERROR = "do not match context!"

_PROMPT = (
    "This is a first-notice-of-loss photo. "
    "Classify the damage. Reply with exactly one word and nothing else: "
    "glass, flood, collision, or other.\n"
    "glass = broken window, shattered glass, cracked windshield or pane.\n"
    "flood = standing water, flooding, water damage to a building or vehicle.\n"
    "collision = vehicle crash, dent, impact, accident, smashed bumper.\n"
    "other = people, pets, landscapes, screenshots, blank images, or anything else."
)


def classify_photo(data: bytes, mime: str = "image/png") -> str:
    pinned = os.environ.get("CLAIMDESK_PHOTO_LABEL", "").strip().lower()
    if pinned:
        return pinned if pinned in LABELS or pinned == "other" else "other"
    key = _api_key()
    if not key:
        print("photo_match: no XAI_API_KEY or Grok login; treating as other", file=sys.stderr)
        return "other"
    try:
        label = _classify_with_grok(data, mime, key)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        print(f"photo_match: HTTP {exc.code} {detail}", file=sys.stderr)
        return "other"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"photo_match: {exc}", file=sys.stderr)
        return "other"
    print(f"photo_match: classified as {label}", file=sys.stderr)
    return label


def matches_report(label: str, peril: str) -> bool:
    want = (peril or "").strip().lower()
    got = (label or "").strip().lower()
    return got in LABELS and got == want


def _api_key() -> str:
    for name in ("XAI_API_KEY", "GROK_API_KEY"):
        val = os.environ.get(name, "").strip()
        if val:
            return val
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, val = line.partition("=")
            if name.strip() in ("XAI_API_KEY", "GROK_API_KEY"):
                val = val.strip().strip('"').strip("'")
                if val:
                    return val
    auth = Path.home() / ".grok" / "auth.json"
    if auth.is_file():
        try:
            blob = json.loads(auth.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            blob = {}
        for rec in blob.values() if isinstance(blob, dict) else []:
            if not isinstance(rec, dict):
                continue
            token = str(rec.get("key") or rec.get("access_token") or "").strip()
            if token:
                return token
    return ""


def _label_from_text(text: str) -> str:
    t = (text or "").lower()
    if not t.strip():
        return "other"
    tokens = re.findall(r"[a-z]+", t)
    if tokens and tokens[0] in LABELS:
        return tokens[0]
    for label in LABELS:
        if re.search(rf"\b{re.escape(label)}s?\b", t) or label in t:
            return label
    return "other"


def _response_text(payload: dict) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"])
    if payload.get("choices"):
        msg = payload["choices"][0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                str(part.get("text") or "") for part in content if isinstance(part, dict)
            )
    chunks: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("text"):
                chunks.append(str(part["text"]))
    return " ".join(chunks)


def _post_json(url: str, body: dict, key: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _classify_with_grok(data: bytes, mime: str, key: str) -> str:
    if mime not in ("image/jpeg", "image/png"):
        mime = "image/png" if mime.endswith("png") else "image/jpeg"
    data_url = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    models = ("grok-4-fast", "grok-4.6", "grok-2-vision-1212")
    last_error = None
    for model in models:
        chat_body = {
            "model": model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        }
        try:
            payload = _post_json("https://api.x.ai/v1/chat/completions", chat_body, key)
            return _label_from_text(_response_text(payload))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (400, 404, 422):
                continue
            raise
    if last_error is not None:
        raise last_error
    return "other"

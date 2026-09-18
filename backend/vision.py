"""Quick Grok chat check: does this upload show the photo the report needs?"""
from __future__ import annotations

import base64
import os
from typing import Any, Callable

from backend.agent import AgentError, load_dotenv

MODEL = "grok-4.6"
NEEDED = {
    "glass": "a photo of broken or cracked vehicle glass, such as a windshield",
    "flood": "a photo of a vehicle in floodwater or inundated by water",
    "collision": "a photo of vehicle collision damage, such as a crumpled bumper or body panel",
}
VISION_MIME = {"image/jpeg": "jpeg", "image/jpg": "jpeg", "image/png": "png"}


def needed_photo(peril: str) -> str:
    return NEEDED.get((peril or "").lower(), "a photo of the reported vehicle damage")


def check_photo(
    content: bytes,
    mime: str,
    peril: str,
    checker: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    needed = needed_photo(peril)
    if checker is not None:
        return checker(content=content, mime=mime, peril=peril, needed=needed)
    kind = VISION_MIME.get((mime or "").split(";")[0].strip().lower())
    if not kind:
        return {
            "match": None,
            "text": "Grok can check JPEG or PNG only. File was stored without a vision check.",
            "needed": needed,
        }
    load_dotenv()
    key = os.environ.get("XAI_API_KEY")
    if not key:
        return {
            "match": None,
            "text": "XAI_API_KEY is missing. File was stored without a vision check.",
            "needed": needed,
        }
    try:
        text = _ask_grok(key, content, kind, needed)
    except Exception as exc:  # noqa: BLE001 — upload should still succeed
        return {"match": None, "text": f"Grok check failed: {exc}", "needed": needed}
    upper = (text or "").lstrip()
    match: bool | None
    if upper.upper().startswith("NO MATCH"):
        match = False
    elif upper.upper().startswith("MATCH"):
        match = True
    else:
        match = None
    return {"match": match, "text": text.strip(), "needed": needed}


def _ask_grok(api_key: str, content: bytes, kind: str, needed: str) -> str:
    from xai_sdk import Client
    from xai_sdk.chat import image, user

    data = base64.b64encode(content).decode("ascii")
    prompt = (
        f"This first-notice file needs {needed}. "
        "Does this image show that? Start with MATCH or NO MATCH, then 1-2 short sentences. "
        "Do not mention money."
    )
    client = Client(api_key=api_key)
    chat = client.chat.create(model=MODEL, temperature=0)
    chat.append(user(prompt, image(f"data:image/{kind};base64,{data}", detail="low")))
    response = chat.sample()
    text = (response.content or "").strip()
    if not text:
        raise AgentError("empty Grok vision response")
    return text

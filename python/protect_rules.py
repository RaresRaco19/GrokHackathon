#!/usr/bin/env python3
"""PreToolUse hook: the kit rule book is read-only. Do not invent another."""
from __future__ import annotations

import json
import sys

PROTECTED_NAMES = {"policy-excerpt.md"}
BLOCK_NEW_RULE_BOOKS = True


def _paths_from(tool_input: dict) -> list[str]:
    keys = (
        "file_path",
        "target_file",
        "path",
        "filePath",
        "filename",
    )
    found: list[str] = []
    for key in keys:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            found.append(value)
    command = tool_input.get("command")
    if isinstance(command, str) and command:
        found.append(command)
    return found


def _mentions_rule_book(text: str) -> bool:
    lower = text.replace("\\", "/").lower()
    return any(name in lower for name in PROTECTED_NAMES)


def _creates_other_rule_book(text: str) -> bool:
    lower = text.replace("\\", "/").lower()
    if "policy-excerpt.md" in lower:
        return False
    return "rules.md" in lower or "payer_rules.md" in lower


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"decision": "allow"}))
        return

    tool_input = event.get("toolInput") or event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    blobs = _paths_from(tool_input)
    new_string = tool_input.get("new_string") or tool_input.get("content") or ""
    if isinstance(new_string, str):
        blobs.append(new_string)

    haystack = "\n".join(blobs)
    if _mentions_rule_book(haystack):
        print(
            json.dumps(
                {
                    "decision": "deny",
                    "reason": (
                        "md/policy-excerpt.md is the given rule book. Do not edit it. "
                        "Do not invent rules. Made-up rules fail the lab."
                    ),
                }
            )
        )
        sys.exit(2)

    if BLOCK_NEW_RULE_BOOKS and _creates_other_rule_book(haystack):
        print(
            json.dumps(
                {
                    "decision": "deny",
                    "reason": (
                        "Do not add another rule file. The only source of rules "
                        "is md/policy-excerpt.md."
                    ),
                }
            )
        )
        sys.exit(2)

    print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()

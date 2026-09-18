"""JSON-RPC client for the kit MCP stub at repo-root rules_mcp.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from backend.paths import repo_root


class RulesMcp:
    """Talk to rules_mcp.py over stdin/stdout. Citations come from lookup_rule."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else repo_root()
        self._proc: subprocess.Popen[str] | None = None
        self._next_id = 1

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        script = self.root / "rules_mcp.py"
        if not script.is_file():
            raise FileNotFoundError(f"rules MCP stub not found: {script}")
        self._proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            cwd=str(self.root),
        )
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "claimdesk-backend", "version": "0.1"},
            },
        )

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                    proc.wait(timeout=3)
                except Exception:
                    pass
        for stream in (proc.stdout, proc.stderr):
            if stream is None:
                continue
            try:
                stream.close()
            except OSError:
                pass

    def __enter__(self) -> "RulesMcp":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def lookup_rule(self, query: str) -> str:
        self.start()
        result = self._rpc(
            "tools/call",
            {"name": "lookup_rule", "arguments": {"query": query}},
        )
        return _tool_text(result)

    def list_rules(self) -> str:
        self.start()
        result = self._rpc("tools/call", {"name": "list_rules", "arguments": {}})
        return _tool_text(result)

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("rules MCP is not running")
        rid = self._next_id
        self._next_id += 1
        req: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            req["params"] = params
        self._proc.stdin.write(json.dumps(req) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("rules MCP closed without a response")
        data = json.loads(line)
        if not isinstance(data, dict):
            raise RuntimeError("rules MCP returned a non-object")
        if "error" in data:
            raise RuntimeError(f"rules MCP error: {data['error']}")
        return data


def _tool_text(rpc: dict[str, Any]) -> str:
    content = ((rpc.get("result") or {}).get("content") or [])
    if not content:
        return ""
    first = content[0]
    if isinstance(first, dict):
        return str(first.get("text") or "")
    return str(first)

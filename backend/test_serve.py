"""API live-ops with a scripted Grok that still hits the real MCP."""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.agent import LlmTurn, ToolCall
from backend.serve import DeskApp, make_server


class AutoLookupClerk:
    """Per-assess script: lookup_rule then JSON quoting the MCP line."""

    def start(self, system_prompt: str, user_text: str) -> None:
        self.user_text = user_text
        self.outputs: list[dict] = []
        self.step = 0

    def complete(self, tool_choice: str) -> LlmTurn:
        if self.step == 0:
            self.step = 1
            return LlmTurn(tool_calls=[ToolCall("1", "lookup_rule", {"query": self._query()})])
        quote = str(self.outputs[-1]["text"])
        report_id = "question"
        match = re.search(r'"id"\s*:\s*"(CL-[^"]+)"', self.user_text, re.I)
        if match:
            report_id = match.group(1).upper()
        rid_match = re.search(r"\b(PX-[A-Z0-9-]+)\b", quote)
        rid = rid_match.group(1).upper() if rid_match else None
        decision = {
            "PX-GLASS": "open",
            "PX-FLOOD": "refuse",
            "PX-COLLISION": "hold",
            "PX-NO-PAY": "refuse",
        }.get(rid or "", "refuse")
        return LlmTurn(
            text=json.dumps({"id": report_id, "decision": decision, "rule_id": rid, "quote": quote})
        )

    def remember_turn(self) -> None:
        return

    def add_tool_result(self, call: ToolCall, output: str) -> None:
        self.outputs.append({"tool": call.name, "query": call.arguments.get("query"), "text": output})

    def add_user(self, text: str) -> None:
        self.step = 0

    def _query(self) -> str:
        lower = self.user_text.lower()
        if "will we pay" in lower:
            return "PX-NO-PAY"
        match = re.search(r'"cover"\s*:\s*"(PX-[A-Z0-9-]+)"', self.user_text, re.I)
        if match:
            return match.group(1).upper()
        return "policy"


class ServeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls._old_var = os.environ.get("CLAIMDESK_VAR")
        os.environ["CLAIMDESK_VAR"] = cls.tmp.name
        cls.app = DeskApp(llm=AutoLookupClerk())
        cls.server, _ = make_server("127.0.0.1", 0, app=cls.app)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.app.close()
        cls.tmp.cleanup()
        if cls._old_var is None:
            os.environ.pop("CLAIMDESK_VAR", None)
        else:
            os.environ["CLAIMDESK_VAR"] = cls._old_var

    def _json(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(self.base + path, data=data, method=method)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            return exc.code, payload

    def test_health_mcp(self) -> None:
        status, payload = self._json("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("Policy excerpt", payload["rules"])

    def test_queue_does_not_call_model(self) -> None:
        status, payload = self._json("GET", "/api/queue")
        self.assertEqual(status, 200)
        self.assertEqual({item["id"] for item in payload["items"]}, {"CL-03", "CL-04", "CL-08"})
        for item in payload["items"]:
            if item.get("decision") is None:
                self.assertTrue(item.get("needs_assess"))
                self.assertFalse(item.get("can_confirm"))
            else:
                self.assertIn(item["decision"], ("open", "hold", "refuse"))

    def test_cl03_confirm_then_undo(self) -> None:
        status, payload = self._json("POST", "/api/assess", {"id": "CL-03"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["decision"], "open")
        self.assertTrue(payload["can_confirm"])
        status, payload = self._json("POST", "/api/confirm", {"id": "CL-03"})
        self.assertEqual(status, 200)
        self.assertTrue(str(payload["claim_number"]).startswith("FNOL-CL-03-"))
        self.assertTrue(payload["can_undo"])
        status, payload = self._json("POST", "/api/undo", {"id": "CL-03"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["send_state"], "draft")
        self.assertTrue(payload["can_confirm"])

    def test_cl04_confirm_is_400(self) -> None:
        self._json("POST", "/api/assess", {"id": "CL-04"})
        status, payload = self._json("POST", "/api/confirm", {"id": "CL-04"})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "refuse is not sent")

    def test_log_has_no_amounts(self) -> None:
        self._json("POST", "/api/assess", {"id": "CL-04"})
        status, payload = self._json("GET", "/api/log")
        self.assertEqual(status, 200)
        blob = json.dumps(payload)
        self.assertNotRegex(blob, r"[$£€]\s*\d")
        for event in payload["events"]:
            for key in event:
                self.assertNotRegex(str(key), r"amount|payout|\$")

    def test_will_we_pay(self) -> None:
        status, payload = self._json("POST", "/api/assess", {"question": "will we pay?"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["decision"], "refuse")
        self.assertEqual(payload["rule_id"], "PX-NO-PAY")
        self.assertTrue(payload["quote"].startswith("PX-NO-PAY."))

    def test_clerk_html_served(self) -> None:
        req = Request(self.base + "/clerk.html", method="GET")
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            self.assertEqual(resp.status, 200)
            self.assertIn("Clerk surface", body)
            self.assertIn("desk.js", body)

    def test_queue_payload_has_reports_and_policy(self) -> None:
        status, payload = self._json("GET", "/api/queue")
        self.assertEqual(status, 200)
        self.assertEqual({row["id"] for row in payload["reports"]}, {"CL-03", "CL-04", "CL-08"})
        self.assertTrue(any(p["id"] == "PX-GLASS" for p in payload["policy"]))
        self.assertIn("photo", payload["reports"][0])
        self.assertIn("received_at", payload["reports"][0])


if __name__ == "__main__":
    unittest.main()

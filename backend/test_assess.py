"""Agent loop: Grok (scripted) must call lookup_rule; MCP supplies the quote."""
from __future__ import annotations

import json
import os
import unittest

from backend.agent import AgentError, LlmTurn, ScriptedLlm, ToolCall, run_agent
from backend.assess import assess
from backend.mcp_client import RulesMcp


def _script(query: str, decision: str, rule_id: str | None, report_id: str) -> ScriptedLlm:
    def after(outputs):
        quote = outputs[-1]["text"]
        return LlmTurn(
            text=json.dumps(
                {
                    "id": report_id,
                    "decision": decision,
                    "rule_id": rule_id,
                    "quote": quote,
                }
            )
        )

    return ScriptedLlm(
        [
            LlmTurn(tool_calls=[ToolCall("1", "lookup_rule", {"query": query})]),
            after,
        ]
    )


class AssessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RulesMcp()
        cls.client.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_cl03_open_quotes_glass_from_mcp(self) -> None:
        llm = _script("PX-GLASS", "open", "PX-GLASS", "CL-03")
        row = assess(report_id="CL-03", client=self.client, llm=llm)
        self.assertEqual(row["decision"], "open")
        self.assertEqual(row["rule_id"], "PX-GLASS")
        self.assertTrue(row["quote"].startswith("PX-GLASS."))
        self.assertEqual(row["mcp"]["tool"], "lookup_rule")
        self.assertEqual(row["mcp"]["query"], "PX-GLASS")
        self.assertEqual(llm.outputs[0]["query"], "PX-GLASS")

    def test_cl04_refuse_quotes_flood(self) -> None:
        llm = _script("PX-FLOOD", "refuse", "PX-FLOOD", "CL-04")
        row = assess(report_id="CL-04", client=self.client, llm=llm)
        self.assertEqual(row["decision"], "refuse")
        self.assertTrue(row["quote"].startswith("PX-FLOOD."))

    def test_cl08_hold_for_photos(self) -> None:
        llm = _script("PX-COLLISION", "hold", "PX-COLLISION", "CL-08")
        row = assess(report_id="CL-08", client=self.client, llm=llm)
        self.assertEqual(row["decision"], "hold")
        self.assertEqual(row["display"], "hold for photos")
        self.assertTrue(row["quote"].startswith("PX-COLLISION."))

    def test_will_we_pay_uses_no_pay_tool(self) -> None:
        llm = _script("PX-NO-PAY", "refuse", "PX-NO-PAY", "question")
        row = assess(question="will we pay?", client=self.client, llm=llm)
        self.assertEqual(row["decision"], "refuse")
        self.assertEqual(row["rule_id"], "PX-NO-PAY")
        self.assertEqual(row["mcp"]["query"], "PX-NO-PAY")

    def test_rejects_decision_without_mcp(self) -> None:
        llm = ScriptedLlm(
            [
                LlmTurn(
                    text=json.dumps(
                        {
                            "id": "CL-03",
                            "decision": "open",
                            "rule_id": "PX-GLASS",
                            "quote": "PX-GLASS. invented",
                        }
                    )
                )
            ]
        )
        with self.assertRaises(AgentError) as ctx:
            run_agent("Assess CL-03", self.client, llm=llm)
        self.assertIn("lookup_rule", ctx.exception.message)

    def test_rejects_invented_rule_id(self) -> None:
        def after(outputs):
            return LlmTurn(
                text=json.dumps(
                    {
                        "id": "CL-03",
                        "decision": "open",
                        "rule_id": "PX-MAGIC",
                        "quote": outputs[-1]["text"],
                    }
                )
            )

        llm = ScriptedLlm(
            [
                LlmTurn(tool_calls=[ToolCall("1", "lookup_rule", {"query": "PX-GLASS"})]),
                after,
            ]
        )
        with self.assertRaises(AgentError):
            assess(report_id="CL-03", client=self.client, llm=llm)

    def test_rejects_payout_amount(self) -> None:
        def after(outputs):
            return LlmTurn(
                text=json.dumps(
                    {
                        "id": "CL-03",
                        "decision": "open",
                        "rule_id": "PX-GLASS",
                        "quote": outputs[-1]["text"],
                        "note": "we will pay $500",
                    }
                )
            )

        llm = ScriptedLlm(
            [
                LlmTurn(tool_calls=[ToolCall("1", "lookup_rule", {"query": "PX-GLASS"})]),
                after,
            ]
        )
        with self.assertRaises(AgentError) as ctx:
            assess(report_id="CL-03", client=self.client, llm=llm)
        self.assertIn("PX-NO-PAY", ctx.exception.message)

    def test_mcp_miss_does_not_invent_rule(self) -> None:
        quote = self.client.lookup_rule("made-up-rule")
        self.assertTrue(quote.lower().startswith("no rule line matched"))
        self.assertNotIn("PX-MAGIC", quote)

    @unittest.skipUnless(os.environ.get("XAI_API_KEY"), "live Grok call needs XAI_API_KEY")
    def test_live_cl04_refuse(self) -> None:
        row = assess(report_id="CL-04", client=self.client)
        self.assertEqual(row["decision"], "refuse")
        self.assertTrue(row["quote"].startswith("PX-FLOOD."))
        self.assertEqual(row["mcp"]["tool"], "lookup_rule")


if __name__ == "__main__":
    unittest.main()

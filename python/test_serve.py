#!/usr/bin/env python3
"""Website API uses decide.py + policy-excerpt.md. Confirm-before-send on a temp var/."""
from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from python import decide
from python.serve_desk import (
    ask_payload,
    confirm,
    ensure_state,
    health_payload,
    load_log,
    log_path,
    queue_payload,
    state_path,
    undo,
    utccompact,
)

CLAIM_NUMBER = re.compile(r"^FNOL-CL-03-\d{8}T\d{6}Z$")
PROMISED_AMOUNT = re.compile(
    r"\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:usd|dollars)\b",
    re.IGNORECASE,
)


class DeskApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._prev = os.environ.get("CLAIMDESK_VAR")
        os.environ["CLAIMDESK_VAR"] = self._tmp.name
        self.var = Path(self._tmp.name)

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("CLAIMDESK_VAR", None)
        else:
            os.environ["CLAIMDESK_VAR"] = self._prev
        self._tmp.cleanup()

    def _by_id(self) -> dict[str, dict]:
        return {row["id"]: row for row in queue_payload()}

    def test_queue_matches_engine(self) -> None:
        policy = decide.load_policy()
        for row in queue_payload():
            engine = decide.decide_report(
                {
                    "id": row["id"],
                    "peril": row["peril"],
                    "photos": row["photos"],
                    "cover": row["cover"],
                },
                policy,
            )
            self.assertEqual(row["decision"], engine["decision"])
            self.assertEqual(row["rule_id"], engine["rule_id"])
            self.assertEqual(row["quoted"], engine["quoted"])
            self.assertEqual(row["source"], "policy-excerpt.md")
        by_id = self._by_id()
        self.assertEqual(by_id["CL-03"]["decision"], "open")
        self.assertEqual(by_id["CL-03"]["label"], "open")
        self.assertEqual(by_id["CL-04"]["decision"], "refuse")
        self.assertEqual(by_id["CL-08"]["decision"], "hold")
        self.assertEqual(by_id["CL-08"]["label"], "hold for photos")

    def test_queue_is_read_only(self) -> None:
        rows = queue_payload()
        self.assertEqual([row["id"] for row in rows], ["CL-03", "CL-04", "CL-08"])
        self.assertFalse(state_path().exists())
        self.assertFalse(log_path().exists())
        self.assertEqual(list(self.var.iterdir()), [])

    def test_queue_flags_before_confirm(self) -> None:
        by_id = self._by_id()
        self.assertTrue(by_id["CL-03"]["can_confirm"])
        self.assertFalse(by_id["CL-03"]["can_undo"])
        self.assertEqual(by_id["CL-03"]["send_state"], "draft")
        self.assertIsNone(by_id["CL-03"]["claim_number"])
        self.assertFalse(by_id["CL-04"]["can_confirm"])
        self.assertFalse(by_id["CL-04"]["can_undo"])
        self.assertTrue(by_id["CL-08"]["can_confirm"])
        self.assertFalse(by_id["CL-08"]["can_undo"])

    def test_ask_payout_is_refused(self) -> None:
        result = ask_payload("will we pay?")
        self.assertEqual(result["label"], "refuse")
        self.assertEqual(result["decision"], "refuse")
        self.assertEqual(result["rule_id"], "PX-NO-PAY")
        self.assertIn("PX-NO-PAY", result["quoted"])
        self.assertIn("payout", result["detail"].lower())

    def test_ask_medical_legal_is_refused(self) -> None:
        result = ask_payload("what medicine should I prescribe")
        self.assertEqual(result["label"], "refuse")
        self.assertEqual(result["decision"], "refuse")
        self.assertIsNone(result["rule_id"])
        self.assertEqual(result["quoted"], "No rule line matched.")
        self.assertIn("medical or legal", result["detail"])

    def test_ask_other_is_off_desk(self) -> None:
        result = ask_payload("what is the weather")
        self.assertEqual(result["label"], "Off-desk")
        self.assertEqual(result["decision"], "Off-desk")
        self.assertIsNone(result["rule_id"])
        self.assertEqual(result["quoted"], "No rule line matched.")
        self.assertIn("claim intake", result["detail"].lower())

    def test_cl03_confirm_then_undo(self) -> None:
        status, payload = confirm("CL-03")
        self.assertEqual(status, 200)
        self.assertEqual(payload["send_state"], "sent")
        self.assertRegex(payload["claim_number"], CLAIM_NUMBER)
        self.assertFalse(payload["can_confirm"])
        self.assertTrue(payload["can_undo"])
        by_id = self._by_id()
        self.assertEqual(by_id["CL-03"]["send_state"], "sent")
        self.assertEqual(by_id["CL-03"]["claim_number"], payload["claim_number"])
        self.assertTrue(by_id["CL-03"]["can_undo"])
        self.assertFalse(by_id["CL-03"]["can_confirm"])

        status, undone = undo("CL-03")
        self.assertEqual(status, 200)
        self.assertEqual(undone["send_state"], "draft")
        self.assertIsNone(undone["claim_number"])
        self.assertTrue(undone["can_confirm"])
        self.assertFalse(undone["can_undo"])
        restored = self._by_id()["CL-03"]
        self.assertEqual(restored["send_state"], "draft")
        self.assertIsNone(restored["claim_number"])
        self.assertTrue(restored["can_confirm"])
        self.assertFalse(restored["can_undo"])

    def test_cl04_confirm_is_400(self) -> None:
        status, payload = confirm("CL-04")
        self.assertEqual(status, 400)
        self.assertEqual(payload, {"error": "refuse is not sent"})
        by_id = self._by_id()
        self.assertEqual(by_id["CL-04"]["send_state"], "draft")
        self.assertIsNone(by_id["CL-04"]["claim_number"])
        self.assertFalse(by_id["CL-04"]["can_confirm"])

    def test_hold_confirm_has_no_claim_number(self) -> None:
        status, payload = confirm("CL-08")
        self.assertEqual(status, 200)
        self.assertEqual(payload["send_state"], "held")
        self.assertIsNone(payload["claim_number"])
        self.assertTrue(payload["can_undo"])
        self.assertFalse(payload["can_confirm"])

    def test_ensure_state_logs_refuse_once(self) -> None:
        ensure_state()
        ensure_state()
        events = [row for row in load_log() if row.get("id") == "CL-04"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["decision"], "refuse")
        self.assertEqual(events[0]["event"], "refuse")
        self.assertTrue(events[0]["quoted"].startswith("PX-FLOOD."))
        state = json.loads(state_path().read_text(encoding="utf-8"))
        self.assertEqual(set(state), {"CL-03", "CL-04", "CL-08"})
        self.assertTrue(state["CL-04"]["refuse_logged"])
        self.assertEqual(state["CL-03"]["send_state"], "draft")

    def test_log_has_no_amount_payout_dollar_keys(self) -> None:
        ensure_state()
        confirm("CL-03")
        undo("CL-03")
        confirm("CL-04")
        events = load_log()
        self.assertTrue(events)
        for event in events:
            keys = list(event)
            lowered = {key.lower() for key in keys}
            self.assertNotIn("amount", lowered)
            self.assertNotIn("payout", lowered)
            self.assertFalse(any("$" in key for key in keys))
            blob = json.dumps(event)
            self.assertIsNone(PROMISED_AMOUNT.search(blob), blob)

    def test_utccompact_format(self) -> None:
        stamp = utccompact()
        self.assertRegex(stamp, r"^\d{8}T\d{6}Z$")

    def test_health_points_at_kit(self) -> None:
        payload = health_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["engine"], "python/decide.py")
        self.assertTrue(payload["policy"].endswith("policy-excerpt.md"))
        self.assertTrue(payload["reports"].endswith("fnol.json"))


if __name__ == "__main__":
    unittest.main()

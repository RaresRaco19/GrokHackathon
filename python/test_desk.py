"""Golden tests: kit reports still decide open / hold / refuse from policy-excerpt.md."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from python import decide

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "python" / "decide.py"
POLICY = (ROOT / "md" / "policy-excerpt.md").read_text(encoding="utf-8")

EXPECTED = {
    "CL-03": {"decision": "open", "rule_id": "PX-GLASS"},
    "CL-04": {"decision": "refuse", "rule_id": "PX-FLOOD"},
    "CL-08": {"decision": "hold", "rule_id": "PX-COLLISION"},
}

# Quoted kit lines may contain the word payout as a prohibition.
PROMISED_AMOUNT = re.compile(
    r"\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:usd|dollars)\b",
    re.IGNORECASE,
)


def run_decide(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def load_json(*args: str) -> dict | list:
    return json.loads(run_decide(*args).stdout)


class DeskGoldenTests(unittest.TestCase):
    def test_three_reports_match_kit_order(self) -> None:
        results = load_json()
        self.assertEqual(len(results), 3)
        self.assertEqual([row["id"] for row in results], ["CL-03", "CL-04", "CL-08"])
        by_id = {row["id"]: row for row in results}
        for report_id, expect in EXPECTED.items():
            with self.subTest(report_id=report_id):
                row = by_id[report_id]
                self.assertEqual(row["decision"], expect["decision"])
                self.assertEqual(row["rule_id"], expect["rule_id"])
                self.assertIn(expect["rule_id"], row["quoted"])
                self.assertIn(row["quoted"], POLICY)

    def test_cl03_open_glass(self) -> None:
        row = load_json("CL-03")
        self.assertEqual(row["decision"], "open")
        self.assertEqual(row["rule_id"], "PX-GLASS")
        self.assertTrue(row["photos"])
        self.assertEqual(row["cover"], "PX-GLASS")
        self.assertIn(row["quoted"], POLICY)
        self.assertTrue(row["quoted"].startswith("PX-GLASS."))

    def test_cl04_refuse_flood_even_with_photos(self) -> None:
        row = load_json("CL-04")
        self.assertEqual(row["decision"], "refuse")
        self.assertEqual(row["rule_id"], "PX-FLOOD")
        self.assertTrue(row["photos"])
        self.assertEqual(row["cover"], "PX-FLOOD")
        self.assertEqual(row["peril"], "flood")
        self.assertIn(row["quoted"], POLICY)
        self.assertTrue(row["quoted"].startswith("PX-FLOOD."))

    def test_cl08_hold_collision(self) -> None:
        row = load_json("CL-08")
        self.assertEqual(row["decision"], "hold")
        self.assertNotIn("label", row)
        self.assertEqual(row["rule_id"], "PX-COLLISION")
        self.assertFalse(row["photos"])
        self.assertIn(row["quoted"], POLICY)
        self.assertTrue(row["quoted"].startswith("PX-COLLISION."))

    def test_each_id_flag(self) -> None:
        for report_id, expect in EXPECTED.items():
            with self.subTest(report_id=report_id):
                row = load_json(report_id)
                self.assertEqual(row["decision"], expect["decision"])
                self.assertEqual(row["rule_id"], expect["rule_id"])

    def test_quotes_come_from_policy_excerpt_only(self) -> None:
        for row in load_json():
            self.assertEqual(row["source"], "policy-excerpt.md")
            self.assertIn(row["quoted"], POLICY)
            self.assertTrue(
                any(line.startswith(row["rule_id"] + ".") for line in POLICY.splitlines()),
                f"{row['rule_id']} missing from policy-excerpt.md",
            )
            self.assertNotIn("PX-FAKE", row["quoted"])

    def test_payout_ask_will_we_pay(self) -> None:
        row = load_json("--advice", "will we pay?")
        self.assertEqual(row["decision"], "refuse")
        self.assertEqual(row["rule_id"], "PX-NO-PAY")
        self.assertIn("PX-NO-PAY", row["quoted"])
        self.assertIn(row["quoted"], POLICY)
        self.assertEqual(row["source"], "policy-excerpt.md")

    def test_payout_family_phrases(self) -> None:
        phrases = (
            "what is the payout",
            "name a settlement",
            "how much",
            "we will pay",
            "payment please",
            "$500",
            "500 dollars",
            "usd please",
            "indemnify this",
            "post a reserve",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                row = load_json("--advice", phrase)
                self.assertEqual(row["decision"], "refuse")
                self.assertEqual(row["rule_id"], "PX-NO-PAY")

    def test_engine_output_has_no_promised_amount(self) -> None:
        blobs = [
            json.dumps(load_json()),
            json.dumps(load_json("CL-03")),
            json.dumps(load_json("CL-04")),
            json.dumps(load_json("CL-08")),
            json.dumps(load_json("--advice", "will we pay?")),
            json.dumps(load_json("--advice", "what is the settlement")),
        ]
        for blob in blobs:
            self.assertIsNone(PROMISED_AMOUNT.search(blob), blob)
        glass = load_json("CL-03")
        self.assertIn("payout", glass["quoted"].lower())

    def test_no_open_collision_path(self) -> None:
        for row in load_json():
            if row.get("cover") == "PX-COLLISION":
                self.assertNotEqual(row["decision"], "open")
        policy = decide.load_policy()
        synthetic = decide.decide_report(
            {
                "id": "CL-XX",
                "peril": "collision",
                "photos": True,
                "cover": "PX-COLLISION",
            },
            policy,
        )
        self.assertNotEqual(synthetic["decision"], "open")
        self.assertEqual(synthetic["decision"], "refuse")
        self.assertIsNone(synthetic["rule_id"])

    def test_medical_legal_is_refused_without_rule_id(self) -> None:
        row = load_json("--advice", "what dose of medicine am I liable for")
        self.assertEqual(row["decision"], "refuse")
        self.assertIsNone(row["rule_id"])
        self.assertEqual(row["quoted"], "No rule line matched.")
        self.assertIn("medical or legal", row["message"])

    def test_off_desk_ask_is_no_match_without_medical_copy(self) -> None:
        row = load_json("--advice", "is glass covered")
        self.assertEqual(row["decision"], "refuse")
        self.assertIsNone(row["rule_id"])
        self.assertEqual(row["quoted"], "No rule line matched.")
        self.assertNotIn("message", row)
        self.assertNotEqual(row.get("rule_id"), "PX-NO-PAY")

    def test_unknown_id_exits_1(self) -> None:
        completed = run_decide("CL-99", check=False)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("CL-99", completed.stderr)

    def test_clerk_view_cl04_prints_refuse(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "CL-04"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("refuse", completed.stdout)
        self.assertIn("PX-FLOOD.", completed.stdout)
        self.assertIn("photos=True", completed.stdout)

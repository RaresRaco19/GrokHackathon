#!/usr/bin/env python3
"""Repeatable FNOL desk. Quotes md/policy-excerpt.md. Invents nothing."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = ROOT / "md" / "policy-excerpt.md"
REPORTS_FILE = ROOT / "data" / "fnol.json"

REQUIRED_KEYS = ("id", "peril", "photos", "cover")
NO_MATCH = "No rule line matched."

PAYOUT_REFUSAL = "The desk does not state a payout."
MEDICAL_LEGAL_REFUSAL = (
    "The desk only decides intake coverage. It will not give medical or legal advice."
)

# Payout-family before medical/legal. `pay(ment)` is pay / payment; `$` needs digits.
PAYOUT_PATTERNS = (
    r"\bpayout\b",
    r"\bsettlement\b",
    r"\bhow much\b",
    r"\bwe will pay\b",
    r"\bwill we pay\b",
    r"\bpayments?\b",
    r"\bpay\b",
    r"\$\s*\d",
    r"\bdollars\b",
    r"\busd\b",
    r"indemnif",
    r"\breserve\b",
)

MEDICAL_LEGAL_PATTERNS = (
    r"\bprescribe\b",
    r"\bprescription\b",
    r"\bdose\b",
    r"\bdosage\b",
    r"\bmedicine\b",
    r"\bmedication\b",
    r"\bliable\b",
    r"\bliability\b",
    r"\blegal advice\b",
    r"\battorney\b",
    r"\blawyer\b",
)


def load_policy() -> dict[str, str]:
    text = POLICY_FILE.read_text(encoding="utf-8")
    policy: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^(PX-[A-Z-]+)\.\s+(.*)$", line.strip())
        if match:
            policy[match.group(1)] = match.group(2).strip()
    return policy


def load_reports() -> list[dict]:
    raw = json.loads(REPORTS_FILE.read_text(encoding="utf-8"))
    return [normalize_report(row) for row in raw]


def normalize_report(raw: dict) -> dict:
    missing = [key for key in REQUIRED_KEYS if key not in raw]
    if missing:
        raise ValueError(f"report missing keys {missing}")
    return {
        "id": raw["id"],
        "peril": raw["peril"],
        "photos": raw["photos"],
        "cover": raw["cover"],
    }


def quote_line(policy: dict[str, str], rule_id: str) -> str:
    body = policy.get(rule_id)
    if not body:
        return NO_MATCH
    return f"{rule_id}. {body}"


def record(
    *,
    decision: str,
    rule_id: str | None,
    quoted: str,
    report: dict | None = None,
    message: str | None = None,
) -> dict:
    out: dict = {
        "decision": decision,
        "rule_id": rule_id,
        "quoted": quoted,
        "source": POLICY_FILE.name,
    }
    if report is not None:
        out.update(
            {
                "id": report["id"],
                "peril": report["peril"],
                "photos": report["photos"],
                "cover": report["cover"],
            }
        )
    if message:
        out["message"] = message
    return out


RULE_HINTS = {
    "PX-GLASS": ("glass", "windshield", "window pane", "shattered", "broken window"),
    "PX-FLOOD": ("flood", "flooding", "inundat", "high water"),
    "PX-COLLISION": ("collision", "crash", "accident", "dent", "bumper", "impact"),
}


def refuse_off_scope(text: str, policy: dict[str, str]) -> dict:
    return ask_against_rules(text, policy)


def ask_against_rules(text: str, policy: dict[str, str]) -> dict:
    """Score a free-text ask against policy-excerpt.md only. Invent nothing."""
    lowered = (text or "").lower()
    if any(re.search(pattern, lowered) for pattern in PAYOUT_PATTERNS):
        return record(
            decision="refuse",
            rule_id="PX-NO-PAY",
            quoted=quote_line(policy, "PX-NO-PAY"),
            message=PAYOUT_REFUSAL,
        )
    if any(re.search(pattern, lowered) for pattern in MEDICAL_LEGAL_PATTERNS):
        return record(
            decision="refuse",
            rule_id=None,
            quoted=NO_MATCH,
            message=MEDICAL_LEGAL_REFUSAL,
        )
    hits = [
        rule_id
        for rule_id, hints in RULE_HINTS.items()
        if rule_id in policy
        and (
            rule_id.lower() in lowered
            or any(hint in lowered for hint in hints)
        )
    ]
    if len(hits) == 1:
        rule_id = hits[0]
        quoted = quote_line(policy, rule_id)
        if rule_id == "PX-FLOOD":
            return record(decision="refuse", rule_id=rule_id, quoted=quoted)
        if rule_id == "PX-GLASS":
            return record(decision="open", rule_id=rule_id, quoted=quoted)
        missing = any(
            token in lowered for token in ("missing", "no photo", "without photo", "need photo")
        )
        on_file = any(
            token in lowered for token in ("photos on", "photo on", "have photo", "with photo")
        )
        if on_file and not missing:
            return record(decision="open", rule_id=rule_id, quoted=quoted)
        return record(decision="hold", rule_id=rule_id, quoted=quoted)
    return record(decision="refuse", rule_id=None, quoted=NO_MATCH)


def decide_report(report: dict, policy: dict[str, str]) -> dict:
    report = normalize_report(report)
    cover = str(report["cover"])
    if cover not in policy:
        return record(decision="refuse", rule_id=None, quoted=NO_MATCH, report=report)
    # Flood before photos — CL-04 has photos true and still refuses.
    if cover == "PX-FLOOD":
        return record(
            decision="refuse",
            rule_id="PX-FLOOD",
            quoted=quote_line(policy, "PX-FLOOD"),
            report=report,
        )
    if report["photos"] is False:
        return record(
            decision="hold",
            rule_id=cover,
            quoted=quote_line(policy, cover),
            report=report,
        )
    # Photos on file: glass and collision may be accepted for intake.
    if cover in ("PX-GLASS", "PX-COLLISION"):
        return record(
            decision="open",
            rule_id=cover,
            quoted=quote_line(policy, cover),
            report=report,
        )
    return record(decision="refuse", rule_id=None, quoted=NO_MATCH, report=report)


def render(result: dict) -> str:
    lines: list[str] = []
    if result.get("id"):
        lines.append(
            f"{result['id']}  {result.get('peril', '')}  "
            f"photos={result.get('photos')}  cover={result.get('cover', '')}"
        )
    shown = "hold for photos" if result["decision"] == "hold" else result["decision"]
    lines.append(f"decision  {shown}")
    if result.get("rule_id"):
        lines.append(f"cited    {result['rule_id']}")
    lines.append(f"quoted   {result['quoted']}")
    if result.get("message"):
        lines.append(result["message"])
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decide CL-03 / CL-04 / CL-08 from kit files."
    )
    parser.add_argument(
        "report_id",
        nargs="?",
        help="CL-03, CL-04, or CL-08. Omit to decide all three.",
    )
    parser.add_argument(
        "--advice",
        metavar="QUESTION",
        help="Treat the text as an ask (payout / medical-legal / off-desk).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of the clerk view.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    policy = load_policy()
    results: list[dict]

    if args.advice:
        results = [ask_against_rules(args.advice, policy)]
    elif args.report_id:
        reports = load_reports()
        match = next((row for row in reports if row["id"] == args.report_id), None)
        if match is None:
            print(f"No report {args.report_id!r} in {REPORTS_FILE.name}", file=sys.stderr)
            return 1
        results = [decide_report(match, policy)]
    else:
        results = [decide_report(row, policy) for row in load_reports()]

    if args.json:
        payload = results[0] if len(results) == 1 else results
        print(json.dumps(payload, indent=2))
    else:
        print("\n\n".join(render(item) for item in results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

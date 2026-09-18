# Claim Intake Desk Constitution

Version: 1.0.0
Ratified: 2026-09-18
Last amended: 2026-09-18

This constitution is the standing set of non-negotiables for the FNOL claim-intake desk. Specs, plans, tasks, and code MUST comply. Lab source: Grok Enablement Workshop, Module 4.3. This is claim intake, not prior authorization.

## I. Kit rules are the only rules

`md/policy-excerpt.md` is the only source of coverage rules. Agents, scripts, skills, tests, and the website backend MUST cite lines that exist in that file. They MUST NOT invent a rule id, paraphrase a rule as if it were a new rule, or add a second rule book. Made-up rules fail the lab. The HTML/JS UI MUST NOT contain coverage rules.

Rationale: the working desk quotes PX-GLASS, PX-FLOOD, PX-COLLISION, and PX-NO-PAY. The kit file is the only artifact that contains those lines.

## II. Decisions quote the rule file

Every coverage decision MUST return a decision label, the cited rule id, and the verbatim rule line. Quote text MUST appear in `md/policy-excerpt.md`. If no line matches, the desk MUST say that no rule line matched and MUST NOT mint a substitute.

Rationale: the lab finish line requires quoted rules. Paraphrase-without-citation is a fail.

## III. Golden cases stay fixed

Until `md/policy-excerpt.md` or `data/fnol.json` change, these outcomes MUST hold:

| Report | Decision | Rule |
|--------|----------|------|
| CL-03 | open | PX-GLASS |
| CL-04 | refuse | PX-FLOOD |
| CL-08 | hold | PX-COLLISION |
| ask “will we pay?” | refuse | PX-NO-PAY |

Flood exclusion (PX-FLOOD) wins even when photos are true. Collision is hold-only when photos are missing; do not invent an open-collision path.

Rationale: these are the demo outcomes the rebuild must match. CL-04 is the scoring refuse case.

## IV. No payout

The desk decides intake only: open, hold, or refuse. It MUST NOT promise a payout, name a settlement amount, or write “we will pay”. A payout-family question MUST be refused and MUST cite PX-NO-PAY. Quoted kit lines MAY contain the word payout as a prohibition. Engine output MUST NOT contain `$` plus digits or a promised settlement number.

Medical or legal questions MUST be refused with no rule id and the no-match sentence. They are not coverage.

Rationale: PX-NO-PAY and the track scoring rule that a payout statement zeros Decisions.

## V. Inspect before write; do not copy the demo

Look at the kit folder before adding files. Do not copy workshop demo HTML. Do not invent claimant names, vehicles, or other chrome that is not in the kit files. Do not rewrite kit JSON/MD bodies.

Rationale: the module page says copying the demo HTML fails the lab. Extra demo fields are not in the kit.

## VI. Repeatable proof (oracle script)

A script that can be run again MUST produce the golden cases. That script is `python/decide.py`. A test MUST check that the three reports still decide the same way, that quotes come from `md/policy-excerpt.md`, that a payout ask is refused, and that engine output has no promised amount. The local website MUST call that same engine over HTTP; it MUST NOT re-implement the rules in JavaScript.

Rationale: lab must-show list (script + test). Cover-id lookup in `load_policy()`, not a token scan.

## VII. Grok Build surfaces stay honest

AGENTS.md, the review-fnol skill, the protect-rules hook, MCP `lookup_rule`, and the fnol-desk plugin MUST point at the same rule file and the same decision path. Chat MUST call `lookup_rule` rather than recalling rules from memory.

Rationale: lab must-show list. MCP lookup is the allowed way to read the rule file.

## Governance

- Amendments bump the version (MAJOR for principle removal or redefinition, MINOR for a new principle, PATCH for wording).
- Specs and plans MUST include a constitution check against these principles.
- A change that would invent a rule, skip a quote, state a payout, or alter a golden case without a kit-file change is a constitution violation and MUST NOT ship.

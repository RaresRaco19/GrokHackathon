# Implementation Plan: Claim Intake Desk (FNOL)

**Branch**: docs PR-5 | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/SDD/spec.md`

## Summary

Rebuild the claim-intake desk from kit files. A Python script is the repeatable decision engine. Grok Build is instructed via AGENTS.md, a review-fnol skill, a PreToolUse hook, project MCP `lookup_rule`, and an fnol-desk plugin. A local website (`web/` UI + `python/serve_desk.py` backend on 127.0.0.1:8788) invokes that same engine over HTTP with confirm-before-send. Intake Clerk is a briefed Bot that does not mint. Tests lock CL-03 / CL-04 / CL-08 and the payout refusal.

## Technical Context

**Language/Version**: Python 3 (stdlib only)
**Primary Dependencies**: none (json, re, pathlib, unittest, argparse, http.server)
**Storage**: kit files on disk (`data/fnol.json`, `md/policy-excerpt.md`)
**Testing**: `unittest` via `python3 -m unittest python.test_desk python.test_serve`
**Target Platform**: macOS laptop (workshop)
**Project Type**: single-folder agent kit (script + Grok Build config + local UI/backend + Bot brief)
**Performance Goals**: decide all three reports in under 1 second
**Constraints**: no extra rule files; no demo HTML copy; no network required to decide; no payout amounts
**Scale/Scope**: 3 reports, 4 rules, 1 MCP server, 1 plugin, 1 Bot brief

## Constitution Check

- I Kit rules only: script loads `md/policy-excerpt.md`; hook blocks edits; skill calls `lookup_rule`.
- II Quote the file: every decision record has `rule_id` + `quoted`.
- III Golden cases: encoded in `python/test_desk.py`.
- IV No payout: `--advice` path and PX-NO-PAY; medical/legal is no-match.
- V Inspect before write: recorded in `lab-plan.md` §1.
- VI Repeatable proof: `python/decide.py` + tests; website calls the same engine.
- VII Honest Grok surfaces: AGENTS.md, skill, hook, MCP, plugin.

No unjustified violations.

## Project Structure

### Documentation (this feature)

```text
lab-plan.md
AGENTS.md
README.md
docs/design.html
docs/c4.html
docs/lab-report.html
docs/plan.html
docs/track-scoring.html
SDD/
  constitution.md
  spec.md
  plan.md
  tasks.md
  data-model.md
  research.md
  quickstart.md
  contracts/decision.md
  checklists/requirements.md
```

### Source Code (repository root)

```text
data/fnol.json             # kit — do not rewrite
md/policy-excerpt.md       # kit — do not rewrite
python/
  decide.py                # engine (CLI + website)
  serve_desk.py            # HTTP backend for web/ on :8788
  display.json             # chrome only; never an engine input
  rules_mcp.py
  protect_rules.py
  test_desk.py
  test_serve.py            # API uses the engine
web/                       # UI only; calls /api/queue ask confirm undo log
bin/run.sh demo.sh desk.sh start-web.sh
var/.gitkeep
.grok/config.toml
.grok/skills/review-fnol/SKILL.md
.grok/hooks/protect-rules.json
.grok/plugins/fnol-desk/
```

**Structure Decision**: keep kit data where the workshop download put it (`data/`, `md/`). Put all Python under `python/`. Put the local website under `web/`. Put Grok Build config under `.grok/`. Put spec-driven docs under `SDD/`. No `ClaimDesk/` subfolder. No root MCP shim.

## Phase 0 — Research

See [research.md](./research.md). Unknowns resolved: kit vs demo chrome, MCP registration command, decision precedence (flood before photos), no root shim, port 8788.

## Phase 1 — Design

- [data-model.md](./data-model.md)
- [contracts/decision.md](./contracts/decision.md)
- [quickstart.md](./quickstart.md)

## Implementation notes

- Decision order: payout-family → medical/legal → flood → photos false → glass → no match.
- Quote format: `{id}. {body}` taken from the parsed rule file, not hard-coded English.
- Matching is cover-id lookup in `load_policy()`, not a token scan of peril text.
- MCP: `[mcp_servers.rules]` command `python3` args `["python/rules_mcp.py"]`. Also run `grok mcp add --scope project rules -- python3 python/rules_mcp.py` on the laptop.
- Hook matcher covers write/edit and shell so a `cat > md/policy-excerpt.md` rewrite is denied too.
- Plugin duplicates skill + hook + `.mcp.json` so the must-show "one pack" is visible.
- Website: `bin/desk.sh` runs `python/serve_desk.py` on 127.0.0.1:8788. UI calls queue / ask / confirm / undo / log. No rules in `web/desk.js`.
- Bot: paste-ready Intake Clerk brief in README. Does not mint. Does not write `var/`.

## Complexity Tracking

No constitution violations to justify.

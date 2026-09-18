# Implementation plan: 4.3 Claim intake

**Track:** Grok Enablement Workshop Module 4.3  
**Date:** 2026-09-18  
**Design:** [design.html](design.html) · canonical HLD/LLD reviewed to 0 open issues  
**Scoring:** [track-scoring.html](track-scoring.html)  
**Execute:** `/execute-plan PLAN.md` (this file’s `## PR Plan` is the DAG)

## Product root (supersedes ClaimDesk/)

Kit and MCP are already on this laptop in **this folder**. Do not create `ClaimDesk/`. Do not copy kit files.

| Already on disk | Path |
|-----------------|------|
| Reports | `fnol.json` |
| Only rule book | `policy-excerpt.md` |
| MCP stub | `rules_mcp.py` |
| MCP registration | `.grok/config.toml` → `python3 rules_mcp.py` (user ran `grok mcp add --scope project rules -- python3 rules_mcp.py`) |
| Briefing (not product) | `track-scoring.html`, `design.html`, this `PLAN.md` |

Implement the desk **in place** under `/Users/tek/work/xAI/project/Hackathon/`, cloning DeskAgent’s layout (`python/`, `web/`, `bin/`, `.grok/`, `docs/`, `SDD/`) around the kit that is already here.

## Golden cases (from kit, not invented)

| Id | peril | photos | cover | Decision | Cited line prefix |
|----|--------|--------|--------|----------|-------------------|
| **CL-03** | glass | true | PX-GLASS | **open** (draft until confirm) | `PX-GLASS.` |
| **CL-04** | flood | true | PX-FLOOD | **refuse** — scoring case, log not send | `PX-FLOOD.` |
| CL-08 | collision | false | PX-COLLISION | **hold** (display “hold for photos”; pocket) | `PX-COLLISION.` |
| ask “will we pay?” | — | — | — | **refuse** | `PX-NO-PAY.` |

Quotes are the verbatim line from `policy-excerpt.md`. Never a payout amount. Never invent a rule id.

## Decision order (`python/decide.py` oracle)

1. Payout-family (`payout`, `settlement`, `how much`, `we will pay`, `pay(ment)`, `$` + digits, `dollars`, `usd`, `indemnif`, `reserve`) → `refuse` / `PX-NO-PAY`.
2. Medical / legal (`prescribe`, `dose`, `medicine`, `liable`, …) → `refuse` / `rule_id` null / `No rule line matched`.
3. Load report. Lookup `cover` in `load_policy()`. Unknown cover → no-match.
4. `PX-FLOOD` → `refuse` (flood before photos; CL-04 has photos and still refuses).
5. `photos` false → `hold` (CL-08). Collision is hold-only; do not invent open-collision.
6. `PX-GLASS` and photos true → `open`.
7. Else no-match.

Chat, website, tests, and Bot must match this engine. UI contains no rules.

## Done-when (track + judges)

- CL-03 → open, quote `PX-GLASS`.
- CL-04 → refuse, quote `PX-FLOOD`.
- No response states a payout.
- Must-show on the laptop: inspect, `AGENTS.md`, plan, skill, hook, MCP `lookup_rule`, rerunnable script, test.
- Live demo: pass then refuse, then point at surfaces + Intake Clerk, then stop.
- Live-ops: who clicks (`POST /api/confirm`), undo, log with **no amounts**.

## Already done

- [x] Kit downloaded to repo root (`fnol.json`, `policy-excerpt.md`, `rules_mcp.py`)
- [x] `grok mcp add --scope project rules -- python3 rules_mcp.py`
- [x] HLD/LLD (`design.html`) reviewed to 0 open issues
- [x] This plan

## Clock rule

PR-1 first (engine + tests). After PR-1, if time is short prefer **PR-3 (website live-ops)** over plugin polish. Plugin is optional on the track page; confirm/undo/log is on the scorecard. Target remains all five PRs.

## PR Plan

Same-day slices. Each PR is independently reviewable. Do not start engine code before inspect notes exist in `lab-plan.md`.

### PR 1: feat(engine): CL-03 open, CL-04 refuse, quotes from policy-excerpt.md

- Files/components affected: lab-plan.md, SDD/constitution.md, python/__init__.py, python/decide.py, python/test_desk.py, bin/run.sh, .gitignore
- Dependencies: None
- Description: Inspect kit in place (do not copy, do not invent ClaimDesk/). Record findings in lab-plan.md §1. Constitution principles adapted from DeskAgent for FNOL. Implement cover-id `decide_report` in python/decide.py (stdlib only). Labels open / hold / refuse. Lock CL-03 open/PX-GLASS, CL-04 refuse/PX-FLOOD, CL-08 hold/PX-COLLISION, payout ask including “will we pay” → PX-NO-PAY, no-payout scan on engine output (quoted kit lines may contain the word payout as a prohibition), quotes substring of policy-excerpt.md. Do not move or rewrite kit JSON/MD bodies. Do not relocate rules_mcp.py in this PR. Merge bar: `python3 -m unittest python.test_desk` green and `python3 python/decide.py CL-04` prints refuse.

### PR 2: feat(grok): review-fnol skill, protect-rules hook, pin MCP, fnol-desk plugin

- Files/components affected: AGENTS.md, lab-plan.md, rules_mcp.py, python/rules_mcp.py, python/protect_rules.py, .grok/config.toml, .grok/skills/review-fnol/SKILL.md, .grok/hooks/protect-rules.json, .grok/plugins/fnol-desk/, bin/run.sh
- Dependencies: PR 1
- Description: Pin RULE_FILE to policy-excerpt.md. Add python/rules_mcp.py with DeskAgent parent-walk (HERE.name == python) plus the pin; replace root rules_mcp.py with a runpy shim so the already-registered workshop command `python3 rules_mcp.py` still works. Keep .grok/config.toml args = ["rules_mcp.py"]. Do not re-run grok mcp add unless config changes. AGENTS.md: only policy-excerpt.md, call lookup_rule, never a payout. Skill /review-fnol. Hook denies edits to policy-excerpt.md and creation of extra *rules.md / payer_rules.md. Plugin packs skill+hook+MCP (thin is fine). bin/run.sh mcp smokes lookup flood → line starting PX-FLOOD and made-up miss. Merge bar: both `python3 rules_mcp.py` and `python3 python/rules_mcp.py` return a PX-FLOOD line; hook dry-run denies a policy edit.

### PR 3: feat(web): FNOL desk UI on serve_desk.py with confirm-before-send

- Files/components affected: python/serve_desk.py, python/display.json, python/test_serve.py, web/index.html, web/desk.js, web/desk.css, bin/desk.sh, bin/start-web.sh, var/.gitkeep, .gitignore
- Dependencies: PR 1
- Description: Original FNOL chrome (do not copy Alder or workshop demo HTML). GET /api/queue is read-only. ensure_state() materializes var/desk_state.json { id: { send_state, claim_number, refuse_logged } } and logs refuse once (not on GET). POST /api/confirm mints FNOL-{id}-{YYYYMMDDTHHMMSSZ} on open only; CL-04 confirm is 400 { "error": "refuse is not sent" }; undo restores draft; can_confirm / can_undo on queue items; POST /api/ask three-way (payout / medical-legal / Off-desk); GET /api/log and /api/health. Log JSONL has no amount/payout/$ keys. Bind 127.0.0.1:8788. Tests use CLAIMDESK_VAR temp dir. Merge bar: `python3 -m unittest python.test_desk python.test_serve`; CL-03 confirm then undo; CL-04 confirm 400.

### PR 4: feat(bot): Intake Clerk brief, Auto Review deny-list, bin/demo.sh

- Files/components affected: README.md, AGENTS.md, bin/demo.sh, lab-plan.md
- Dependencies: PR 1
- Description: Document paste-ready Intake Clerk brief. Bot does not mint and does not write var/. Laptop POST /api/confirm is the only mint. Auto Review blocks send, spend, delete, payout language, invented rules. bin/demo.sh prints CL-03, CL-04, payout refuse, unittest, MCP hit+miss. No second engine. Merge bar: `bin/demo.sh` exits 0 with CL-04 refuse and PX-FLOOD in the MCP hit.

### PR 5: docs: c4 twin, lab-report, SDD spec pack, README laptop map

- Files/components affected: docs/c4.html, docs/lab-report.html, SDD/spec.md, SDD/plan.md, SDD/tasks.md, SDD/data-model.md, SDD/contracts/decision.md, SDD/quickstart.md, SDD/research.md, SDD/checklists/requirements.md, README.md
- Dependencies: PR 1, PR 2, PR 3, PR 4
- Description: Copy design.html to docs/c4.html once the code matches. Lab-report checklist with evidence paths. SDD pack from DeskAgent shape. README laptop map: inspect, AGENTS.md, plan, skill, hook, MCP, script, test, website, Bot. Quickstart: run → test → MCP → desk.sh → Bot. Docs do not replace the live demo.

## Task checklist (DeskAgent-shaped)

### Phase 0 — already done

- [x] T000 Kit files at repo root; MCP `rules` registered to `python3 rules_mcp.py`

### Phase 1 — Setup (PR 1)

- [ ] T001 Inspect `fnol.json`, `policy-excerpt.md`, `rules_mcp.py` and record findings in `lab-plan.md` §1 (do not rewrite kit bodies)
- [ ] T002 Write `SDD/constitution.md` (kit-only rules, quote the file, golden cases, no payout, inspect-before-write, oracle script, honest Grok surfaces)
- [ ] T003 `python/__init__.py`, `.gitignore` (`var/*.jsonl`, `var/desk_state.json`, keep `var/.gitkeep` later)

### Phase 2 — Engine (PR 1)

- [ ] T004 Parse `policy-excerpt.md` (`^(PX-[A-Z-]+)\.\s+(.*)$`) in `python/decide.py`
- [ ] T005 Load `fnol.json`; require keys `id, peril, photos, cover`; no aliases
- [ ] T006 Decision order: off-scope → flood → photos false → glass → no-match
- [ ] T007 `bin/run.sh` (`all`, `CL-03`, `CL-04`, `CL-08`, `advice`, `test`)

### Phase 3 — Golden tests (PR 1)

- [ ] T008 CL-03 → open / PX-GLASS; quote in file
- [ ] T009 CL-04 → refuse / PX-FLOOD; photos true still refuse
- [ ] T010 CL-08 → hold / PX-COLLISION; no open-collision path
- [ ] T011 Payout ask including “will we pay” → refuse / PX-NO-PAY; output has no `$` / settlement amount
- [ ] T012 Merge bar: `python3 -m unittest python.test_desk` and `python3 python/decide.py CL-04`

### Phase 4 — Grok surfaces (PR 2)

- [ ] T013 Pin MCP `RULE_FILE` to `policy-excerpt.md`; parent-walk under `python/`; root shim; keep config `args = ["rules_mcp.py"]`
- [ ] T014 `AGENTS.md` + `.grok/skills/review-fnol/SKILL.md` (`/review-fnol`); must call `lookup_rule`
- [ ] T015 Hook `python/protect_rules.py` + `.grok/hooks/protect-rules.json` (protect `policy-excerpt.md`; block extra rule books)
- [ ] T016 Plugin `.grok/plugins/fnol-desk/` (skill + hook + MCP). Thin is fine.
- [ ] T017 `bin/run.sh mcp` — hit `flood` starts with `PX-FLOOD`; miss `made-up-rule`

### Phase 5 — Website live-ops (PR 3)

- [ ] T018 `python/serve_desk.py` — `/api/queue` (read-only), `/api/ask`, `/api/confirm`, `/api/undo`, `/api/log`, `/api/health`
- [ ] T019 `ensure_state`, confirm mint, CL-04 400, undo, log no amounts, `CLAIMDESK_VAR`
- [ ] T020 Original `web/` UI calling those APIs; no rules in JS
- [ ] T021 `bin/desk.sh` / `bin/start-web.sh` on `127.0.0.1:8788` (kill old listener first)
- [ ] T022 `python/test_serve.py`

### Phase 6 — Bot + demo (PR 4)

- [ ] T023 Intake Clerk brief in README (no mint, no `var/` writes)
- [ ] T024 `bin/demo.sh` full walkthrough

### Phase 7 — Docs (PR 5)

- [ ] T025 `docs/c4.html`, `docs/lab-report.html`, SDD pack, README laptop map

## Demo script (after merge)

1. One sentence: “Claim intake. Open, hold, or refuse against the policy excerpt. Never a payout. A Grok Bot keeps the queue after we close the laptop.”
2. CL-03 → open. Quote PX-GLASS. Confirm click.
3. CL-04 → refuse. Quote PX-FLOOD. Confirm is refused.
4. Point at AGENTS.md, skill, hook, MCP `lookup_rule`, Intake Clerk (wait-for-yes, never mint).
5. Stop.

## Paste-ready Bot brief

```
Name: Intake Clerk
Title: Claim intake night watch
Description: Re-run the claim-intake script on fnol.json. The only rule source is policy-excerpt.md via lookup_rule. For each report return open, hold for photos, or refuse, and quote the policy line. Never state a payout or settlement amount. Never give medical or legal advice. CL-03 glass stays open and waits for the clerk to click before a claim number exists. CL-04 flood stays refused and is logged on the laptop, not sent. Hold for photos waits for the clerk. Off-scope questions are refused. Notes on the Bot if needed; never write ClaimDesk/var/ or Hackathon/var/; never mint FNOL-…. If anything would send, spend, delete, or name money, stop and ask for a yes.
```

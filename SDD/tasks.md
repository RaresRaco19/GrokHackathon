# Tasks: Claim Intake Desk (FNOL)

**Input**: [plan.md](./plan.md), [spec.md](./spec.md), [data-model.md](./data-model.md), [contracts/decision.md](./contracts/decision.md)
**Prerequisites**: kit files already in the repo (`data/fnol.json`, `md/policy-excerpt.md`, `python/rules_mcp.py`)

Tests are included because the lab finish line requires them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no incomplete dependency)
- **[USn]**: user story from spec.md

## Phase 0: Kit already on disk

- [x] T000 Layout: `data/fnol.json`, `md/policy-excerpt.md`, `python/rules_mcp.py`; MCP `python3 python/rules_mcp.py`

## Phase 1: Setup (PR 1)

- [x] T001 Inspect kit files and record findings in `lab-plan.md` §1 (do not rewrite kit bodies)
- [x] T002 [P] Write standing Grok rules in `AGENTS.md` (later PR 2 completed the Grok-facing copy)
- [x] T003 [P] Write `SDD/constitution.md`

## Phase 2: Foundational engine (PR 1)

- [x] T004 Parse `md/policy-excerpt.md` (`^(PX-[A-Z-]+)\.\s+(.*)$`) in `python/decide.py`
- [x] T005 Load `data/fnol.json`; require keys `id, peril, photos, cover`; no aliases
- [x] T006 Decision order: off-scope → flood → photos false → glass → no-match
- [x] T007 `bin/run.sh` (`all`, `CL-03`, `CL-04`, `CL-08`, `advice`, `test`, `mcp`)

## Phase 3: User Story 1 — Glass open (P1)

**Goal**: CL-03 open citing PX-GLASS
**Independent test**: `python3 python/decide.py CL-03` → open / PX-GLASS

- [x] T008 [US1] Implement glass + photos path (PX-GLASS) in `python/decide.py`
- [x] T009 [P] [US1] Add CL-03 golden assertion in `python/test_desk.py`

## Phase 4: User Story 2 — Flood refuse (P1)

**Goal**: CL-04 refuse citing PX-FLOOD even with photos true
**Independent test**: `python3 python/decide.py CL-04` → refuse / PX-FLOOD

- [x] T010 [US2] Evaluate PX-FLOOD before photos in `python/decide.py`
- [x] T011 [P] [US2] Add CL-04 plus photos-true-still-refuse tests in `python/test_desk.py`

## Phase 5: User Story 3 — Collision hold (P1)

**Goal**: CL-08 hold citing PX-COLLISION; no open-collision path
**Independent test**: `python3 python/decide.py CL-08` → hold / PX-COLLISION

- [x] T012 [US3] Implement photos-false hold in `python/decide.py`
- [x] T013 [P] [US3] Add CL-08 plus no-open-collision tests in `python/test_desk.py`

## Phase 6: User Story 4 — Payout / medical-legal (P1)

**Goal**: Refuse payout with PX-NO-PAY; medical/legal with no rule id
**Independent test**: `python3 python/decide.py --advice "will we pay?"`

- [x] T014 [US4] Implement payout and medical/legal refusal in `python/decide.py`
- [x] T015 [P] [US4] Add payout, no-promised-amount, and medical-legal tests in `python/test_desk.py`

## Phase 7: Grok surfaces (PR 2)

- [x] T016 MCP is `python/rules_mcp.py` (parent-walk + pin `md/policy-excerpt.md`); config `args = ["python/rules_mcp.py"]`. No root shim.
- [x] T017 [US1] `AGENTS.md` + `.grok/skills/review-fnol/SKILL.md` (`/review-fnol`); must call `lookup_rule`
- [x] T018 Hook `python/protect_rules.py` + `.grok/hooks/protect-rules.json` (protect `md/policy-excerpt.md`; block extra rule books)
- [x] T019 Plugin `.grok/plugins/fnol-desk/` (skill + hook + MCP)
- [x] T020 `bin/run.sh mcp` — hit `flood` starts with `PX-FLOOD`; miss `made-up-rule`

## Phase 8: User Story 5 — Website live-ops (PR 3)

**Goal**: Clerk uses a local page that invokes `decide.py`; confirm-before-send; refuse not sent.
**Independent test**: `bin/desk.sh` then `/api/queue` matches `python3 python/decide.py --json`

- [x] T021 [US5] Reverse-engineer FNOL chrome into `web/` (HTML/CSS/JS only; no rules)
- [x] T022 [P] [US5] Add `python/serve_desk.py` (`/api/queue` read-only, `/api/ask`, `/api/confirm`, `/api/undo`, `/api/log`, `/api/health`)
- [x] T023 [US5] `ensure_state`, confirm mint, CL-04 400, undo, log no amounts, `CLAIMDESK_VAR`
- [x] T024 `bin/desk.sh` / `bin/start-web.sh` on `127.0.0.1:8788` (kill old listener first)
- [x] T025 `python/test_serve.py`

## Phase 9: User Story 6 — Bot + demo (PR 4)

- [x] T026 [US6] Intake Clerk brief in README (no mint, no `var/` writes); Auto Review deny-list
- [x] T027 `bin/demo.sh` full walkthrough (CL-03, CL-04, payout refuse, unittest, MCP hit+miss)

## Phase 10: Docs (PR 5)

- [x] T028 Copy `docs/design.html` to `docs/c4.html` once paths match the live kit
- [x] T029 [P] Write `docs/lab-report.html` with evidence paths
- [x] T030 [P] Write remaining SDD pack (spec, plan, tasks, data-model, contracts, research, quickstart, checklist)
- [x] T031 README laptop map: inspect, AGENTS.md, plan, skill, hook, MCP, script, test, website, Bot

## Dependencies

- Phase 0 before 1. Phase 1 before 2. Phase 2 before stories 1–4.
- Stories 1–4 are independently testable; implementation order 1 → 2 → 3 because flood must precede photos, then glass, then advice.
- Plugin (T019) after skill and hook exist.
- Website (phase 8) after the oracle exists; parallel to Grok surfaces.
- Bot (phase 9) after the oracle exists.
- Docs (phase 10) after PR 1–4 so evidence paths are real.

## Parallel example

```text
T002 + T003 together after T001
T009 with T008
T011 with T010
T013 with T012
T015 with T014
T017 + T018 after T016
T022 with T021
T029 + T030 + T031 after T028
```

## Implementation strategy

MVP is T000–T015: three reports match the track. Then Grok surfaces, website live-ops, Bot, then docs.

Suggested MVP: User Stories 1–3 (the three reports). Story 4 is still a lab finish-line item and ships in the same engine pass.

## Task summary

- Total: 32
- Kit: 1
- Setup: 3
- Foundational: 4
- US1: 2
- US2: 2
- US3: 2
- US4: 2
- Grok surfaces: 5
- Website UI + backend: 5
- Bot + demo: 2
- Docs: 4
- Parallel opportunities: T002/T003, story test tasks, T017/T018, T021/T022, T029/T030/T031

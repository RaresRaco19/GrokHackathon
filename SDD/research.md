# Research: Reverse-Engineering the Claim Intake Desk

## Decision: rebuild from kit files, do not copy demo HTML

**Rationale**: the module page says copying the demo HTML fails the lab. The kit is reports plus one policy excerpt plus an MCP stub.

**Alternatives considered**: screenshot-faithful web clone; iframe the demo; copy Alder Health chrome. All fail the lab.

## Decision: implement in place, do not create ClaimDesk/

Kit already lives at `data/fnol.json`, `md/policy-excerpt.md`, `python/rules_mcp.py`. A second product folder would copy kit files and mix inspect with a move.

**Rationale**: constitution V; `md/PLAN.md` supersedes an earlier ClaimDesk/ sketch.

**Alternatives considered**: copy kit into `ClaimDesk/` for a clean inspect folder. Rejected — kit was already here.

## Decision: golden outcomes from the kit + track page

| id | Decision | Kit flags | Cited |
|----|----------|-----------|-------|
| CL-03 | open | glass, photos true, PX-GLASS | PX-GLASS |
| CL-04 | refuse | flood, photos true, PX-FLOOD | PX-FLOOD (scoring case) |
| CL-08 | hold | collision, photos false, PX-COLLISION | PX-COLLISION |
| Ask box | refuse | payout / “will we pay?” | PX-NO-PAY |

**Rationale**: lab says inspect first, write that down, then rebuild. Cover ids in the JSON already determine the labels.

**Alternatives considered**: guess CL-04 from photos true (would open). Rejected — flood exclusion wins.

## Decision: ignore demo-only chrome

Claimant names, vehicles, member ids, and payout amounts are not in the kit. The rebuild does not invent them.

**Rationale**: constitution V; invented fields look like copied HTML.

**Alternatives considered**: hard-code demo names for showmanship. Rejected.

## Decision: flood outranks photos

CL-04 has `photos: true`. Track still refuse. Evaluate PX-FLOOD before the photos-false hold branch.

**Rationale**: otherwise a flood case with photos would open.

**Alternatives considered**: require photos false to refuse flood. Rejected — the cover id is the trigger.

## Decision: collision is hold-only

CL-08 photos false → hold. A synthetic collision with photos true must not open (no PX-GLASS path). Do not invent open-collision.

**Rationale**: kit has no open-collision report. Track wording is “Need photos”.

## Decision: Python stdlib script as the oracle

`python/decide.py` is the repeatable surface. Tests call it. Chat is instructed to match it after `lookup_rule`.

**Rationale**: lab requires a script you can run again and a test. No third-party packages on workshop wifi.

**Alternatives considered**: LLM-only decisions with no script (not repeatable). A public hosted app is out of scope; the local desk is `web/` via `bin/desk.sh`.

## Decision: website UI invokes the Python backend

`python/serve_desk.py` is the backend. `web/desk.js` only fetches. Both paths call `python/decide.py` against the kit files.

**Rationale**: one engine for CLI, tests, and UI. Confirm-before-send is live-ops, not a second rule book.

**Alternatives considered**: keep a JS clone of the rules (looks like the demo, lies about the source of truth); iframe the workshop URL (not a rebuild).

## Decision: no root MCP shim

Register `rules` via `.grok/config.toml` / `grok mcp add --scope project rules -- python3 python/rules_mcp.py`. The stub already parent-walks and pins `md/policy-excerpt.md`.

**Rationale**: a root `rules_mcp.py` with `ROOT = HERE` would miss `md/policy-excerpt.md` if copied under `python/` unchanged. All Python lives under `python/`.

**Alternatives considered**: root shim for the grey-box workshop command. Rejected in `md/PLAN.md`.

## Decision: hook protects the rule book

PreToolUse denies edits to `md/policy-excerpt.md` and creation of another `*rules.md` / `payer_rules.md`.

**Rationale**: "a hook: check that runs before Grok Build does something" and "made-up rules fail the lab."

**Alternatives considered**: SessionStart echo only (too weak); Stop-gate that re-runs tests (nice extra, not required).

## Decision: Bot is a briefed teammate, not a second engine

Intake Clerk re-states the same path. It does not mint `FNOL-…` and does not write `var/`. Laptop `POST /api/confirm` is the only mint.

**Rationale**: Bot is a plus. Grok Build must-show still lives on the laptop.

**Alternatives considered**: Grok Bot as the only runtime. Fails laptop Grok Build checkboxes.

## Decision: docs do not replace the live demo

C4 twin, lab-report, and SDD pack point at evidence paths. Judges score what they can see run.

**Rationale**: `md/judging.md` — each table is a live demo.

**Alternatives considered**: walk HTML instead of `bin/demo.sh`. Rejected.

# Lab plan — Claim intake (FNOL)

Source: Grok Enablement Workshop, Module 4.3
Working track: open / hold / refuse against `md/policy-excerpt.md`. Never a payout.

This file is the agreed plan. Kit data files already on disk stay untouched. New files follow the layout in §5.

## 1. Inspect (what is already here)

Looked at this folder before writing engine code. The kit is reports + one policy excerpt + an MCP stub. No demo source. No claimant names.

| File | Role |
|------|------|
| `data/fnol.json` | The three FNOL reports |
| `md/policy-excerpt.md` | The only source of rules |
| `python/rules_mcp.py` | Local MCP stub: `list_rules` and `lookup_rule` (pins `md/policy-excerpt.md`) |
| `python/__init__.py` | Package marker; all Python lives under `python/` |
| `docs/` | HTML briefing (design, plan, scoring) |
| `md/PLAN.md` | Executable PR DAG |
| `md/judging.md` | Judge live-demo notes |

`data/fnol.json` is an array of `{id, peril, photos, cover}` — no aliases:

| id | peril | photos | cover |
|----|--------|--------|--------|
| CL-03 | glass | true | PX-GLASS |
| CL-04 | flood | true | PX-FLOOD |
| CL-08 | collision | false | PX-COLLISION |

`md/policy-excerpt.md` heading is `# Policy excerpt`. Parsed lines (`^(PX-[A-Z-]+)\.\s+(.*)$`):

- `PX-GLASS. Glass breakage is in force when photos are on the file. Accept for intake. Do not promise a payout.`
- `PX-FLOOD. Flood is excluded. Return Refuse and quote this rule.`
- `PX-COLLISION. Collision needs photos. If photos are missing, return Need photos.`
- `PX-NO-PAY. Never write “we will pay” or name a settlement amount.`

Do not edit those bodies. Do not invent a second rule file. Made-up rules fail the lab.

Decision order from the kit + track (cover-id lookup, not token scan):

1. Payout-family ask (`payout`, `settlement`, `how much`, `we will pay`, `pay(ment)`, `$` + digits, `dollars`, `usd`, `indemnif`, `reserve`) → refuse / PX-NO-PAY.
2. Medical / legal (`prescribe`, `dose`, `medicine`, `liable`, …) → refuse / `rule_id` null / `No rule line matched.`
3. Load the report. Require keys `id`, `peril`, `photos`, `cover`. Lookup `cover` in `load_policy()`. Unknown cover → no-match.
4. `PX-FLOOD` → refuse (flood before photos; CL-04 has photos and still refuses).
5. `photos` false → hold (CL-08). Collision is hold-only; do not invent open-collision.
6. `PX-GLASS` and photos true → open (CL-03).
7. Else no-match.

JSON `decision` is `open` | `hold` | `refuse`. Clerk view may display hold as `hold for photos`. Quotes are the verbatim line from the excerpt. The word `payout` may appear in a quoted prohibition; never a `$` amount or promised settlement number.

## 2. Golden cases (from kit, not invented)

| Id | Decision | Cited |
|----|----------|-------|
| **CL-03** | **open** | `PX-GLASS` |
| **CL-04** | **refuse** (scoring case; log not send) | `PX-FLOOD` |
| CL-08 | **hold** | `PX-COLLISION` |
| ask “will we pay?” | **refuse** | `PX-NO-PAY` |

### Extra chrome we will not invent

No claimant names, vehicles, or payout amounts in the kit. The rebuild uses only kit data. Do not copy Alder / PA demo HTML.

## 3. Done when (track finish line)

1. CL-03 → open, quote `PX-GLASS`
2. CL-04 → refuse, quote `PX-FLOOD` (photos true does not override)
3. No response states a payout amount
4. Laptop can show the must-show list

Must show (later PRs complete the Grok / website / Bot surfaces):

- **inspect** — look at the folder before writing files (this section)
- **AGENTS.md** — short rules file for Grok Build
- **plan** — this file and `md/PLAN.md`, agreed before the rest is written
- **a skill** — how Grok reviews a report
- **a hook** — check before Grok edits the policy excerpt
- **MCP `lookup_rule`** — `python/rules_mcp.py` already registered
- **a plugin** — skill + hook + MCP packed together
- **a script you can run again** — `python/decide.py`
- **a test** — the three reports still decide the same way

## 4. How the rebuilt desk decides

Single path. Rules are loaded from `md/policy-excerpt.md`. No other rule source. `python/decide.py` is the oracle.

Same order as §1. Quote text is the matching line from the excerpt, not a paraphrase. If no line matches, say `No rule line matched.` Do not mint a substitute rule id.

Grok Build, when a clerk asks in chat, follows the same path: call MCP `lookup_rule`, then apply this order. The Python script is the repeatable, testable copy of that path.

The local website (later PR) uses that same path. The UI does not decide.

## 5. Files this plan generates

Kit files listed in §1 are not regenerated.

| Path | Why |
|------|-----|
| `lab-plan.md` | This plan |
| `SDD/constitution.md` | Standing non-negotiables (FNOL, not PA) |
| `python/decide.py` | Repeatable decision script |
| `python/test_desk.py` | Golden tests for the three reports + payout ask |
| `bin/run.sh` | Case runner: all, CL-03, CL-04, CL-08, advice, test |
| `.gitignore` | `__pycache__`, `.DS_Store`, `var/*.jsonl`, `var/desk_state.json` |

Later PRs (not this slice): AGENTS.md, skill, hook, plugin, website, Bot brief, remaining SDD pack.

## 6. Spec-driven pack (SDD)

| Artifact | Contents |
|----------|----------|
| `SDD/constitution.md` | Kit-only rules, quote the file, golden cases, no payout, inspect-before-write, oracle script, honest Grok surfaces |

Remaining SDD files come in a later docs PR.

## 7. Work order

1. Inspect kit and write this plan (this file, §1)
2. Constitution
3. Decision script + golden tests + `bin/run.sh`
4. Grok surfaces (skill, hook, plugin)
5. Website confirm / undo / log
6. Bot + demo script
7. Docs / laptop map

## 8. Out of scope

- Rewriting `data/fnol.json` or `md/policy-excerpt.md` bodies
- A root `rules_mcp.py` shim (MCP already lives under `python/`)
- Copying Alder patient names or PA demo HTML
- Inventing an open-collision path
- Stating a payout or settlement amount
- A public hosted web app

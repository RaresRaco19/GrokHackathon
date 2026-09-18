# Quickstart: prove the desk

Docs do not replace the live demo. Run these steps on the laptop, then point at the files.

## Prerequisites

- Python 3
- Kit data in this repo (`data/fnol.json`, `md/policy-excerpt.md`)
- All Python under `python/` (`decide.py`, `serve_desk.py`, `rules_mcp.py`, `protect_rules.py`, `test_desk.py`, `test_serve.py`)
- Grok Build, for the MCP / skill / hook / Bot demo

## 1. Run

```bash
python3 python/decide.py
python3 python/decide.py CL-03
python3 python/decide.py CL-04
python3 python/decide.py CL-08
python3 python/decide.py --advice "will we pay?"
bin/run.sh
bin/demo.sh
```

Expected labels: **open**, **refuse**, **hold for photos**, then the payout refusal.

| Case | Decision | Cited |
|------|----------|-------|
| CL-03 | open | PX-GLASS |
| CL-04 | refuse | PX-FLOOD |
| CL-08 | hold for photos | PX-COLLISION |
| will we pay? | refuse | PX-NO-PAY |

## 2. Test

```bash
python3 -m unittest python.test_desk python.test_serve
```

All tests pass (30). This is the lab "test" checkbox. `python.test_serve` checks that the website API uses `decide.py`, that CL-03 confirm-then-undo works, and that CL-04 confirm is 400.

## 3. MCP

From this folder:

```bash
grok mcp add --scope project rules -- python3 python/rules_mcp.py
```

If Grok asks to trust the folder, say yes (`/hooks-trust` or launch with `--trust`). Until the folder is trusted, project AGENTS.md, project hooks, project skills, and the fnol-desk plugin stay inactive. Smoke the stub:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"lookup_rule","arguments":{"query":"flood"}}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"lookup_rule","arguments":{"query":"made-up-rule"}}}' \
  | python3 python/rules_mcp.py
```

The flood result must start with `PX-FLOOD`. The made-up query must return `No rule line matched 'made-up-rule'.`

Or: `bin/run.sh mcp`

## 4. desk.sh (local website)

```bash
bin/desk.sh
```

Opens http://127.0.0.1:8788/

The page is UI only. The backend is `python/serve_desk.py`:

| Browser | Backend | Engine |
|---------|---------|--------|
| load / click queue | `GET /api/queue` | `decide.py` + `data/fnol.json` + `md/policy-excerpt.md` |
| Send to desk | `POST /api/ask` | `decide.py` (PX-NO-PAY if payout) |
| Confirm | `POST /api/confirm` | mint on open only; CL-04 → 400 |
| Undo | `POST /api/undo` | back to draft |

Expected: CL-03 open, CL-04 refuse, CL-08 hold for photos, “will we pay?” refuse. Same labels as step 1.

In chat: `/review-fnol` CL-03, CL-04, CL-08, then ask for a payout. Outcomes must match step 1 and the website.

## 5. Bot

Paste the Intake Clerk brief from `README.md` into a Grok Bot.

- Wait-for-yes.
- Does not mint `FNOL-…`.
- Does not write `var/`.
- Laptop `POST /api/confirm` is the only mint.
- Auto Review deny-list: send, spend, delete, payout language, invented rules.

CL-03 stays open until the clerk clicks. CL-04 stays refused and is logged on the laptop, not sent.

## Laptop map (must-show)

| Checkbox | Path |
|----------|------|
| inspect | `lab-plan.md` §1 |
| AGENTS.md | `AGENTS.md` |
| plan | `lab-plan.md`, `md/PLAN.md` |
| skill | `.grok/skills/review-fnol/SKILL.md` (`/review-fnol`) |
| hook | `.grok/hooks/protect-rules.json` → `python/protect_rules.py` |
| MCP | `python/rules_mcp.py` + `.grok/config.toml` |
| script | `python/decide.py` / `bin/run.sh` / `bin/demo.sh` |
| test | `python/test_desk.py` + `python/test_serve.py` |
| website | `bin/desk.sh` → http://127.0.0.1:8788/ |
| Bot | Intake Clerk brief in `README.md` |

## Spec pack

`SDD/spec.md` is the product spec. `SDD/tasks.md` is the work list. Constitution: `SDD/constitution.md`. C4 twin: `docs/c4.html`. Lab-report: `docs/lab-report.html`.

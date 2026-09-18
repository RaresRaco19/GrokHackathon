# GrokHackathon

Workshop track **4.3 Claim intake**. A clerk opens a damage report. The desk reads `md/policy-excerpt.md`, returns open / hold for photos / refuse, quotes the file, and never states a payout.

Docs (`docs/c4.html`, `docs/lab-report.html`, `SDD/`) do not replace the live demo. Run the script, then point.

## Laptop map

| Checkbox | Path |
|----------|------|
| inspect | [`lab-plan.md`](lab-plan.md) §1 |
| AGENTS.md | [`AGENTS.md`](AGENTS.md) |
| plan | [`lab-plan.md`](lab-plan.md), [`md/PLAN.md`](md/PLAN.md) |
| skill | [`.grok/skills/review-fnol/SKILL.md`](.grok/skills/review-fnol/SKILL.md) — `/review-fnol` |
| hook | [`.grok/hooks/protect-rules.json`](.grok/hooks/protect-rules.json) → [`python/protect_rules.py`](python/protect_rules.py) |
| MCP | [`python/rules_mcp.py`](python/rules_mcp.py) + [`.grok/config.toml`](.grok/config.toml) |
| script | [`python/decide.py`](python/decide.py) / [`bin/run.sh`](bin/run.sh) / [`bin/demo.sh`](bin/demo.sh) |
| test | [`python/test_desk.py`](python/test_desk.py) + [`python/test_serve.py`](python/test_serve.py) |
| website | [`bin/desk.sh`](bin/desk.sh) → http://127.0.0.1:8788/ |
| Bot | Intake Clerk brief below |

C4 twin: [`docs/c4.html`](docs/c4.html). Lab-report with evidence paths: [`docs/lab-report.html`](docs/lab-report.html). Prove-the-desk: [`SDD/quickstart.md`](SDD/quickstart.md).

## Kit (do not rewrite)

| File | Role |
|------|------|
| `data/fnol.json` | Three FNOL reports |
| `md/policy-excerpt.md` | The only rule book |
| `python/rules_mcp.py` | Local MCP stub: `list_rules` and `lookup_rule` |

Python lives under `python/`. Port **8788**.

| Id | Decision | Cited |
|----|----------|-------|
| CL-03 | open | PX-GLASS |
| CL-04 | refuse (scoring; log not send) | PX-FLOOD |
| CL-08 | hold for photos | PX-COLLISION |
| “will we pay?” | refuse | PX-NO-PAY |

## Quickstart

Run → test → MCP → desk.sh → Bot.

```bash
python3 python/decide.py
python3 python/decide.py CL-04
python3 python/decide.py --advice "will we pay?"

python3 -m unittest python.test_desk python.test_serve

grok mcp add --scope project rules -- python3 python/rules_mcp.py
bin/run.sh mcp

bin/desk.sh          # http://127.0.0.1:8788/
bin/demo.sh          # engine + tests + MCP; website not required
```

MCP: `grok mcp add --scope project rules -- python3 python/rules_mcp.py`

Open [`docs/plan.html`](docs/plan.html). Execute: `/execute-plan md/PLAN.md`

## Intake Clerk — paste into Grok Bot

```
Name: Intake Clerk
Title: Claim intake night watch
Description: Re-run the claim-intake script on data/fnol.json. The only rule source is md/policy-excerpt.md via lookup_rule. For each report return open, hold for photos, or refuse, and quote the policy line. Never state a payout or settlement amount. Never give medical or legal advice. CL-03 glass stays open and waits for the clerk to click before a claim number exists. CL-04 flood stays refused and is logged on the laptop, not sent. Hold for photos waits for the clerk. Off-scope questions are refused. Notes on the Bot if needed; never write GrokHackathon/var/; never mint FNOL-…. If anything would send, spend, delete, or name money, stop and ask for a yes.
```

The Bot does not mint and does not write `var/`. Laptop `POST /api/confirm` is the only mint.

Auto Review deny-list: send, spend, delete, payout language, invented rules.

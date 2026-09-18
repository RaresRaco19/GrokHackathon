# GrokHackathon

Workshop track **4.3 Claim intake**. Layout:

| Folder | Contents |
|--------|----------|
| `docs/` | HTML briefing: design, plan, scoring |
| `md/` | Markdown: `PLAN.md`, `policy-excerpt.md`, judging, README |
| `data/` | `fnol.json` (kit reports) |
| `python/` | All Python (`rules_mcp.py` now, then decide/serve/tests) |

Open `docs/plan.html`. Execute: `/execute-plan md/PLAN.md`

MCP: `grok mcp add --scope project rules -- python3 python/rules_mcp.py`

Laptop walkthrough (engine + tests + MCP; website not required):

    bin/demo.sh

## Intake Clerk — paste into Grok Bot

```
Name: Intake Clerk
Title: Claim intake night watch
Description: Re-run the claim-intake script on data/fnol.json. The only rule source is md/policy-excerpt.md via lookup_rule. For each report return open, hold for photos, or refuse, and quote the policy line. Never state a payout or settlement amount. Never give medical or legal advice. CL-03 glass stays open and waits for the clerk to click before a claim number exists. CL-04 flood stays refused and is logged on the laptop, not sent. Hold for photos waits for the clerk. Off-scope questions are refused. Notes on the Bot if needed; never write GrokHackathon/var/; never mint FNOL-…. If anything would send, spend, delete, or name money, stop and ask for a yes.
```

The Bot does not mint and does not write `var/`. Laptop `POST /api/confirm` is the only mint.

Auto Review deny-list: send, spend, delete, payout language, invented rules.

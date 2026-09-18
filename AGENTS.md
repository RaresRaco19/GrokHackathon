# Claim intake desk

This folder is an FNOL intake desk rebuilt from kit files. Grok Build follows these rules every session.

## Source of truth

- The only rule book is `md/policy-excerpt.md`.
- Report data is `data/fnol.json`.
- Never invent a rule, a rule id, or a quote. If `lookup_rule` returns no match, say so.
- Do not edit `md/policy-excerpt.md`.
- Never state a payout or settlement amount.

## How to decide

When a clerk opens a report or asks the desk:

1. Load the review-fnol skill.
2. Call MCP `lookup_rule` (server `rules`) against `md/policy-excerpt.md`. Do not skip this.
3. Apply the path in `lab-plan.md` §4. Same outcomes as the working desk:
   - CL-03 glass, photos true → open, cite PX-GLASS
   - CL-04 flood, photos true → refuse, cite PX-FLOOD
   - CL-08 collision, photos false → hold, cite PX-COLLISION
4. Quote the matching line from the rule file, including the rule id.

## Payout and off-scope

Payout-family ask → refuse. Cite PX-NO-PAY. Reply: "The desk does not state a payout."

Medical or legal advice → refuse. No rule id. Say `No rule line matched.` Reply: "The desk only decides intake coverage. It will not give medical or legal advice."

Do not write "we will pay" or name a settlement amount.

## Repeatable check

```
python3 python/decide.py
python3 -m unittest python.test_desk python.test_serve
bin/run.sh
bin/demo.sh
```

Decisions from chat must match that script.

## Website

The local site is not a second rule book. `bin/desk.sh` starts `python/serve_desk.py` on 127.0.0.1:8788. The UI only renders. Chat, CLI, and the website MUST match `python/decide.py`.

## Grok Bot

Intake Clerk re-runs that same path. It does not mint `FNOL-…` and does not write `var/`. Laptop `POST /api/confirm` is the only mint. Auto Review blocks send, spend, delete, payout language, and invented rules. If anything would send, spend, delete, or name money, stop and ask for a yes.

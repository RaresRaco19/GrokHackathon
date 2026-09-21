---
name: review-fnol
description: Review an FNOL claim-intake report against md/policy-excerpt.md. Use when a clerk opens CL-03, CL-04, or CL-08, asks the desk to decide intake, or asks for a payout. Slash command /review-fnol.
---

# Review an FNOL report

Decide intake: open, hold, or refuse. Never a payout. Do not invent rules.

## Inputs

- `data/fnol.json` — id, peril, photos, cover
- `md/policy-excerpt.md` — only rule book (read through MCP `lookup_rule`)

## Steps

1. If the user asks about a payout, settlement, how much, "we will pay", payment, dollars, USD, indemnify, or a reserve:
   - Call `lookup_rule` with query `PX-NO-PAY` (or `payout`).
   - Reply exactly: `The desk does not state a payout.`
   - Cite PX-NO-PAY. Stop.
2. If the user asks for medical or legal advice (prescribe, dose, medicine, liable, attorney):
   - Do not cite a coverage rule.
   - Reply: `The desk only decides intake coverage. It will not give medical or legal advice.`
   - Say `No rule line matched.` Stop.
3. Identify the report id (CL-03 / CL-04 / CL-08). Read that object in `data/fnol.json`.
4. Call MCP `lookup_rule` on the cover id and peril (`PX-GLASS`, `PX-FLOOD`, `PX-COLLISION`, `flood`, `glass`, `photos`). Use server `rules`. If the tool is missing, say the MCP is not registered and stop inventing text.
5. Decide in this order, quoting the **exact** matching line from the tool result:
   - Cover id is not in `md/policy-excerpt.md` → say `No rule line matched`. Do not mint a rule id.
   - Cover is PX-FLOOD → **refuse**, PX-FLOOD (photos true does not override)
   - Photos false → **hold** (display "hold for photos"), cite the cover id (CL-08 / PX-COLLISION)
   - Cover is PX-GLASS and photos true → **open**, PX-GLASS
   - Cover is PX-COLLISION and photos true → **open**, PX-COLLISION
   - No matching line → say `No rule line matched`. Do not mint a rule id.
6. Photos may be attached on CL-03, CL-04, and CL-08. The picture must match that report's peril (glass, flood, or collision). If it does not, do not change the case; say `do not match context!`
7. Answer with: decision, rule id, quoted line. Do not add claimant names, vehicles, or payout amounts.

## Checks

- Quote text must appear in `md/policy-excerpt.md`.
- Chat decisions must match `python3 python/decide.py <id>`.
- Never write "we will pay" or name a settlement amount.

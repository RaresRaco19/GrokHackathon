---
name: review-fnol
description: >
  Assess FNOL damage reports in fnol.json against the policy excerpt via the
  rules MCP. Use when reviewing claims, running /review-fnol, or deciding
  open / hold / refuse for an intake inquiry.
---

# /review-fnol

Follow `AGENTS.md`. Call `rules__lookup_rule` once per inquiry before you decide. Do not skip MCP. Do not invent a PX-* id. Do not name a payout.

## Steps

1. Read `fnol.json` (keys `id`, `peril`, `photos`, `cover` only).
2. For each report, call `rules__lookup_rule` with `query` set to `cover` (fallback: `peril`).
3. Emit the decision block from `AGENTS.md` (`open` / `hold` / `refuse` + verbatim quote).
4. If the user asked about paying, call `rules__lookup_rule` with `query` `PX-NO-PAY` and refuse.
5. Stop. Do not mint `FNOL-…`. Do not write `var/`.

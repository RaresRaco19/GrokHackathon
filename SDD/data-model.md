# Data Model: Claim Intake Desk (FNOL)

## Report

Source: `data/fnol.json`.

| Field | Type | Notes |
|-------|------|-------|
| id | string | `CL-03`, `CL-04`, `CL-08` |
| peril | string | Display (`glass`, `flood`, `collision`); not the matching key |
| photos | boolean | File checklist; false on CL-08 |
| cover | string | Matching key (`PX-GLASS`, `PX-FLOOD`, `PX-COLLISION`) |

Validation: required keys `id`, `peril`, `photos`, `cover`. No aliases. Unknown ids are errors, not invented reports.

## Rule

Source: `md/policy-excerpt.md`. One rule per line:

```
PX-<AREA>. <body>
```

Parsed with `^(PX-[A-Z-]+)\.\s+(.*)$`.

| id | body (summary) |
|----|----------------|
| PX-GLASS | Glass breakage in force when photos are on the file; accept for intake; do not promise a payout |
| PX-FLOOD | Flood is excluded; return Refuse and quote this rule |
| PX-COLLISION | Collision needs photos; if photos are missing, return Need photos |
| PX-NO-PAY | Never write “we will pay” or name a settlement amount |

Validation: ids and bodies MUST be parsed from the file. Tests MUST assert the quoted body is a substring of `md/policy-excerpt.md`.

## Decision

Produced by `python/decide.py`, by the review-fnol skill, and by the website backend (`python/serve_desk.py` calling `decide.py`).

| Field | Type | Allowed values |
|-------|------|----------------|
| decision | string | `open`, `hold`, `refuse` |
| rule_id | string or null | PX-GLASS, PX-FLOOD, PX-COLLISION, PX-NO-PAY, or null on no match |
| quoted | string | Verbatim `{id}. {body}` or `No rule line matched.` |
| source | string | Always `policy-excerpt.md` (basename) |
| id, peril, photos, cover | copied | Present on coverage decisions |
| message | string | Present on payout and medical/legal refusals |

Clerk view may display hold as `hold for photos`. Website JSON adds `label`, `send_state`, `claim_number`, `can_confirm`, `can_undo`.

## Send state (website only)

Source: `var/desk_state.json`, keyed by report id.

| Field | Type | Notes |
|-------|------|-------|
| send_state | string | `draft`, `sent`, `held` |
| claim_number | string or null | `FNOL-{id}-{YYYYMMDDTHHMMSSZ}` on open confirm only |
| refuse_logged | boolean | CL-04 logged once in `ensure_state()`, not on GET |

## Log event

Source: `var/intake-log.jsonl`.

| Field | Type | Notes |
|-------|------|-------|
| ts | string | utccompact `YYYYMMDDTHHMMSSZ` |
| id | string | Report id |
| decision | string | open / hold / refuse |
| quoted | string | Verbatim policy line |
| event | string | `confirm`, `undo`, `refuse` |
| claim_number | string | Optional; never an amount |

Forbidden keys: `amount`, `payout`, `$`. Quoted kit lines MAY contain the word payout as a prohibition.

## State transitions

```
open report
    → payout-family question      → refuse (PX-NO-PAY)
    → medical / legal question    → refuse (no rule id)
    → cover is PX-FLOOD           → refuse (PX-FLOOD)
    → photos false                → hold (cover line; CL-08)
    → cover is PX-GLASS + photos  → open (PX-GLASS)
    → no matching rule            → refuse (no rule id)

open + draft   → confirm → sent  + FNOL-…
hold + draft   → confirm → held  + no number
refuse         → confirm → 400 refuse is not sent
sent or held   → undo    → draft + number cleared
```

No open after PX-FLOOD or missing photos on the same report. Collision is hold-only when photos are false.

## Relationships

- Report 1–1 Decision (per run)
- Decision N–1 Rule (by rule_id), except the no-match path
- Report 1–1 Send state (website)
- Decision 0–N Log event

## Website display chrome (not a decision input)

Optional overlay from `python/display.json`, keyed by report id. Used only by the local UI. The engine never reads this file. Kit has no claimant names — do not invent them.

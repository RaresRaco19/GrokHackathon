# Contract: Decision record

The repeatable script is the contract surface. Chat MUST emit the same decision, rule id, and quote.

## Command

```
python3 python/decide.py                 # all three reports
python3 python/decide.py CL-03           # one report
python3 python/decide.py --advice TEXT   # payout / medical-legal / off-desk
python3 python/decide.py --json […]      # machine-readable
```

Exit 0 on success. Exit 1 if the report id is not in `data/fnol.json`.

## JSON object

```json
{
  "decision": "open",
  "rule_id": "PX-GLASS",
  "quoted": "PX-GLASS. Glass breakage is in force when photos are on the file. Accept for intake. Do not promise a payout.",
  "source": "policy-excerpt.md",
  "id": "CL-03",
  "peril": "glass",
  "photos": true,
  "cover": "PX-GLASS"
}
```

### Coverage decision

Required: `decision`, `rule_id`, `quoted`, `source`, `id`, `peril`, `photos`, `cover`.
`decision` is one of `open`, `hold`, `refuse`.
`quoted` MUST start with `rule_id` + `. ` unless `rule_id` is null.
Clerk view prints hold as `hold for photos`. Engine JSON keeps `decision: "hold"`.

### No matching rule

`decision` is `refuse`. `rule_id` is null. `quoted` is `No rule line matched.`

### Payout-family refusal

```json
{
  "decision": "refuse",
  "rule_id": "PX-NO-PAY",
  "quoted": "PX-NO-PAY. Never write “we will pay” or name a settlement amount.",
  "source": "policy-excerpt.md",
  "message": "The desk does not state a payout."
}
```

Report fields are omitted.

### Medical / legal refusal

```json
{
  "decision": "refuse",
  "rule_id": null,
  "quoted": "No rule line matched.",
  "source": "policy-excerpt.md",
  "message": "The desk only decides intake coverage. It will not give medical or legal advice."
}
```

## Batch

With no id and no `--advice`, `--json` prints an array of three coverage objects in kit order (CL-03, CL-04, CL-08).

## Invariants

1. `source` is always `policy-excerpt.md`.
2. When `rule_id` is set, that id appears as a line prefix in `md/policy-excerpt.md`, and the quoted line is a substring of that file.
3. Golden cases: CL-03 open/PX-GLASS, CL-04 refuse/PX-FLOOD, CL-08 hold/PX-COLLISION.
4. Engine output MUST NOT contain `$` plus digits or a promised settlement number. Quoted kit lines MAY contain the word payout as a prohibition.
5. The engine never mints `claim_number` and never writes `var/`.

## MCP (chat path)

Server name: `rules`. Tools: `list_rules`, `lookup_rule`.
Command: `python3 python/rules_mcp.py`.
`lookup_rule` argument: `{ "query": "<string>" }`.
Hit for `flood` starts with `PX-FLOOD`.
Miss response: `No rule line matched '<query>'.` — treat as no match, do not invent.

## HTTP (website UI → Python backend)

`bin/desk.sh` starts `python/serve_desk.py` on `127.0.0.1:8788`. The UI MUST call these APIs. It MUST NOT re-implement `decide.py` in JavaScript.

### `GET /api/queue`

Read-only. Does not write `var/`. Returns an array. Each item is a coverage decision from `decide.py` plus:

| Field | Notes |
|-------|-------|
| `label` | `hold for photos` when `decision` is `hold`; else the decision |
| `send_state` | `draft` / `sent` / `held` |
| `claim_number` | null until open confirm |
| `can_confirm` | open or hold in draft |
| `can_undo` | sent or held |

Optional display chrome from `python/display.json` is not an input to the engine.

### `POST /api/ask`

Body: `{ "question": "<text>" }`.

Payout-family → `{ "label": "refuse", "decision": "refuse", "rule_id": "PX-NO-PAY", "quoted": "PX-NO-PAY. …", "detail": "The desk does not state a payout." }`

Medical/legal → `{ "label": "refuse", "rule_id": null, "quoted": "No rule line matched.", "detail": "<coverage-only sentence>" }`

Any other question → `{ "label": "Off-desk", "decision": "Off-desk", "rule_id": null, … }`

### `POST /api/confirm`

Body: `{ "id": "CL-03" }`. Only mint.

- Open + draft → 200, `send_state: sent`, `claim_number: FNOL-CL-03-YYYYMMDDTHHMMSSZ`
- Hold + draft → 200, `send_state: held`, `claim_number: null`
- Refuse → 400 `{ "error": "refuse is not sent" }`
- Missing / unknown id / already confirmed → 400 `{ "error": "…" }`

### `POST /api/undo`

Body: `{ "id": "CL-03" }`. Sent or held → draft. Claim number cleared. History appended, not deleted.

### `GET /api/log`

JSONL as an array. Keys: `ts`, `id`, `decision`, `quoted`, `event`, optional `claim_number`. No `amount`, `payout`, or `$` keys.

### `GET /api/health`

`{ "ok": true, "policy": "<path to policy-excerpt.md>", "reports": "<path to fnol.json>", "engine": "python/decide.py" }`

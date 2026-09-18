# Claim intake desk (backend)

Open, hold for photos, or refuse against `policy-excerpt.md`. Never a payout.

**Grok assesses every inquiry.** The model must call `lookup_rule`; Python runs that tool against local `rules_mcp.py` and only then accepts the JSON decision. Python is not a second rule book.

Kit (do not rewrite): `fnol.json`, `policy-excerpt.md`, `rules_mcp.py`.

## Setup

```text
pip install -r requirements.txt
```

Put `XAI_API_KEY` in the environment or a gitignored `.env`. Live assess (`python -m backend.run CL-04`, `POST /api/assess`) needs the key. Unit tests inject a scripted model and still hit the real MCP.

## Run

```text
python -m backend.run mcp
python -m unittest backend.test_assess backend.test_serve
python .grok/hooks/scripts/enforce_rules.py --self-test
python -m backend.run CL-04
python -m backend.serve
bash bin/desk.sh
```

`bin/desk.sh` loads `.env`, starts the API + `web/` on `127.0.0.1:8788`, and opens **http://127.0.0.1:8788/clerk.html**. The same process serves the clerk UI and Grok assessments against `fnol.json`.

API binds `127.0.0.1:8788`. State dir is `var/` (`CLAIMDESK_VAR`). Kit root: `CLAIMDESK_ROOT`.

## API (colleague frontend)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/health` | MCP reachable |
| GET | `/api/queue` | Cached decisions only. Does not call Grok. `needs_assess` until POST assess. |
| POST | `/api/assess` | `{ "id": "CL-03" }` or `{ "question": "will we pay?" }`. Grok + MCP tools. |
| POST | `/api/confirm` | Human click. Mints `FNOL-{id}-{UTC}` on **open** only. CL-04 → `400 {"error":"refuse is not sent"}`. |
| POST | `/api/undo` | Restore draft. |
| GET | `/api/log` | JSONL events. No amount / payout / `$` keys. |

`mcp` on a decision is the tool call the model actually made.

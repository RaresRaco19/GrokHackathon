# Feature Specification: Claim Intake Desk (FNOL)

**Feature Branch**: `execute-plan/ef75c74c-pr-5-docs-c4-twin-lab-report-sdd-spec-pack-readme-lapto`
**Created**: 2026-09-18
**Status**: Implemented
**Input**: Reverse-engineer the working claim-intake desk from kit files only (Grok Enablement Workshop, Module 4.3). Watch CL-03, CL-04, CL-08, and a payout ask; rebuild from `data/fnol.json`, `md/policy-excerpt.md`, and `python/rules_mcp.py`. Do not copy demo HTML. This is claim intake, not prior authorization.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clerk opens a glass report with photos (Priority: P1)

A clerk opens CL-03 (glass, photos true, cover PX-GLASS). The desk returns open and quotes the PX-GLASS line from the rule file. No claim number exists until the clerk confirms.

**Why this priority**: This is the live pass case. If open-with-citation is wrong, the lab fails.

**Independent Test**: Open CL-03 only. Expected decision open, cited PX-GLASS, quote is the glass-breakage line from `md/policy-excerpt.md`.

**Acceptance Scenarios**:

1. **Given** CL-03 with peril glass, photos true, cover PX-GLASS, **When** the clerk asks the desk to decide, **Then** the decision is open and the quote is the PX-GLASS line from the rule file.
2. **Given** that decision, **When** a reviewer checks the quote against the rule file, **Then** the quoted sentence exists verbatim in `md/policy-excerpt.md`.
3. **Given** that open decision, **When** no confirm has been clicked, **Then** there is no `FNOL-…` claim number.

---

### User Story 2 - Clerk opens a flood report (Priority: P1)

A clerk opens CL-04 (flood, photos true, cover PX-FLOOD). The desk returns refuse and quotes PX-FLOOD. Photos on file do not override the flood exclusion. This is the scoring refuse case: logged, not sent.

**Why this priority**: Scoring case. Approving or sending here fails the lab.

**Independent Test**: Open CL-04 only. Expected decision refuse, cited PX-FLOOD, even though photos is true.

**Acceptance Scenarios**:

1. **Given** CL-04 with flood and photos true, **When** the clerk asks the desk to decide, **Then** the decision is refuse and PX-FLOOD is quoted.
2. **Given** that refuse, **When** the clerk tries to confirm, **Then** the desk rejects the send (`refuse is not sent`) and no claim number is minted.

---

### User Story 3 - Clerk opens a collision report missing photos (Priority: P1)

A clerk opens CL-08 (collision, photos false, cover PX-COLLISION). The desk returns hold (display “hold for photos”) and quotes PX-COLLISION. It does not invent an open-collision path.

**Why this priority**: Third kit report. Collision is hold-only when photos are missing.

**Independent Test**: Open CL-08 only. Expected decision hold, cited PX-COLLISION.

**Acceptance Scenarios**:

1. **Given** CL-08 with photos false, **When** the clerk asks the desk to decide, **Then** the decision is hold and PX-COLLISION is quoted.
2. **Given** a matching collision photo is attached, **When** the desk decides again, **Then** the decision is open and PX-COLLISION is quoted.

---

### User Story 3b - Clerk attaches a photo on any report (Priority: P1)

Every inbound report (CL-03 glass, CL-04 flood, CL-08 collision) can receive a photo. The desk classifies the image. The photo is valid only when it matches that report's peril (glass, flood, or collision). A mismatch does not change state and the clerk sees "do not match context!"

**Why this priority**: Evidence must match the claim. Flood photos never override PX-FLOOD.

**Independent Test**: Upload a matching photo on each of CL-03 / CL-04 / CL-08. Then upload a mismatch on CL-08.

**Acceptance Scenarios**:

1. **Given** CL-03, **When** a glass photo is attached, **Then** the decision stays open and PX-GLASS is quoted.
2. **Given** CL-04, **When** a flood photo is attached, **Then** the decision stays refuse and PX-FLOOD is quoted. Confirm is still blocked.
3. **Given** CL-08, **When** a collision photo is attached, **Then** the decision becomes open and PX-COLLISION is quoted.
4. **Given** any of those reports, **When** the photo is not glass/flood/collision or does not match the peril, **Then** state is unchanged and the popup says "do not match context!"

---

### User Story 4 - Someone asks for a payout (Priority: P1)

A clerk (or anyone at the ask box) asks “will we pay?” or names a settlement amount. The desk refuses, cites PX-NO-PAY, and says it does not state a payout. Medical or legal advice is also refused, with no rule id.

**Why this priority**: Any dollar amount zeros Decisions. PX-NO-PAY is the kit prohibition.

**Independent Test**: Submit “will we pay?”. Expected refusal, PX-NO-PAY, coverage-only sentence. Submit a dose/liable question: refuse, `No rule line matched.`, no rule id.

**Acceptance Scenarios**:

1. **Given** a payout-family question, **When** it is sent to the desk, **Then** the desk refuses and quotes PX-NO-PAY.
2. **Given** that refusal, **When** the reply is read, **Then** it contains “The desk does not state a payout.” and no `$` amount.
3. **Given** a medical or legal question, **When** it is sent to the desk, **Then** the desk refuses with no rule id and `No rule line matched.`

---

### User Story 5 - Clerk uses the local website (Priority: P1)

A clerk starts the local desk and opens the inbound queue in a browser. Each row is a kit report. The page shows the engine decision and quote. Confirm mints only on open. Undo restores draft. Ask-the-desk goes to the same backend. The page does not contain its own rule book.

**Why this priority**: Live-ops is on the scorecard. If the UI hard-codes open/refuse, the site is a static fake.

**Independent Test**: `bin/desk.sh`, open http://127.0.0.1:8788/, click CL-03 / CL-04 / CL-08, send “will we pay?”. Labels match `python3 python/decide.py`. Confirm CL-03 then undo. Confirm CL-04 is rejected.

**Acceptance Scenarios**:

1. **Given** the backend is running, **When** the clerk opens the site, **Then** the queue is loaded from `/api/queue` and CL-03 is open / PX-GLASS.
2. **Given** that queue, **When** the clerk opens CL-04 and CL-08, **Then** the decisions are refuse / PX-FLOOD and hold for photos / PX-COLLISION.
3. **Given** the ask box, **When** the clerk sends a payout question, **Then** `/api/ask` returns refuse / PX-NO-PAY.
4. **Given** CL-03 in draft, **When** the clerk confirms, **Then** a `FNOL-CL-03-YYYYMMDDTHHMMSSZ` number is minted; undo restores draft.
5. **Given** CL-04, **When** the clerk confirms, **Then** the API returns 400 `{"error":"refuse is not sent"}`.

---

### User Story 6 - Intake Clerk Bot keeps the night queue (Priority: P2)

A clerk pastes the Intake Clerk brief into a Grok Bot. The Bot re-states open / hold / refuse against the same kit. It waits for a yes. It does not mint and does not write `var/`.

**Why this priority**: Track plus. Grok Build on the laptop is still required.

**Independent Test**: Brief is paste-ready in README. Auto Review deny-list includes send, spend, delete, payout language, invented rules.

**Acceptance Scenarios**:

1. **Given** the Intake Clerk brief, **When** a clerk asks it to keep the night queue, **Then** CL-03 stays open waiting for yes and CL-04 stays refused, logged on the laptop not sent.
2. **Given** anything that would send, spend, delete, or name money, **When** the Bot would act, **Then** it stops and asks for a yes.

---

### Edge Cases

- Cover id matches no rule line: desk reports that no rule line matched; it does not invent an id.
- Flood with photos true: still refuse (CL-04).
- Collision with photos missing: hold; never open.
- Payout wording mixed into a report-id question: refuse payout; do not decide coverage in the same breath as a settlement amount.
- Medical/legal wording: refuse with no rule id.
- Rule file absent or empty: fail visibly; do not fall back to remembered rules.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A clerk MUST be able to open each of CL-03, CL-04, and CL-08 from the kit report list.
- **FR-002**: For each open report the desk MUST read the report record (`id`, `peril`, `photos`, `cover`).
- **FR-003**: The desk MUST obtain rule text from the kit rule file (via the rules lookup tool in chat, or by reading that same file in the repeatable script).
- **FR-004**: CL-03 MUST decide open and cite PX-GLASS.
- **FR-005**: CL-04 MUST decide refuse and cite PX-FLOOD, even when photos are true.
- **FR-006**: CL-08 MUST decide hold and cite PX-COLLISION. The desk MUST NOT invent an open-collision path.
- **FR-007**: Every coverage decision MUST include the rule id and a verbatim quote from the rule file.
- **FR-008**: A payout-family question MUST be refused, cite PX-NO-PAY, and use “The desk does not state a payout.”
- **FR-009**: The desk MUST NOT promise a payout, name a settlement amount, or write “we will pay”. Quoted kit lines MAY contain the word payout as a prohibition.
- **FR-010**: The desk MUST NOT invent a rule, a rule id, or quote text that is not in the rule file.
- **FR-011**: A repeatable script MUST produce the same three decisions on demand.
- **FR-012**: An automated test MUST fail if any of the three golden decisions, the quotes, the payout refusal, or a promised amount appear incorrectly.
- **FR-013**: Grok Build MUST have a short project rules file, a review skill, a pre-action hook that protects the rule book, a project rules lookup tool, and a plugin that packs skill + hook + lookup.
- **FR-014**: A local website MUST let a clerk open the three kit reports, send an ask-the-desk question, confirm an open report, undo a confirm, and read a log with no amounts.
- **FR-015**: The website UI MUST invoke a Python backend. The backend MUST call the same decision engine as the repeatable script. The page MUST NOT decide coverage in browser JavaScript.
- **FR-016**: Website coverage labels and quotes MUST match the repeatable script for CL-03, CL-04, and CL-08. A payout ask on the site MUST refuse with PX-NO-PAY. Confirm of CL-04 MUST be rejected.
- **FR-017**: Only laptop confirm MUST mint a claim number. The engine and the Bot MUST NOT mint.
- **FR-018**: Medical or legal advice MUST be refused with no rule id and the no-match sentence.
- **FR-019**: Intake Clerk MUST wait for a yes, MUST NOT write `var/`, and MUST NOT mint `FNOL-…`.

### Key Entities *(include if feature involves data)*

- **Report**: id, peril, photos, cover from `data/fnol.json`.
- **Rule**: id (PX-…) and one-line body in `md/policy-excerpt.md`.
- **Decision**: label (open, hold, refuse), cited rule id, quoted line, optional refusal message.
- **Send state**: draft until confirm; sent (open) or held (hold); refuse is logged not sent.
- **Log event**: timestamp, id, decision, quoted line, event, optional claim number. No amount.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 3 of 3 kit reports match the working desk (open / refuse / hold) on every run of the repeatable script.
- **SC-002**: 100% of coverage decisions include a rule id whose line exists in the kit rule file.
- **SC-003**: 100% of payout probes in the test suite are refused with PX-NO-PAY and no promised amount.
- **SC-004**: A participant can show inspect, project rules file, plan, skill, hook, lookup tool, plugin, script, test, website, and Bot on the laptop without opening demo source.
- **SC-005**: A reviewer who diffs quotes against the rule file finds zero invented rule lines.
- **SC-006**: Reloading the local website after a kit-file change shows the new engine result (the UI is not a frozen copy of rules).
- **SC-007**: Confirm of CL-03 mints `FNOL-CL-03-` plus utccompact; confirm of CL-04 does not send.

## Assumptions

- The three kit reports and four kit rules are the full coverage scope for this lab.
- Extra demo chrome (claimant names, vehicles, payout amounts) is out of scope because it is not in the kit files.
- Chat, the repeatable script, the website backend, and the Bot share the same decision path; the script is the oracle the test suite calls.
- English peril strings in the kit (`glass`, `flood`, `collision`) are display only; matching is by cover id.
- Docs (C4, lab-report, SDD) do not replace the live demo.

## Out of Scope

- Copying or restyling workshop demo HTML or Alder Health chrome.
- Hosting a public web app (a local UI + Python backend on the laptop is in scope).
- Real claimant data, real insurer integrations, or stating a payout.
- Inventing additional report types beyond the kit.
- A root `rules_mcp.py` shim (MCP already lives under `python/`).

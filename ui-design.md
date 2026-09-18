# Dashboard design: Intake Desk

## 0. Meta
- Product: Intake Desk (FNOL — first notice of loss)
- Audience: The on-laptop clerk who opens, holds, or refuses reports against `policy-excerpt.md`
- Primary question the dashboard answers: For this shift, which reports are open, hold-for-photos, or refuse — and which policy line is quoted?
- Platform: web dashboard, desktop-first
- A11y target: WCAG 2.2 AA
- Locale / number format: `en-US`; tabular lining figures; thousands separators; no currency; no settlement amounts
- Stack to match (or "greenfield"): greenfield semantic HTML + CSS + vanilla JS under `web/`, later served by `python/serve_desk.py` on `127.0.0.1:8788` (that server is not in this spec’s build)
- Mode: replicate (`https://legora.com/bar`)
- Spec status: complete
- Source page type: public research/marketing article (not an authenticated app). Layout, region order, and widget types are taken from that article. Copy, photos, brand, and operational screens are original to Intake Desk.

## 1. Assumptions
- The source URL is a long-form research page, not a claims desk. This spec keeps that page’s region order and widget types, then adds the minimum operational screens the FNOL product needs (queue, claim detail, policy, log).
- Kit data is the only live queue: `fnol.json` rows `CL-03`, `CL-04`, `CL-08`. UI never invents extra reports or extra `PX-*` ids.
- Decision labels are `open` / `hold` / `refuse` from `python/decide.py` (oracle). UI does not contain rules; it displays engine output and quotes from `policy-excerpt.md`.
- A claim number exists only after the clerk confirms an `open` draft. Confirm on `CL-04` is blocked. Undo restores draft.
- No payout, settlement amount, or `$` appears in UI copy, logs, or charts.
- Photos in `web/assets/` are original generated stills (desk, glass, flood, collision, intake tray). They are not taken from the source site.
- Until `serve_desk.py` exists, the frontend reads `web/desk.json` and keeps confirm/undo in `localStorage` key `intake.desk.v1`. When the API is present, the same shapes are fetched from `/api/queue`, `/api/confirm`, `/api/undo`, `/api/ask`, `/api/log`.
- Default time range is last 7 days. All three kit reports have `received_at` inside that window.
- Auth is not implemented. The clerk chip is a static label (`Mara Ellison`). No login wall.
- Density is **roomy editorial** (source intent), not the compact dashboard default.
- `sm` is a usable single column of the same article/desk, not a marketing-site restyle.

## 2. Open questions
- Q: Should the Python API land in this UI pass? Options: fixture-only now / wire `serve_desk.py` now. Default if unanswered: fixture-only with the API shapes documented in §10 so PR-3 can swap the adapter.
- Q: Bot “Intake Clerk” surface in this chrome? Options: out of scope / status chip only. Default: out of scope (pointer in footer only).

## 3. Tweaks (replicate only)

| Axis | Keep | Change |
|---|---|---|
| IA | One long briefing page with the same region order as `/bar` (hero → meta+lead → strip → why → fundamentals → KPI row → heatmap → anatomy → classification table → 01–03 cards → scored checklist → findings/charts → example cards → footer) | Add operational routes the source does not have: Queue, Claim, Policy, Log — required for FNOL live-ops |
| Nav | Top bar, left links, centered wordmark, right text control + filled pill CTA | Labels become Queue / Policy / Log / Ask; wordmark `INTAKE`; CTA is context-specific (`Open queue` or `Confirm`); no Product/Solutions mega-menus |
| Shell | No sidebar; sticky top bar; article column ~720px for prose, ~1120px for widgets | Add time-range control (source has none) top-right of the content pane; add skip link, toast region, last-updated |
| Hero | Kicker + large title + full-width photo with two-line overlay | Original desk photo; overlay `INTAKE` / `First notice of loss`; no statue, no source wordmark |
| Meta | Left stacked Category / Updated / Author | Category `Live ops`; date `18 Sep 2026`; authors are fictional clerks, not source names |
| Strip | Two rows of five marks under a caption | Original peril/tray photos with FNOL captions; **no partner or lab logos** |
| KPIs | Three giant numbers in a 3-up row | Values from the kit (3 reports, 4 rules, 2 photos), not 28 / 5,161 / 11,075 |
| Heatmap | 4-column color-weight grid + 4-stop legend | Cells are the three kit reports + policy covers; sequential **navy** (not source forest green) |
| Charts | Grouped bars by bucket; two scatter plots; muted grid; lab color key | Series are decision labels and photo completeness; no model names, no cost axis, no source lab colors |
| Brand | Light paper, black type, pill CTA, editorial measure | Wordmark `INTAKE`; accent navy `#1B365D`; type IBM Plex Sans + Source Serif 4 + IBM Plex Mono (not Aktiv Grotesk / Playfair / source green `#005032`) |
| Copy / images | Region jobs stay the same | All sentences, names, photos, and numbers are original FNOL fiction or kit facts |
| Usability | — | Hit targets ≥ 44px; visible focus; loading/empty/error on every data view; do not copy the cookie modal |

## 4. Design tokens

### Color

| Token | Value | Use |
|---|---|---|
| `token.color-bg` | `#F7F6F2` | Page |
| `token.color-surface` | `#FFFFFF` | Cards, top bar, heatmap empty cells |
| `token.color-surface-muted` | `#EFEDE7` | 01–03 step cards, inset wells |
| `token.color-surface-hover` | `#E8EEF4` | Row / nav hover |
| `token.color-text` | `#141414` | Primary text, wordmark, H1 |
| `token.color-text-muted` | `#5C5C5C` | Meta, captions, axis (≥ 4.5:1 on `color-bg`) |
| `token.color-border` | `#E1DED6` | Table rules, card hairlines, heatmap gaps |
| `token.color-accent` | `#1B365D` | Primary pill, current nav underline, heatmap max, focus |
| `token.color-accent-hover` | `#132844` | Pill hover |
| `token.color-on-accent` | `#FFFFFF` | Text on pill and dark heatmap cells |
| `token.color-success` | `#1F6B4A` | Open badge, check |
| `token.color-warning` | `#9A5B12` | Hold badge |
| `token.color-danger` | `#9B2C2C` | Refuse badge, missed check |
| `token.color-focus` | `#1B365D` | 2px focus ring, offset 2px |
| `token.color-overlay` | `rgba(20, 20, 20, 0.35)` | Hero photo scrim |
| `token.color-heat-1` | `#E8EEF4` | Heatmap: idle / zero |
| `token.color-heat-2` | `#9BB0C7` | Heatmap: hold / photos missing |
| `token.color-heat-3` | `#4A6F94` | Heatmap: open |
| `token.color-heat-4` | `#1B365D` | Heatmap: refuse (highest weight) |
| `token.color-chart-open` | `#1B365D` | Series: open |
| `token.color-chart-hold` | `#C4A35A` | Series: hold (not green/red alone) |
| `token.color-chart-refuse` | `#6B2D2D` | Series: refuse |
| `token.color-chart-avg` | `#141414` | Average rule on charts |
| `token.color-toast-ok` | `#1F6B4A` | Confirm toast border |
| `token.color-toast-err` | `#9B2C2C` | Error toast border |

Accent is used for the primary pill, current nav, focus, and the darkest heatmap cell. KPI tiles, body links in prose, and chart fills do **not** all use accent.

### Typography

| Token | Font | Size | Line-height | Weight | Use |
|---|---|---|---|---|---|
| `token.font-ui` | `"IBM Plex Sans", "Segoe UI", sans-serif` | — | — | — | Chrome, nav, table, buttons |
| `token.font-display` | `"Source Serif 4", Georgia, serif` | — | — | — | Mission lead, section titles in the briefing |
| `token.font-mono` | `"IBM Plex Mono", ui-monospace, monospace` | — | — | — | Meta labels, claim ids, quotes, KPI numbers |
| `token.type-kicker` | ui | `0.6875rem` / 11px | 1.2 | 500 | `LIVE OPS` kicker; letter-spacing `0.12em`; uppercase |
| `token.type-h1` | ui | `2.75rem` / 44px (`lg`); `2rem` / 32px (`sm`) | 1.1 | 500 | Page title |
| `token.type-lead` | display | `1.75rem` / 28px (`lg`); `1.375rem` / 22px (`sm`) | 1.3 | 400 | Mission paragraph |
| `token.type-h2` | display | `1.5rem` / 24px | 1.25 | 600 | Section titles |
| `token.type-h3` | ui | `1rem` / 16px | 1.3 | 600 | Card titles, widget titles |
| `token.type-body` | ui | `1rem` / 16px | 1.55 | 400 | Prose |
| `token.type-caption` | ui | `0.75rem` / 12px | 1.4 | 400 | Meta, axis, helper |
| `token.type-kpi` | mono | `3.5rem` / 56px (`lg`); `2.5rem` / 40px (`sm`) | 1 | 400 | KPI values; `font-variant-numeric: tabular-nums` |
| `token.numeric` | mono | inherit | inherit | 400 | Every number in KPIs, tables, charts, badges |

### Space, radius, elevation, motion, z-index, breakpoints

| Token | Value | Use |
|---|---|---|
| `token.space-1` | `4px` | Icon gaps |
| `token.space-2` | `8px` | Control gap |
| `token.space-3` | `16px` | Compact inner |
| `token.space-4` | `24px` | Card padding |
| `token.space-5` | `32px` | Region gap |
| `token.space-6` | `48px` | Section gap (`md+`) |
| `token.space-7` | `64px` | Briefing section gap (`lg`) |
| `token.radius-sm` | `6px` | Inputs, heatmap cells |
| `token.radius-md` | `8px` | Cards |
| `token.radius-pill` | `999px` | CTA, chips, badges |
| `token.elev-1` | `0 1px 0 rgba(20,20,20,0.06)` | Top bar bottom hairline (no drop shadow) |
| `token.elev-toast` | `0 8px 24px rgba(20,20,20,0.12)` | Toasts |
| `token.motion` | `160ms ease` | Hover, drawer; honor `prefers-reduced-motion: reduce` → `0ms` |
| `token.z-nav` | `40` | Sticky top bar |
| `token.z-drawer` | `50` | `sm` nav drawer |
| `token.z-toast` | `60` | Toasts |
| `token.hit` | `44px` | Min height/width for icon buttons, pills, nav links |
| `token.prose` | `720px` | Measure for lead and body |
| `token.shell` | `1120px` | Widgets, heatmap, charts |
| `token.nav-h` | `64px` | Top bar height |

| Breakpoint | px | Layout change |
|---|---|---|
| `token.bp-sm` | 375 | Single column; nav links in a drawer; heatmap 2 columns; KPI stack; tables scroll-x with sticky first column; CTA stays in the top bar |
| `token.bp-md` | 768 | Meta column stacks above lead; heatmap 2 columns; KPI 3-up if width allows |
| `token.bp-lg` | 1280 | Persistent top bar links; meta 200px left + lead; KPI 3-up; heatmap 4-up; charts full `token.shell` |
| `token.bp-xl` | 1440 | Same as `lg`; do not add a fourth KPI |

## 5. Information architecture

- Sitemap
  - Intake briefing (`screen.overview`) — source-page replica with FNOL content
  - Queue (`screen.queue`) — added
  - Claim (`screen.claim`) — added
  - Policy (`screen.policy`) — added
  - Log (`screen.log`) — added
  - Ask overlay (`comp.ask-dialog`) — added, not a route

| ID | Path | Screen | Auth |
|---|---|---|---|
| `route.overview` | `/` or `index.html` | `screen.overview` | none |
| `route.queue` | `queue.html` | `screen.queue` | none |
| `route.claim` | `claim.html?id={id}` | `screen.claim` | none |
| `route.policy` | `policy.html` | `screen.policy` | none |
| `route.log` | `log.html` | `screen.log` | none |

Sidebar items: none. Top-bar items in order:

| Label | Destination | Icon | Badge rule |
|---|---|---|---|
| Queue | `route.queue` | none | Count of `send_state = draft` (integer, tabular) |
| Policy | `route.policy` | none | none |
| Log | `route.log` | none | none |
| Ask | opens `comp.ask-dialog` | none | none |
| INTAKE (center wordmark) | `route.overview` | `logo.product` (text, not an image) | none |
| {time range} | `comp.time-range` | none | none |
| Open queue / Confirm | primary CTA | arrow-up-right | Confirm enabled only when `can_confirm` on `screen.claim` |

Global controls: time range (last 7d default), clerk chip `Mara Ellison` (not a menu), last updated timestamp.

## 6. Global shell

**Placement**
- `lg`: sticky top bar full width, `token.nav-h`, `token.color-surface`, bottom `token.elev-1`. Content starts below. Toasts fixed bottom-right, 16px from edges.
- `sm`: same bar; left links collapse to a 44×44 menu button (accessible name `Menu`); drawer slides from the left, `token.color-surface`, Esc closes, focus traps.

**Contents (left → right)**
1. `sm` only: `comp.icon-button` Menu
2. Nav links Queue, Policy, Log, Ask (`nav aria-label="Desk"`)
3. Centered wordmark `INTAKE` (`a` to overview, `font-weight: 500`, letter-spacing `0.18em`)
4. `comp.time-range`
5. Clerk text `Mara Ellison` (`type-caption`, not a button)
6. Primary `comp.button` — on overview/queue/policy/log: label `Open queue` → `route.queue`. On claim: label `Confirm` when `can_confirm`, else `Confirm` disabled with `aria-disabled` and title from §7.

**Components used:** `comp.button`, `comp.icon-button`, `comp.time-range`, `comp.toast`, `comp.ask-dialog`

**States**
- default: wordmark + links + CTA
- nav current: 2px underline `token.color-accent`, `aria-current="page"`
- drawer-open (`sm`)
- scrolled: bar stays opaque white (no shrink)
- CTA loading: spinner in the button, label unchanged

**Keyboard / focus**
1. Skip link `Skip to main content` (visible on focus) → `#main`
2. Nav links in visual order
3. Wordmark
4. Time range
5. Primary CTA
6. Main

Esc closes drawer and `comp.ask-dialog`. Focus ring 2px `token.color-focus`, offset 2px. Never `outline: none` without the ring.

**Copy**
- Skip: `Skip to main content`
- Menu: `Menu` / `Close menu`
- Wordmark accessible name: `Intake Desk home`
- Last updated (in main, not the bar): `Updated {relative}` with `title="{absolute}"`

## 7. Screens

### screen.overview — Intake briefing

**Route:** `index.html` (`route.overview`)
**Goal:** Answer “how is this shift’s queue shaped, and how does this desk decide?”
**Entry / exit:** Default land. KPI `Reports in queue` and heatmap cells go to `route.queue` (filtered). Example cards go to `route.claim`. CTA `Open queue`.

**Layout**
- `lg`: article column centered. Regions top → bottom as listed.
- `sm`: same order, stacked; hero 16:9; meta above lead.

```
[ TOP BAR: Queue Policy Log Ask | INTAKE | range | Open queue ]
[ kicker LIVE OPS ]
[ h1 Introducing the intake desk ]
[ hero 16:9  overlay INTAKE / First notice of loss ]
[ meta 200px | lead + body ]
[ photo strip 5 cells ]
[ h2 Why this desk exists ]
[ h2 How a report is decided  + ol 1–4 ]
[ h2 This shift ]
[ KPI  | KPI  | KPI ]
[ heatmap 4 col ]
[ h2 Four parts of a file ]
[ ol 1–4 ]
[ table open / hold / refuse ]
[ h2 How we score a file ]
[ 01 | 02 | 03 ]
[ scored checklist ]
[ h2 This shift’s picture ]
[ grouped bars ]
[ scatter photos vs decision ]
[ example cards CL-03 / CL-04 / CL-08 ]
[ footer ]
```

**Regions**

1. **Hero** — kicker `Live ops`; `h1` `Introducing the intake desk`; image `web/assets/hero.jpg` `alt="Claims office desk with a cork board of vehicle photos, a closed laptop, and stacked folders at dusk."`; overlay text `INTAKE` (left) and `First notice of loss` (right), `token.color-on-accent`. Overlay is HTML, not baked into the photo.

2. **Meta + lead** — fields: `category` = `Live ops`; `updated` = `18 Sep 2026`; `authors` = `Mara Ellison`, `Kenji Okada`, `Priya Shah`. Lead (display): `This desk opens, holds, or refuses a first notice of loss against a four-line policy excerpt. A clerk clicks before a claim number exists. Flood is refused. Missing photos wait. Nobody names a payout.` Body: `The engine reads fnol.json and quotes policy-excerpt.md. The website only displays that decision. Confirm mints a number on open files. Refuse is logged on this laptop and is not sent.`

3. **Photo strip** — caption `Files this desk already knows how to see:` cells, each a link to the matching claim or policy:
   - `glass.jpg` → CL-03 · Glass
   - `flood.jpg` → CL-04 · Flood
   - `collision.jpg` → CL-08 · Collision
   - `tray.jpg` → Policy excerpt
   - `hero.jpg` (cropped) → Queue
   Alt text in § data. No logos.

4. **Why this desk exists** — prose in Copy.

5. **How a report is decided** — numbered 1–4 (fundamentals).

6. **This shift KPIs** — `comp.kpi-tile` × 3. Fields:
   - `reports_in_queue` number `3` caption `Reports in queue` helper `Each a cover id, a peril, and a photos flag.` drill → `route.queue`
   - `rules_in_force` number `4` caption `Policy lines in force` helper `PX-GLASS, PX-FLOOD, PX-COLLISION, PX-NO-PAY.` drill → `route.policy` (not a metric breakdown of reports; still a link because it has a destination)
   - `photos_on_file` number `2` caption `Photos on file` helper `2 of 3 reports. Collision is waiting.` drill → `route.queue?photos=false`

7. **Heatmap** — `comp.heatmap` 4 columns × 2 rows:

   | Cell | Weight | Color token | Dest |
   |---|---|---|---|
   | Glass · CL-03 · open | 3 | heat-3 | claim CL-03 |
   | Flood · CL-04 · refuse | 4 | heat-4 | claim CL-04 |
   | Collision · CL-08 · hold | 2 | heat-2 | claim CL-08 |
   | Payout ask · off-desk | 1 | heat-1 | Ask dialog (prefill empty) |
   | Photos on file · 2 | 3 | heat-3 | queue photos=true |
   | Photos missing · 1 | 2 | heat-2 | queue photos=false |
   | Draft · 3 | 3 | heat-3 | queue send_state=draft |
   | Logged refuse · 1 | 1 | heat-1 | log |

   Legend: `Idle` heat-1 · `Hold` heat-2 · `Open` heat-3 · `Refuse` heat-4.

8. **Four parts of a file** — numbered list (Copy).

9. **Decision table** — `comp.table` columns `Label` | `When` | `What the clerk sees`. Rows: open / hold / refuse (Copy). Not sortable (3 rows). Row click → filtered queue.

10. **How we score a file** — three `comp.step-card` 01 02 03 + `comp.score-card` defaulting to CL-03 (see component).

11. **This shift’s picture** — `comp.chart` grouped bars: x = peril (`glass`, `flood`, `collision`); series = open/hold/refuse counts (1, 0, 0 / 0, 0, 1 / 0, 1, 0). Average rule is the mean of the three decision weights (open=1, hold=0, refuse=0 mapped to 0–1) drawn as a 1px `token.color-chart-avg` line at `0.33`. Second widget: scatter, x = photos `0|1`, y = decision weight, points labeled CL-03 / CL-04 / CL-08. No cost axis.

12. **Example cards** — three `comp.example-card` for CL-03, CL-04, CL-08.

13. **Footer** — product name, links to Policy / Log / Queue, line `Rule book: policy-excerpt.md. Engine: python/decide.py. No payouts.` © 2026 Intake Desk.

**States**
- default: kit data as above
- loading: KPI values `—`; heatmap cells pulse `token.color-surface-muted`; charts show `comp.empty-state` variant loading `Loading this shift…`
- empty (`?state=empty` or time range with no reports): KPI `0`; heatmap all heat-1; empty state `No reports in this range.` action `Reset to last 7 days`
- error: KPI `!`; inline `Could not load the queue.` + `Retry`
- partial: charts failed, KPIs ok — chart card shows error + Retry; rest stays

**Copy**
- Kicker: `Live ops`
- H1: `Introducing the intake desk`
- Hero overlay: `INTAKE` / `First notice of loss`
- Why heading: `Why this desk exists`
- Why body: `A first notice of loss is a file, not a promise. This desk exists so a clerk can see the same three golden cases a judge will ask for: glass that can open, flood that must refuse, collision that waits for photos. The policy excerpt is the only rule book. If a question is medical, legal, or about money, the desk turns it down.`
- Fundamentals heading: `How a report is decided`
  1. `The cover id on the report selects a line in policy-excerpt.md.`
  2. `The clerk’s question is the prompt. Payout and medical-legal questions are off-desk.`
  3. `The file is the photos flag plus the peril. Missing photos cannot open.`
  4. `The engine is python/decide.py. The website does not keep a second copy of the rules.`
- Anatomy heading: `Four parts of a file`
  1. `Report id — CL-03, CL-04, or CL-08.`
  2. `Peril and photos — glass, flood, or collision, and whether photos are on the file.`
  3. `Quoted line — the verbatim PX-* sentence from policy-excerpt.md.`
  4. `Clerk action — confirm (open only), hold, or log a refuse. Undo puts an open file back to draft.`
- Findings heading: `This shift’s picture`
- Chart 1 title: `Decisions by peril`
- Chart 1 helper: `Count of open, hold, and refuse on the three kit reports.`
- Chart 2 title: `Photos on file vs decision`
- Chart 2 helper: `1 = photos present. Decision weight: refuse 0, hold 0.5, open 1. No money axis.`
- Source line under charts: `Source: fnol.json + policy-excerpt.md`

**A11y:** `h1` once; `h2` per section; heatmap cells are links with names like `Glass CL-03, open`; KPI values in `<p>` with `<h3>` captions; charts have a text table fallback in a visually adjacent `<table class="sr-chart-data">` (visible `sm` as a stacked table, `lg` available to AT). Focus order: skip → nav → range → CTA → kicker/h1 → meta → lead → strip → sections.

**Acceptance criteria**
- Given the kit fixture, when the briefing loads, then KPIs read `3`, `4`, and `2` with tabular nums.
- Given a heatmap cell `Flood · CL-04`, when activated, then `claim.html?id=CL-04` opens.
- Given `?state=empty`, when the briefing loads, then the empty copy and reset action are visible; no source-site numbers appear.
- Given any view, when copy is searched for `$` or `settlement`, then there are zero matches.

### screen.queue — Queue

**Route:** `queue.html`
**Goal:** Which reports need a clerk click, and which are already decided?
**Entry / exit:** Nav Queue, overview KPI/heatmap. Row click → `route.claim`. Filters persist in `localStorage` `intake.filters.queue`.

**Layout**
- `lg`: page title + filter bar + table full `token.shell`
- `sm`: title, filters wrap, table scroll-x, sticky `id` column

```
[ title Reports ]
[ filters: decision | photos | send_state | chips | clear ]
[ table ]
[ status: N of 3 · last updated ]
```

**Regions**
- Title `Reports` + caption `Three kit files. Confirm is a human click.`
- `comp.filter-bar` fields:
  - `decision`: All / Open / Hold / Refuse (default All)
  - `photos`: All / On file / Missing
  - `send_state`: All / Draft / Numbered / Logged
- `comp.table` columns:

| Column | Field | Align | Sort | Example |
|---|---|---|---|---|
| Report | `id` | left, sticky | alpha | `CL-03` |
| Peril | `peril` | left | alpha | `glass` |
| Photos | `photos` | left | — | `On file` / `Missing` |
| Cover | `cover` | left | alpha | `PX-GLASS` |
| Decision | `decision` | left | alpha | badge Open |
| Send | `send_state` | left | alpha | `Draft` |
| Quoted line | `quote` | left | — | first 80 chars + ellipsis |

Row height ≥ 40px. Quote is not truncated for AT (`title` = full quote).

**States**
- loading: 3 skeleton rows
- empty: `No reports match these filters.` action `Clear filters`
- error: `Could not load reports.` `Retry`
- default: 3 rows

**Copy:** primary none (CTA in bar is `Open queue` current). Helper under title as above. Photos labels `On file` / `Missing` (never color-only).

**A11y:** `<table>` with `<th scope="col">`; row is `tr` with `tabindex="0"` and Enter opens claim. Decision badge includes the word Open/Hold/Refuse.

**Acceptance criteria**
- Given default filters, when the page loads, then CL-03, CL-04, CL-08 are visible in that order.
- Given Photos = Missing, when applied, then only CL-08 remains and a chip `Photos: Missing` can be cleared in one click.
- Given a row focused, when Enter is pressed, then the claim route for that id opens.

### screen.claim — Claim

**Route:** `claim.html?id=CL-03`
**Goal:** What is the engine decision for this file, and may the clerk confirm?
**Entry / exit:** Queue row, overview cards. Exit: Back to queue, Confirm, Undo, Ask.

**Layout**
- `lg`: 2 columns — main (photo, facts, quote) 2fr + score card 1fr
- `sm`: photo, facts, score card, actions (CTA already in bar)

```
[ back to queue ]
[ h1 CL-03 ] [ badge Open ]
[ photo 4:3 ]     [ score card ]
[ facts dl ]
[ quote block ]
[ confirm / undo note ]
```

**Regions**
- Facts (`dl`): Report, Peril, Photos, Cover, Decision, Send state, Claim number (`—` until minted), Received (`18 Sep 2026, 09:14 UTC`)
- Photo: `assets/glass.jpg` / `flood.jpg` / `collision.jpg` with alts in §10
- Quote: `<blockquote>` verbatim policy line
- `comp.score-card` for this id
- Note: `Confirm is the only way a claim number is minted. Refuse cannot be sent. Undo restores draft.`

**Actions**
- `Confirm` — POST `/api/confirm` `{id}` ; success toast `Claim number {claim_number} minted.` ; disabled if `!can_confirm` with reason `Refuse is not sent` (CL-04) or `Hold waits for photos` (CL-08)
- `Undo` — POST `/api/undo` `{id}` ; visible iff `can_undo`; toast `Returned to draft.`
- `Ask` — opens dialog with `id` context

**States**
- loading: photo muted, facts `—`
- empty: unknown id `No report {id} in fnol.json.` action `Back to queue`
- error: `Could not load this report.` Retry
- confirm error 400: toast `Refuse is not sent.` (exact), stay on page
- numbered: claim number `FNOL-CL-03-20260918T091422Z` (example format `FNOL-{id}-{YYYYMMDDTHHMMSSZ}`)

**Copy:** Back `All reports`. Headings use the id. Quote caption `Quoted from policy-excerpt.md`.

**A11y:** `h1` is the id; badge is text not color-only; Confirm is the first focusable in main after Back.

**Acceptance criteria**
- Given CL-03 draft, when Confirm is pressed, then a claim number matching `^FNOL-CL-03-` appears and Undo is enabled.
- Given CL-04, when Confirm is pressed, then the button stays disabled or the 400 message `Refuse is not sent` is shown, and no claim number appears.
- Given CL-08, when the page loads, then the score card shows a missed High item `Photos are missing` and Confirm is disabled.

### screen.policy — Policy excerpt

**Route:** `policy.html`
**Goal:** What may this desk quote?
**Entry / exit:** Nav Policy. Read-only.

**Layout:** title + 4 rule cards in a 1-column `token.prose` measure.

Each card: `h2` rule id, body the verbatim line from `policy-excerpt.md`, no paraphrase.

**States:** loading skeleton; empty `policy-excerpt.md is missing.` ; error `Could not load the rule book.` Retry. UI never offers an edit control.

**Copy:** Title `Policy excerpt`. Helper `The only rule book. Hooks block edits. Lookup is MCP lookup_rule.`

**Acceptance criteria:** All four lines appear verbatim, including `PX-GLASS.` `PX-FLOOD.` `PX-COLLISION.` `PX-NO-PAY.`

### screen.log — Live-ops log

**Route:** `log.html`
**Goal:** What already happened on this laptop, and does the log name money?
**Entry / exit:** Nav Log.

**Layout:** title, time range (global), table.

Columns: Time (relative + absolute title) | Report | Event | Detail

Events: `refuse_logged`, `confirmed`, `undone`, `ask_refused`. Detail is the quoted rule id or `Off-desk`. No amount fields.

Default rows after a fresh load: one `refuse_logged` for CL-04 (engine logs refuse once, not on GET). After confirm of CL-03, a `confirmed` row.

**States:** loading; empty `No events in this range.` Reset range; error Retry.

**Acceptance criteria:** Log JSON/UI has no keys `amount`, `payout`, `$`.

## 8. Components

### comp.button — Button
- Purpose: primary and secondary actions
- Anatomy: label + optional trailing arrow
- Props: `label` string required; `variant` `primary|ghost|danger`; `disabled`; `loading`; `href` or `onClick`
- Variants: primary filled `token.color-accent` / `on-accent`, height 44px, padding 12×16, radius pill; ghost transparent + border; danger ghost with `token.color-danger` text
- States: default, hover (`accent-hover`), focus (ring), disabled (opacity 0.45, `aria-disabled`, no pointer), loading (inline spinner, `aria-busy`)
- Keyboard: Enter/Space
- Do not use when an icon-only control is needed (`comp.icon-button`)

### comp.icon-button — Icon button
- 44×44, accessible `name` required (Menu, Close, Clear)
- States: default, hover, focus, disabled

### comp.kpi-tile — KPI tile
- Purpose: one number, one question
- Anatomy: caption `h3`, value `p.numeric`, helper `p`
- Props: `caption`, `value` (number or `—` / `!`), `helper`, `href` optional
- Drillable iff `href` set; then the whole card is a link. Non-drillable tiles are not clickable.
- States: default, hover (if link), loading (`—`), empty (`0`), error (`!` + helper `Could not load`)
- Token: surface on bg, **no accent fill**, no border; 1px divider under caption only

### comp.table — Table
- Real `<table>`; sticky header `token.color-bg`; sortable button in `<th>` when sort=true
- Numeric columns right-aligned + tabular nums (none in queue except counts in status)
- States: default, loading skeletons, empty, error
- Page size: all rows (3); no pager unless log exceeds 50, then page size 50

### comp.filter-bar — Filter bar
- Selects apply **on change** (no Apply button) on queue
- Applied values render as `comp.chip`; one-click clear all `Clear filters`
- Persist per screen

### comp.chip — Chip
- Pill, caption `Photos: Missing`, trailing × (`Clear {label}`)
- Radius pill, height 32px (filter chip; still inside a 44px hit row)

### comp.time-range — Time range
- Placement: top bar right, before CTA
- Options: `Last 7 days` (default), `Last 30 days`, `Last 90 days`, `This shift` (since 06:00 local)
- Changing it refetches every widget on the current view
- Persist `intake.timeRange`
- `sm`: compact select, still labelled `Time range`, not an unlabeled icon

### comp.chart — Chart
- SVG only (no chart library)
- Max 3 series: open / hold / refuse
- Colors from chart tokens; average line `token.color-chart-avg`
- Gridlines `token.color-border`; no 3D, no gradient fills
- Title + helper + `Source:` caption
- States: loading, empty `No points in this range.`, error + Retry
- Include a data table for AT

### comp.badge — Badge
- `open` success, `hold` warning, `refuse` danger, `off-desk` muted
- Text label always; color is extra
- Radius pill, type caption, padding 4×8

### comp.empty-state — Empty state
- Title, body, one action
- Used for empty, error (action Retry), loading (no action, `role="status"`)

### comp.toast — Toast
- 4s (`4000ms`), pause on hover/focus; role `status` for ok, `alert` for error
- Confirm, undo, ask-refused, API errors
- Not used for navigation

### comp.heatmap — Heatmap grid
- CSS grid, gap 8px, cell min-height 88px, radius sm
- Inner: label + numeric weight/id
- Dark cells (`heat-3`, `heat-4`) use `token.color-on-accent`
- Keyboard: each cell a link

### comp.step-card — Numbered step
- Anatomy: index `01` muted, title, body
- Background `token.color-surface-muted`, padding 24px
- Not clickable

### comp.score-card — Scored checklist
- Purpose: show why this file is open, hold, or refuse (source “90% quality” widget, FNOL content)
- Anatomy: eyebrow (report id + peril), large decision word (not a percent), progress bar of high-importance items passed, list of checks
- Props: `id`, `decision`, `items[]` `{ text, passed, importance: high|medium|low }`
- CL-03 items:
  - Photos are on the file · pass · high
  - Cover is PX-GLASS · pass · high
  - Quote is the PX-GLASS line · pass · high
  - No payout language · pass · high
  - Claim number minted · fail (until confirm) · low
- CL-04 items:
  - Peril is flood · pass · high
  - Quote is the PX-FLOOD line · pass · high
  - Confirm is blocked · pass · high
  - Logged, not sent · pass · high
- CL-08 items:
  - Cover is PX-COLLISION · pass · high
  - Photos are on the file · fail · high
  - Quote is the PX-COLLISION line · pass · high
  - Decision is hold · pass · high
- Importance pills: High `token.color-success` on light green `#E5F3EC`; Medium `#9A5B12` on `#F8EEDC`; Low muted
- Missed items use a text `Miss` plus `token.color-danger`, not color alone
- Progress bar: `(passed high) / (high total)` — CL-03 = 4/4, CL-04 = 4/4, CL-08 = 3/4
- Large word: `Open` / `Refuse` / `Hold` (never a copied `90%`)

### comp.example-card — Example report
- Eyebrow `{peril} · {decision} · {photos label}`
- Title = id
- Body = one-sentence clerk prompt (Copy on overview)
- Footer `Expected: {decision}. Quote {cover}.`
- Entire card links to claim

### comp.ask-dialog — Ask
- Modal, role `dialog`, labelled `Ask the desk`
- Field: textarea `Question` (required)
- Submit `Check question` → `/api/ask` `{ text }`
- Results: `refuse` + `PX-NO-PAY` quote for payout-family; `refuse` + `No rule line matched` for medical/legal; otherwise the engine decision for a named id if present
- Esc / backdrop click closes; focus trap
- Empty submit: inline `Write a question first.`

## 9. Flows

1. Land on Overview → change time range to Last 90 days → KPIs, heatmap, charts refetch (same three reports; last updated ticks). Change to a custom empty window via `?state=empty` in demo → empty copy → `Reset to last 7 days` restores.
2. KPI `Reports in queue` → Queue (filters default). Heatmap `Collision · CL-08` → Claim CL-08. Back → Queue with previous filters.
3. Queue: set Photos = Missing → chip `Photos: Missing` → only CL-08 → Clear filters → 3 rows.
4. Empty range / error / retry: Overview `?state=error` shows Retry on KPIs and charts; Retry removes the query and reloads fixture. Queue empty filters show `No reports match these filters.`
5. Confirm path: Queue → CL-03 → Confirm → toast with `FNOL-CL-03-…` → Undo → draft. CL-04 Confirm does not mint.
6. Ask: Ask → `will we pay?` → refuse + verbatim `PX-NO-PAY. Never write “we will pay” or name a settlement amount.`

## 10. Data contract

| Entity | Fields used in UI | Source screen/component |
|---|---|---|
| Report | `id` string `CL-03`; `peril` `glass\|flood\|collision`; `photos` bool; `cover` `PX-GLASS\|PX-FLOOD\|PX-COLLISION`; `decision` `open\|hold\|refuse`; `quote` string verbatim; `send_state` `draft\|numbered\|logged`; `claim_number` string\|null; `can_confirm` bool; `can_undo` bool; `received_at` ISO-8601; `photo` path | queue, claim, heatmap, examples |
| PolicyLine | `id` `PX-*`; `text` verbatim line including the id prefix | policy, quote, ask |
| LogEvent | `ts` ISO-8601; `id` report or null; `event` `refuse_logged\|confirmed\|undone\|ask_refused`; `detail` string (rule id or `Off-desk`) | log |
| ShiftKpi | `reports_in_queue` int; `rules_in_force` int; `photos_on_file` int; `updated_at` ISO-8601 | overview KPIs |
| AskResult | `decision` `open\|hold\|refuse`; `rule_id` string\|null; `quote` string | ask dialog |

Display rules:
- Integers: `3` (no decimals)
- Percents: not used (score card uses `3 / 3 high checks`)
- Currency: **forbidden**
- Deltas: not used (no prior period in the kit)
- Timestamps: lists `3m ago`; detail/hover `18 Sep 2026, 09:14 UTC`
- Photos: `true` → `On file`; `false` → `Missing`
- Claim number empty: display `—`

Fixture `received_at`:
- CL-03 `2026-09-18T09:14:00Z`
- CL-04 `2026-09-18T09:31:00Z`
- CL-08 `2026-09-18T10:02:00Z`

Image alts:
- `hero.jpg`: `Claims office desk with a cork board of vehicle photos, a closed laptop, and stacked folders at dusk.`
- `glass.jpg`: `Spiderweb crack across a car windshield, viewed from the passenger seat.`
- `flood.jpg`: `Silver sedan in knee-deep floodwater on a residential street.`
- `collision.jpg`: `Silver hatchback with a crumpled rear bumper in an empty parking lot.`
- `tray.jpg`: `Policy binder, clipboard, and photo sleeve on an oak desk.`

## 11. Implementation notes
- Files: `web/index.html`, `web/queue.html`, `web/claim.html`, `web/policy.html`, `web/log.html`, `web/desk.css`, `web/desk.js`, `web/desk.json`, `web/assets/*`
- Shared chrome injected by `desk.js` `mountShell({ current, cta })`
- Client state keys: `intake.timeRange`, `intake.filters.queue`, `intake.desk.v1` `{ [id]: { send_state, claim_number } }`
- Filters apply on change
- Charts: inline SVG, series colors from tokens
- Data adapter: `DeskData.load()` tries `/api/queue` then `desk.json`
- Demo states: `?state=loading|empty|error` on any page
- Serve locally: `python3 -m http.server 8788 --directory web --bind 127.0.0.1`

## 12. Out of scope
- Python engine, MCP, hooks, Bot, and `serve_desk.py` (planned PRs)
- Login, roles, and multi-tenant orgs
- Marketing homepage, cookie banner, partner logos, model-lab comparisons
- Payout calculators, reserves, and any dollar UI
- Editing `policy-excerpt.md`
- Inventing reports beyond CL-03, CL-04, CL-08
- Pixel-perfect tracing of the source Framer file or copying its wordmark, statue image, or green

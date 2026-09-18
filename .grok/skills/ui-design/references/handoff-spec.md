# Handoff spec format

Write one markdown file a coding agent can implement without reading the chat. Use these sections **in this order**. Omit a section only when it cannot apply (say why in Assumptions).

Stable IDs: `screen.overview`, `comp.kpi-tile`, `token.color-accent`, `route.list`. Coding agents copy these names into code.

## Document skeleton

```markdown
# Dashboard design: <product name>

## 0. Meta
- Product:
- Audience:
- Primary question the dashboard answers:
- Platform: web dashboard, desktop-first
- A11y target: WCAG 2.2 AA
- Locale / number format:
- Stack to match (or "greenfield"):
- Mode: create | replicate (<source URL>)
- Spec status: complete | partial (<what's out>)

## 1. Assumptions
- ...

## 2. Open questions
- Q: ... Options: ... Default if unanswered: ...

## 3. Tweaks (replicate only)
Table: Keep vs Change. Every personal tweak lives here (brand, color, type, spacing, usability fixes). IA/layout that stays faithful is listed under Keep.

## 4. Design tokens
### Color
| Token | Value | Use |
|---|---|---|

### Typography
| Token | Font | Size | Line-height | Weight | Use |
|---|---|---|---|---|---|

Include a `numeric` row: tabular lining, the size used in KPI values and table cells.

### Space, radius, elevation, motion, z-index, breakpoints
Tables with token, value, use. Each breakpoint: one sentence on layout change.

## 5. Information architecture
- Sitemap (nested list)
- Route table: ID | Path | Screen | Auth
- Sidebar items in order: label, destination, icon name, badge rule if any
- Global controls: time range, search, user menu

## 6. Global shell
Sidebar, top bar, time-range control, filter chip row, toasts:
- Placement per breakpoint
- Contents (left → right / top → bottom)
- Components used
- States: default, collapsed sidebar, drawer-open (`sm`), scrolled, nav current
- Keyboard / focus
- Copy

## 7. Screens
One `### screen.<id> — <name>` per screen. Each MUST include:

**Route:** path
**Goal:** one sentence (the question this view answers)
**Entry / exit:** how users arrive; where KPIs, rows, and CTAs go

**Layout**
- `lg`: named regions left → right, top → bottom
- `sm`: block order
- ASCII wireframe for `lg` (and `sm` if it reflows)

**Regions** (for each)
- Components (IDs)
- Data fields (name, type, example that looks real)
- Actions (label, dest or event)

**States:** default, loading, empty, error, plus screen-specific (no permission, no data in range, widget failure). For each: what the user sees and the recovery action.

**Copy:** every label, heading, button, helper, empty/error string. Final English (or specified locale).

**A11y:** heading outline, landmarks, table header rules, focus order (numbered).

**Acceptance criteria:** given / when / then.

## 8. Components
One `### comp.<id> — <name>` per shared component:

- Purpose, anatomy
- Props / data: name, type, required, example
- Variants and states (default, hover, focus, disabled, loading, empty, error, selected — only those that apply, none implied)
- Behavior (click, keyboard)
- Token usage
- Do not use when... (if a similar component exists)

Minimum dashboard set when those surfaces are in scope: `comp.button`, `comp.icon-button`, `comp.kpi-tile`, `comp.table`, `comp.filter-bar`, `comp.chip`, `comp.time-range`, `comp.chart`, `comp.badge`, `comp.empty-state`, `comp.toast`.

## 9. Flows
Numbered steps with screen IDs. At least:

1. Land on Overview → change time range → widgets refresh
2. KPI or table row → Detail (with filters preserved)
3. Apply filters on List → chips appear → clear
4. Empty range / error / retry

Each step: user action, system response, destination.

## 10. Data contract
| Entity | Fields used in UI | Source screen/component |
|---|---|---|

Include display rules: percent decimals, currency, delta vs previous period, timestamp format.

## 11. Implementation notes
- File/route mapping if the stack is known; otherwise `app/shell`, `app/overview`, `ui/kpi-tile`
- Client state: time range, per-screen filters, sidebar collapsed, open drawer
- Forms/filters: apply on change vs Apply button (pick one per screen and stick to it)
- Charts: library only if the repo has one; otherwise specify SVG/CSS and the series colors from tokens

## 12. Out of scope
Bullet list so the coding agent does not invent marketing pages, a public homepage, or backend jobs.
```

## Density rules

- Shared layouts: write once, diff the second screen (`Same as screen.list except...`)
- Example values look real (`"Acme North"`, `1,240`, `+4.2% vs prior 7d`)
- Quantities: default page size, KPI count, series max, toast duration (ms)
- No TBD in a required field. Use an assumption and list it in §1

## Done check (author must pass before saving)

- A coder can build each in-scope screen without inventing a token, route, label, or state
- Every data view has loading, empty, and error
- Every number has a unit/format and tabular nums
- Time range is specified (placement, defaults, what it refetches)
- Contrast and hit targets are stated via tokens
- Replicate mode: §3 lists every tweak; IA matches the source unless a Keep/Change row says otherwise

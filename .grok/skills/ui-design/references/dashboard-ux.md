# Dashboard UX (apply; do not paste into the spec)

Pass/fail while designing. The spec cites decisions; it does not lecture.

## Easy to use

- **One question per view.** The Overview answers "how are we doing?" The List answers "which items?" The Detail answers "what about this one?"
- **Stable chrome.** Sidebar destinations and the time-range / global filter stay put across screens. Do not invent a second nav.
- **Time range lives top-right of the content pane**, not buried in a page. Default: last 7 days, with 30d / 90d / custom. Changing it refetches every widget on the view.
- **Filters as chips** once applied. One-click clear. Default filters should already show a useful picture (not an empty table).
- **KPI → drill-down.** A metric tile that has a breakdown is a link (or button) to the List or Detail pre-filtered. Tiles that are not drillable are not clickable.
- **Tables:** sortable columns, sticky header, row click → Detail. Numeric columns right-aligned with tabular nums. Primary identifier left-aligned and sticky if the table is wide.
- **Hick:** sidebar ≤ 7 top-level items. Extra destinations go under a group, not a second icon rail.
- **Fitts:** hit targets ≥ 44×44 CSS px for icon buttons in the shell; table row height ≥ 40px; filter controls not sub-32px.
- **Status always visible:** last updated, applied filters, and page of N. Failed widgets show an inline error with retry, not a blank card.
- **Recognition:** persist the last time range and filters per screen in the spec as client state. Do not make the user re-select on every visit.
- **One primary action per view** (Export, Create, Save). Style it as the only filled accent button. Secondary actions are ghost or icon-button.

## Attractive (taste floor)

Dashboards fail when they look like a component-library demo. Tune chrome so data is the hero.

- **Surfaces, not boxes.** Page `color-bg` and card `color-surface` must differ enough to see hierarchy without a border on every card. Use a 1px `color-border` only to separate table rows or inset controls — not as a frame around the whole page.
- **One accent.** `color-accent` is for the primary action, current nav item, and focus ring. It is not a fill for KPI tiles, charts, and links all at once.
- **Type:** UI sans for chrome (`h1`–`h3`, `body`, `caption`). **Tabular lining figures** on every number (`font-variant-numeric: tabular-nums`). Do not use a display/serif face in a dashboard unless Replicate requires it.
- **Type scale is small and tight.** Overview title ~20–24px, KPI value ~28–36px, table body 13–14px, caption 12px. Do not scale marketing-site `display` sizes into a data UI.
- **8px spacing scale.** Compact density: card padding 16px, section gap 24px, control gap 8px. No one-off `13px`.
- **Radius 6–8px** on cards and controls. Pills only for filter chips and status badges.
- **Charts:** at most 6 categorical series. Colorblind-safe (not rainbow). Sequential for magnitude, categorical for series, diverging for plus/minus. Gridlines muted; no 3D, no gradient fills on bars.
- **Status color is semantic only:** success / warning / danger for states, never as decoration. Contrast still ≥ 4.5:1 for text on those surfaces.
- **No decorative heroes, blobs, or glassmorphism** behind numbers. No purple-gradient "AI" chrome unless the source site in Replicate mode actually uses it and the user wants fidelity.

Default greenfield palette (override with brand or with Replicate tweaks):

| Role | Value | Use |
|---|---|---|
| color-bg | `#0F1419` | Page |
| color-surface | `#1A2129` | Cards, sidebar, top bar |
| color-surface-hover | `#222B35` | Row / nav hover |
| color-text | `#F2F5F8` | Primary text |
| color-text-muted | `#8B9AAB` | Meta, axis, timestamps |
| color-border | `#2A3540` | Dividers, table lines |
| color-accent | `#3D9CF0` | Primary action, current nav, focus |
| color-success | `#3DDC97` | Positive delta, healthy |
| color-warning | `#F5C14A` | Degraded |
| color-danger | `#F07178` | Negative delta, error |
| color-focus | `#3D9CF0` | 2px focus ring |

Light theme is allowed when the user asks or the source site is light: invert surfaces, keep the same roles, re-check contrast.

## Feedback and states

Every data-backed region has **loading**, **empty**, **error**, **partial** (one widget failed), and **populated**. Spec the copy and the recovery action for each.

Every action has a visible result: spinner on the control, optimistic row, or toast. Toasts are for confirmation of writes/exports, not for navigation.

## Accessibility (WCAG 2.2 AA)

- Text contrast ≥ 4.5:1 (3:1 for ≥24px / 19px bold). Charts and UI chrome ≥ 3:1 against adjacent surfaces
- Name, role, value on every control. Icon-only buttons have an accessible name
- Do not encode meaning with color alone (delta arrows + text, not just red/green)
- Tables: real `<table>` or grid with row/column headers. KPI tiles are headings + values, not unlabeled div soup
- Keyboard: tab order matches visual order; Esc closes menus/dialogs; skip link to main. Sidebar is a `nav`
- Focus: 2px `color-focus` ring. Never `outline: none` without a replacement
- `prefers-reduced-motion`; UI motion ≤ 200ms

## Responsive

| Token | px | Layout change |
|---|---|---|
| sm | 375 | Single column; sidebar becomes a drawer; tables scroll horizontally with sticky first column |
| md | 768 | Content + optional filter rail; sidebar may still be drawer |
| lg | 1280 | Persistent sidebar (240px) + main. KPI row up to 4 across. Table uses full width |
| xl | 1440 | Wider main; do not stretch a 4-KPI row to 6 empty cards |

Primary action stays visible at `sm` (top bar or sticky footer). Do not hide the time range behind an unlabeled icon.

## Content

Write the actual microcopy. Sentence case. Verbs on buttons (`Export CSV`, `Apply`, `Retry`).

Numbers always have a unit or a defined format (`1,240` requests, `12.4%`, `$1,240.00`). Deltas include direction and period (`+4.2% vs prior 7d`).

Timestamps: relative in lists (`3m ago`) with absolute on hover/detail (`18 Sep 2026, 14:03 UTC`).

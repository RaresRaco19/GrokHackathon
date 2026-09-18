---
name: ui-design
description: >
  Design dashboard UI/UX: write a design spec and, when needed, a full frontend
  that is attractive and easy to use. Use when creating a dashboard from scratch
  or when given a URL to analyze and replicate with small personal tweaks
  (branding, color, type, spacing) while keeping the original information
  architecture. Trigger phrases: dashboard UI, dashboard UX, design a dashboard,
  replicate this site, clone this URL, UI spec, frontend from URL. Use when the
  user runs /ui-design.
---

# Dashboard UI/UX

Produce a coding-agent-ready **dashboard spec**. Also build a **full frontend** when step 0 says to.

Read before designing:

- `references/dashboard-ux.md` — taste and usability (apply, do not paste)
- `references/handoff-spec.md` — spec shape
- `references/replicate.md` — only when a URL is in the request

Do not restate those files in the spec. Use them.

## 0. Mode

**Create** if there is no URL. **Replicate** if the user gave a URL (or said clone/replicate this site). Follow `references/replicate.md` before writing the spec.

**Spec always.** Build frontend when any of these is true:

- The user asked to build, implement, code, or ship a working UI
- Mode is Replicate (the replica is the point), unless they said spec-only

If only a spec was requested, write it and stop. Offer to implement from that file.

## 1. Ground in the repo

If a codebase exists, inspect routes, shell, component library, tokens, and stack. Match them. Invent a system only when none exists.

User-supplied brand, screenshots, copy, and named tweaks override defaults and override source-site chrome in Replicate mode.

## 2. Ask only for blockers

Infer the rest; list inferences under **Assumptions**. Ask only if a missing fact would change IA or the screen set (what the dashboard is for, who uses it, URL vs greenfield). One round, then design.

## 3. Defaults (when unspecified)

- Web dashboard, **desktop-first**, responsive down to `md` (768). `sm` is a usable single-column, not a phone-first marketing layout
- Authenticated app shell: sidebar + top bar
- WCAG 2.2 AA
- Locale `en-US`. Numbers: tabular lining, thousands separators, explicit units
- Greenfield screen set when the user did not name screens: **Overview**, **List/table**, **Detail**. Add **Settings** only if the job includes configuration
- Replicate screen set: whatever the source site actually has (see `references/replicate.md`)
- Density: compact. One accent color. Tabular numbers on every metric

## 4. Design, then write

Work in this order, then emit one spec that follows `references/handoff-spec.md`:

1. Job of the dashboard and the primary question it answers
2. Tokens
3. IA: routes, nav, permissions if any
4. App shell (sidebar, top bar, filters/time range, toasts)
5. Each in-scope screen
6. Shared components
7. Key flows (filter, drill-down, empty/error recovery)
8. Accessibility and responsive behavior
9. Implementation notes and acceptance criteria

Every value a coder needs must be explicit: token names, hex/rem, breakpoint px, routes, component names, field names, empty/loading/error copy. No lorem. No "make it nice".

Apply every check in `references/dashboard-ux.md` before saving.

## 5. Visuals

Do not use image generation for UI that contains real labels, numbers, or structure.

If you are not building the frontend this turn, put ASCII or CSS-grid wireframes in each screen section of the spec.

## 6. Write the spec to disk

Path: user-specified path, else `docs/ui-design.md` when `docs/` exists, else `ui-design.md` at the workspace root.

Overwrite only a spec this skill wrote, or when the user asked to replace it. Otherwise write `ui-design-<slug>.md` beside it.

## 7. Frontend (when step 0 says to)

Implement the in-scope screens from the spec, not from chat paraphrase.

- Match the repo stack if one exists. If greenfield, use semantic HTML + CSS (or the project's existing framework) with the spec's tokens as CSS variables
- Real labels and example data from the spec. No lorem, no unlabeled gray boxes
- Include loading, empty, and error states for every data view
- Desktop layout first; `sm` must remain usable
- After UI work, verify in the browser if browser tools exist: navigate, click primary filters, open a detail, hit an empty state. If no browser tools, say what you could not click

## 8. Report

After writing (and building, if any):

- Absolute path to the spec
- Screens covered
- Create vs Replicate; in Replicate, the source URL and the tweak list
- Assumptions that most affect implementation
- Frontend path(s) if built
- That a coding agent should implement **from the spec file**, not from chat paraphrase

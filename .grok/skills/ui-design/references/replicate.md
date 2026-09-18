# Replicate a dashboard from a URL

Run this **before** the spec when the user gave a URL. Goal: same information architecture and layout, with small personal tweaks — not a pixel-perfect stolen skin, and not a redesign.

## 1. Capture the source

1. Fetch the URL with `web_fetch` and `open_page` (use both: structure + visible text).
2. Follow primary nav links that are dashboard surfaces (overview, lists, details, settings). Skip marketing, docs, and login-only walls you cannot pass. If auth blocks the app, capture the public marketing/dashboard preview if any, and record **auth-gated** as an assumption.
3. Inventory, as facts, not vibes:

| Capture | What to write down |
|---|---|
| IA | Nav items in order, routes if visible, screen list |
| Shell | Sidebar vs top nav, presence of search, time range, user menu |
| Layout per screen | Region names and order (KPI row, chart, table, side panel) |
| Widgets | KPI labels, chart types, table columns, filters |
| Chrome | Color roles (bg/surface/text/accent), type vibe (sans/size/density), radius, dark vs light |
| Interaction | What is clickable, drill-downs, filter behavior |
| Gaps | Missing empty states, poor contrast, tiny targets, unlabeled icons |

Do not invent screens the source does not have.

If the page is not a dashboard (marketing site, docs, blog), say so, extract any app-like IA you can, and design a **dashboard** that serves the same product job — still list what came from the URL vs what you added.

## 2. Keep vs tweak

**Keep (faithful):**

- Screen set and why each exists
- Nav structure and order
- Region layout (KPI row above table, etc.)
- Widget types (these KPIs, this table, this chart kind)
- Primary flows (filter, drill-down)

**Tweak (always apply these four, unless the user forbids a row):**

| Axis | What to change |
|---|---|
| Brand | Product name, logo slot, and user-supplied identity. Do not copy the source logo or trademarked wordmark |
| Color | Keep role structure (bg/surface/text/accent). Retune values to the taste floor in `dashboard-ux.md` (or the user's brand). Do not copy a competitor's trademark palette unless the user asked for fidelity |
| Type | Named UI sans + tabular nums from `dashboard-ux.md`. Keep the source's density intent (compact vs roomy) |
| Spacing | Normalize to the 8px scale. Fix inconsistent source padding; do not change region order |

**Usability fixes (allowed, record each in spec §3):** missing empty/error/loading, contrast failures, hit targets < 44px, unlabeled icon buttons, color-only meaning. These are tweaks, not IA changes.

**Do not:** add screens, restyle as a marketing landing, drop the table "because cards are nicer", or rearrange nav "for taste".

User-named tweaks override this table.

## 3. Assets and legal

- Replace source logos, photos, and custom illustrations with a named placeholder (`logo.product`, `avatar.user`)
- Keep generic chart shapes and table structure
- Do not scrape behind a login or bypass paywalls
- Example data in the spec is **realistic fiction** in the same domain, not copied customer records from the page

## 4. Then design

Hand the keep/tweak table to the spec as **§3 Tweaks**. Tokens come from the tweak palette, not from sampling hex off a competitor unless fidelity was requested. Continue at SKILL.md step 4.

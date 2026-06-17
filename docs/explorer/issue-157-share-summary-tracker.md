# Issue #157 — Share summary tracker

Living document for the social media summary feature. Update this file as ideas land and work completes.

**GitHub issue:** [#157 — Social Media Summary Generator](https://github.com/jimchurches/myebirdstuff/issues/157)

**Implementation sub-issues:**

| Phase | Issue | Scope |
|-------|-------|--------|
| 0 | [#273](https://github.com/jimchurches/myebirdstuff/issues/273) | Foundation — compute, layouts, tests, design app |
| 1 | [#274](https://github.com/jimchurches/myebirdstuff/issues/274) | Period stats hardening |
| 2 | [#275](https://github.com/jimchurches/myebirdstuff/issues/275) | Playwright PNG export |
| 3 | [#276](https://github.com/jimchurches/myebirdstuff/issues/276) | Social Cards tab in main app |
| 4 | [#277](https://github.com/jimchurches/myebirdstuff/issues/277) | v1 polish — stat picker, favourite birds, layout tuning |

**Prototype branch:** `157-social-summary-prototype` → PR for #273 to `beta-next`

**Design app:**

```bash
streamlit run explorer/app/streamlit/design_share_summary_app.py
```

---

## Status at a glance

| Area | Status | Notes |
|------|--------|-------|
| Layout mockups (HTML) | **Done (prototype)** | Hero, tiles, minimal, spotlight |
| Aspect ratios | **Done (prototype)** | Square post, portrait post, story |
| App logo on card | **Done (prototype)** | Footer banner only (no top-right corner) |
| Period: yearly | **Done (prototype)** | From CSV or sample data |
| Period: monthly | **Done (prototype)** | `compute_share_summary_stats` |
| Period: weekly | **Done (prototype)** | Sun–Sat weeks; title `May 31, 2026 - June 6, 2026` |
| Period: custom / trip | **Done (prototype)** | Date range + trip title as green subtitle |
| Longest streak (year/month) | **Agreed** | Summary row when applicable; not week/custom v1 |
| Birding days | **Done (prototype)** | Unique checklist days; label “Birding days” |
| Countries | **Done (prototype)** | All period types; default on tiles/minimal |
| World bird coverage | **Summary row only** | Available stat; not on card tiles by default |
| Favourite bird(s) | **Roadmap** | Pure user pick (up to 3); choices from period species list |
| PNG generation | **Done (design app)** | `share_summary_png_export.py` — Playwright HTML→PNG at 1080px formats |
| PNG save UX | **Done (design app)** | **Export current card** below preview — PNG regenerated inside `@st.fragment` (Streamlit disallows sidebar inside fragments) |
| Main app integration | **Design noted** | New **Social Cards** tab before Settings; tab-aware sidebar TBD |
| Map thumbnail on card | **Dropped (v1)** | v2 |
| Compare to last year | **Dropped (v1)** | v2 |
| Custom @handle watermark | **Dropped (v1)** | v2 |
| Media uploads | **Dropped** | Not in eBird observation CSV |
| User picks stats on card | **Agreed (v1)** | Defaults per layout; picker UI TBD |
| Current vs previous period | **Done (design app)** | Radio for year/month/week; default via `suggest_period_anchor()` |
| Colour schemes | **Config in defaults.py** | Index tunable; no UI yet |
| Multiple themes (light/dark) | **Config only** | Add entries to colour scheme array |
| User picks layout in app | **Agreed (v1)** | Hero grid, Stat tiles, Minimal list, **Spotlight** |

---

## Decisions (2026-06-09)

Captured after second prototype review — closes most open layout/stat questions.

### Dropped / deferred

- **Media uploads** (photos/sounds per month) — not in observation CSV; idea dropped.
- **Map thumbnail** on card — v2.
- **Compare to last year** — v2.
- **Custom watermark / @handle** — v2.
- **Colour scheme UI** — v2 (config-only for now; see Colours).
- **App-wide mobile UX** — out of scope; Social Cards tab should still be phone-friendly.

### Default stats per layout

Configured in ``explorer/core/share_summary_defaults.py`` (re-exported from ``defaults.py``) as ``SHARE_SUMMARY_HERO_DEFAULT_STATS`` / ``SHARE_SUMMARY_TILES_DEFAULT_STATS``.

| Layout | Default stats (in order) |
|--------|--------------------------|
| **Hero** (4 tiles) | Total species, Lifers, Total checklists, Unique locations |
| **Stat tiles** (6) | Above + Countries, Birding days |
| **Minimal list** (6) | Same as stat tiles |
| **Spotlight** | **Lifers** (``SHARE_SUMMARY_SPOTLIGHT_STAT_DEFAULT``) |

Users will eventually pick stats from the full catalogue; defaults above are the starting point.

**Birding hours** — computed and shown in the **summary metrics row** (all available stats with values); **not** on card tiles by default.

### Available stats catalogue (v1 target)

All should appear in the summary row (with values) so users can pick interesting items for custom cards.

| Stat | Scope | In compute today? | On card default? |
|------|-------|-------------------|------------------|
| Total species | Period | Yes | Yes (hero/tiles) |
| Lifers | Period | Yes | Yes |
| Total checklists | Period | Yes | Yes |
| Unique locations | Period | Yes | Yes |
| Countries | Period | Yes (all period types) | Yes (tiles/minimal) |
| Birding days | Period | Yes | Yes (tiles/minimal) |
| Total individuals | Period | Yes | No |
| Total bird families | Period (taxonomy map) | Yes | No |
| Birding hours | Period | Yes | **Summary only** |
| Total distance (km) | Period (**year** and **lifetime** only) | Yes | No |
| Longest streak (days) | Period (year/month/lifetime) | Yes | No |
| Shared checklists | Period | Yes | No |
| Days birding with others | Period | Yes | No |
| World bird coverage | All-time (taxonomy) | Yes (summary row) | No |
| Total species (from taxa) | All-time | Yes (summary row) | No |
| Observed species (from taxa) | All-time | Yes (summary row) | No |
| Total families (from taxa) | All-time | Yes (summary row) | No |
| Favourite bird(s) | User pick (≤3) | Roadmap | No |
| Trip title | User text (custom range) | Yes | Replaces green subtitle |

**Note:** “Total bird families” (period) and “Total families (from taxa)” (all-time list) are **different metrics** — both may be offered; labels must distinguish them.

**Also discussed, not in list above:** spotlight single-stat cards (“Year birds”, etc.) — layout choice, not a separate metric. **Label fine-tuning:** custom/trip species spotlight uses **Species** (not “Birds”) to match other layouts; year/month/week still use “Year birds” / “Month birds” / “Week birds” — revisit during tuning.

### Roadmap ideas (not scheduled)

**Best day / best checklist (card stat)** — Rankings in the main app link to the checklist or date on eBird; that context is valuable. As a card highlight without links, a possible pattern: tile title **Best day**, value only (e.g. `97 species` or `2,506 individuals`) — no date, no URL. Deferred until card UX is clearer.

**Geographic scope (states / provinces)** — Not just another stat: a **period constraint** like custom date range. Examples: “Australian” year, “New South Wales” lifetime — filter all stats to a country or state/province before computing the card. Touches period resolution, sidebar controls, and sample/live data paths; on author todo list separately from v1 stat catalogue.

### Countries

- **Default** on stat tiles and minimal list for **all period types** (year, month, week, custom).
- May revisit after user testing (previously year-only).

### Longest streak

- **Agreed:** computed for **year and month** periods only (matches Yearly Summary / checklist-stats logic).
- Shown in the **summary metrics row** when applicable; **not** on default card tiles.
- **Week and custom/trip** periods do not get longest streak unless compute is extended later — no plan to do that for v1.

### Logo & titles

- **Logo:** footer banner only (logo + “Personal eBird Explorer”). **No** top-right corner logo.
- **Green subtitle** (smaller heading): period flavour text — “Birding year in review”, “Monthly birding summary”, etc.; or **trip title** on custom ranges.
- **Large headline:** always the period label — year, month name, weekly date range, or custom date range.
- **Trip title:** replaces the **green subtitle** on **all layouts** (hero, tiles, minimal, spotlight). Layout-specific subtitles (“My birding stats”, “Summary”) apply only when no trip title is set.
- **Weekly title:** Sun–Sat week; format ``May 31, 2026 - June 6, 2026`` (same visual weight as year/month headlines).
- **Custom date range:** compact range as large headline (existing ``format_custom_date_range``); trip title in green subtitle when set.

### Colours

- Current palette looks good for v1.
- Schemes live in ``explorer/core/share_summary_defaults.py`` → ``SHARE_SUMMARY_COLOR_SCHEMES`` (array of dicts: ``bg``, ``bg_alt``, ``text``, ``muted``, ``border``, ``accent``).
- Active scheme: ``SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT`` (flip index to test new schemes without code changes).
- **No UI control** for colour schemes yet.
- **Dark theme:** add a second entry to the array when a good palette exists; otherwise mark v2 with colour-scheme work.

### Period selection — current vs previous

Control for **current period** vs **previous period** (radio in design app; Social Cards tab wording TBD).

Example: on Saturday afternoon finishing the birding month → “current month”; on 2 June posting May results → “previous month”. Same for year/week.

**Default anchor** (`suggest_period_anchor` in `share_summary_compute.py`, reference = today): month → previous if day ≤ 7 else current; year → previous if 1–14 January else current; week → current on Sat/Sun, previous on Mon/Tue, else current.

Period resolved via `resolve_period()` relative to reference date (design app uses `date.today()`).

### Card layout iteration (still open)

- Hero 4-tile grid may need **sizing** to reduce blank space (same for 6-tile stat card).
- Square layout might fit **9 tiles** (room for favourite-bird slot later); portrait/story differ.
- Per-layout iteration expected during user testing.

### Controls & sidebar (still open)

- Exact control layout (sidebar vs in-tab vs hybrid) TBD.
- If sidebar: show **Social Cards controls only on Social Cards tab**; restore map controls elsewhere; preserve session state when switching (see Tab-aware sidebar section).

---

## User feedback (2025-06-09)

Captured from initial prototype review:

- **Direction confirmed** — mockups are the right idea; good starting point, tuning expected.
- **Logo** — include Personal eBird Explorer logo on the image (can be small). ✅ Added in prototype (corner + footer).
- **Aspect ratios** — want all three:
  - **Story** — 1080×1920 ✅
  - **Post (square)** — 1080×1080 ✅
  - **Post (portrait)** — 1080×1350 (4:5 Instagram feed) ✅
- **Periods** — yearly, monthly, weekly, and custom date range (trip report). ✅ Scaffolded in design app + `share_summary_compute.py`.
- **Layouts** — user selects from **Hero grid**, **Stat tiles**, **Minimal list**, **Spotlight** (all agreed for v1).
- **Spotlight species label** — period-aware: Year / Month / Week birds; **Species** for custom/trip range.
- **Single-stat images** — ideas only for now (“Year birds”, “Lifers this year”, etc.). ✅ **Spotlight** layout added as a sketch.
- **Community research** — user plans to look at what others have done with external tools before locking stats/layout.
- **Trip title (custom range)** — optional name shown on the card **with** the date range, not instead of it. Examples:
  - `1 – 7 June 2025` → **North Coast NSW Exploration**
  - `6 May – 12 May 2025` → **Central NSW Loop**
  ✅ Prototype: sidebar “Trip title (optional)” when custom range is selected; card shows dates above title.

### Decisions (2025-06-09, continued)

- **PNG generation: Playwright** — agreed. HTML layout → headless Chromium screenshot; downloadable image remains possible (display as real PNG in app). Pillow fallback only if Cloud blocks Chromium.
- **Save UX: deferred** — button vs right-click vs hybrid to decide when building the PNG step; both remain viable once image is rendered via `st.image` / `<img>`.
- **Mobile context** — app was developed desktop-first (author workflow), but share summaries are inherently “phone” (Instagram, stories, on-the-go sharing). Many users access the web app on phones even if tables/maps are desktop-oriented. Broader mobile polish is a separate concern but **this feature should be designed and tested on phone early** (save affordance, preview size, touch). Not a phone-native app, but not desktop-only for this feature.

### Main app placement (2025-06-09 — design notes)

- **Tab name:** **Social Cards** — matches design studio tab label; Title Case like other main tabs. Retired working title: ~~Socials~~.
- **Tab order:** last data tab, **immediately before Settings** (after Maintenance).
  - Proposed strip: Map → Checklist Statistics → Ranking & Lists → Bird Families → Yearly Summary → Country → Maintenance → **Social Cards** → Settings
  - Code touchpoint: `NOTEBOOK_MAIN_TAB_LABELS` in `explorer/app/streamlit/streamlit_ui_constants.py`
- **Tab content:** Like the design mockup — period, layout, aspect ratio, spotlight stat, trip title, **current card** preview, and PNG export. Users change layout via sidebar controls.
- **Design utility** (`design_share_summary_app.py`) — kept for iteration without touching the main app; **UI should mirror the main app Social Cards tab** (sidebar + current card). Align fully when shipping #276.

### Design utility vs main app (#276)

| Feature | Design studio (`design_share_summary_app.py`) | Main app **Social Cards** tab |
|---------|--------------------------------------------------|-------------------------------|
| **Current card** preview | Yes | Yes |
| **Available statistics** expander | Yes | TBD (#276) |
| **Export current card** | Yes — below **Current card** preview, inside `@st.fragment` | Yes — **generate on export click** with spinner (#276; see **PNG export UX**) |

Both use one **current card** preview; users cycle layout via sidebar **Layout** control.

### PNG export UX (#275 / #276)

**Problem:** Card statistics and spotlight use `@st.fragment` so the HTML preview can rerun quickly. PNG generation **outside** the fragment did not rerun on fragment-only updates, so the download could lag behind the preview unless the user triggered a full app rerun.

| Context | Approach | Rationale |
|---------|----------|-----------|
| **Design studio** | **Export inside the fragment** — `_cached_share_summary_png` + `st.download_button` below the **Current card** preview (not sidebar: Streamlit forbids `st.sidebar` inside `@st.fragment`) | Card stat / spotlight edits rerun the fragment and refresh the PNG. Sidebar changes (period, layout, format, favourites) still cause a full rerun. `@st.cache_data` avoids repeat Playwright work for the same inputs. |
| **Main app Social Cards (#276)** | **Generate on export click** — one **Export current card** control; show a short spinner (“Generating PNG…”), run Playwright, then offer download | End users expect a single action. Playwright takes a few seconds — acceptable when they explicitly export. Avoids background PNG generation on every control change. **Do not** copy the design-studio pre-generation pattern unless the main tab uses the same fragment + stale-export constraint. |

**Agreed 2026-06-11** — implement lazy export in #276; design studio uses in-fragment export.

---

## Open questions (for when you're back)

Most items below were **resolved 2026-06-09** — see **Decisions (2026-06-09)**. Remaining open items:

### Layouts

1. ~~Ship all layouts~~ — **Agreed:** Hero grid, Stat tiles, Minimal list, Spotlight selectable in v1.
2. ~~Spotlight species wording~~ — **Agreed:** Year / Month / Week birds; **Species** for custom trip (was “Birds”).
3. ~~Hero/tiles/minimal default stats~~ — **Agreed** (see Decisions table).
4. Card tile sizing / blank space — iterate during testing.

### Stats on the card

5. ~~Default 4-stat hero set~~ — **Agreed:** species, lifers, checklists, locations.
6. ~~Birding days~~ — **Agreed:** on tiles/minimal defaults; summary row always.
7. ~~Countries~~ — **Agreed:** all period types on tiles/minimal defaults.
8. ~~Birding hours on card~~ — **Summary row only**, not default on cards.
9. ~~Trip title placement~~ — **Agreed:** green subtitle; dates as large headline.
10. **Favourite bird(s)** — roadmap.
11. **World bird coverage** — summary row; card placement when user picks stat.
12. **Shared checklists / days birding with others** — wire into period compute (phase 1).
13. **Total species/families (from taxa)** — wire from Bird Families bundle when stat picker lands.

### Visual design

14. ~~Logo placement~~ — **Footer only.**
15. ~~Accent colours~~ — **defaults.py schemes;** no UI yet.
16. ~~Weekly title format~~ — **Sun–Sat + long US date range.**

### Period UX

17. **Current vs previous period** — open (see Decisions).

### PNG / mobile / sidebar

18. Save UX — deferred (phase 2).
19. Phone testing — before v1.
20. Tab-aware sidebar — phase 3.

### World bird coverage (roadmap — partial)

**Observed species (%)** against the eBird/Clements living taxonomy — same metric as **Rankings → Interesting Lists → Species: Coverage** and **Bird Families** overview.

- Example display: **World bird coverage** → **6.8%**
- **All-time / list-wide**, not period-scoped.
- **Summary row:** included so users can add it via stat picker later.
- **Not** on default card tiles.

### Favourite bird(s) (roadmap — not implemented)

Optional highlight of one or more memorable species on a share card (year summary, trip report, etc.).

- **Pure user choice — not calculated.** No algorithmic “favourite bird” (no auto-pick by lifer, count, rarity, etc.). The user decides what counts as their favourite bird(s) for that card.
- **Picker, not free text:** up to **3 species** chosen from birds **recorded in the selected period** (same export, filtered by date range). Type-ahead / searchable list from that set — avoids spelling errors and invalid species.
- **Display TBD:** dedicated layout slot, footer strip, or extra panel on existing layouts (Hero / tiles / story may need more room).
- **Data:** common + scientific names from export for selected species; static PNG only (no eBird links on image).
- **Open questions when implementing:**
  - Required for trip cards vs optional on all period types?
  - One shared “favourite birds” list per card or separate picks per layout/format?
  - How to render 1 vs 2 vs 3 species (stacked names, mini list, icons)?
  - Sort order of picks — user-defined drag order?

**Status:** roadmap only — do **not** implement until after v1 layouts + Playwright PNG land (likely phase 4 or follow-up issue).

*(Visual design / PNG / mobile / sidebar open items moved to **Open questions** — most resolved 2026-06-09.)*

## Tab-aware sidebar (design notes)

### Current behaviour

- Sidebar is built **once per rerun** in `render_map_sidebar_and_working_set()` (`app_map_working_ui.py`), **before** main tabs render.
- It always shows **Map** controls (view mode, date filter, species search, basemap, etc.).
- Widgets **do** change when switching **map view** (All locations ↔ Species ↔ Lifers ↔ Families) — that logic already lives in the map sidebar.
- Sidebar does **not** change when switching **main tabs** (Checklist Statistics, Yearly Summary, etc.) — map controls stay visible even on non-map tabs.

### Desired behaviour for Social Cards

When the user selects the **Social Cards** tab:

- Sidebar should show **Social Cards controls** (mirroring the design app sidebar):
  - Period: year / month / week / custom (+ trip title when custom)
  - Aspect ratio: square / portrait post / story
  - Layout: Hero grid / Stat tiles / Minimal list / Spotlight
  - Spotlight stat (when Spotlight layout)
  - Optional: preview scale (maybe main panel only)
- Main panel: **current card** preview only (+ PNG export). Same pattern as the design studio.
- **PNG export (#276):** generate on **Export current card** click with spinner — not pre-generated on every control change (see **PNG export UX**).

When the user leaves **Social Cards** (any other main tab):

- Sidebar should **restore map controls** for the **currently selected map view** (preserve existing map session state — basemap, species pick, date filter, etc.).

Other data tabs (Checklist, Yearly, …) — **no change for v1**; map sidebar can stay as today until/unless we revisit global sidebar policy.

### Streamlit constraint (to discuss at implementation)

`st.tabs()` does **not** expose which tab is selected on the server — all tab blocks run each rerun. Today the app has no `active_main_tab` session key.

**Possible approaches** (pick one in phase 3):

| Approach | Pros | Cons |
|----------|------|------|
| **A. Conditional sidebar + session tab key** | Clean swap Map ↔ Social Cards | Need a reliable way to set tab key (see below) |
| **B. Social Cards controls in main panel only** | Simple; no tab detection | Sidebar still map-heavy on Social Cards tab |
| **C. Replace top tabs with nav that sets session state** | Sidebar always knows context | Larger UX change |
| **D. `@st.fragment` Social Cards tab + sidebar section** | Partial reruns for preview | Sidebar still global; still need conditional render at top level |

**Likely path:** **A** — refactor sidebar into `render_map_sidebar(...)` and `render_socials_sidebar(...)`, gated by `st.session_state[STREAMLIT_MAIN_TAB_KEY]`. Set that key via one of:

- Streamlit version/feature that reports tab selection (if available when we implement)
- Lightweight sync widget (acceptable if minimal)
- Social Cards-specific entry that sets key when its fragment mounts (evaluate against Streamlit behaviour)

**Map state preservation:** When switching away from Social Cards, only sidebar **widgets** swap; do not clear map working-set keys (`STREAMLIT_MAP_VIEW_LABEL_KEY`, species search, export recipe, etc.).

### UX reference

Standalone prototype: `streamlit run explorer/app/streamlit/design_share_summary_app.py` — use as the template for Social Cards tab **controls + current card preview** (#276).

---

Both turn your layout into a downloadable PNG. The prototype already builds the card as **HTML + CSS** (same pattern as map HTML export).

### Playwright (HTML → screenshot)

Uses headless Chromium to open the HTML and screenshot at exact pixel size (1080×1080, etc.).

| | |
|---|---|
| **Pros** | What you see in the design app is what you get; easy to iterate layouts; repo already uses Playwright in **tests**; fits the existing “export HTML then render” architecture. |
| **Cons** | Larger dependency; need Chromium binaries (~100MB+); **Streamlit Cloud** may need extra setup or may not support headless browsers — must verify before committing. |

### Pillow (draw in Python)

Draws rectangles and text directly onto a PNG canvas in code.

| | |
|---|---|
| **Pros** | Small, simple dependency; no browser; predictable on Cloud/serverless. |
| **Cons** | Every layout change means Python drawing code, not CSS; harder to match the HTML prototype; long labels and wrapping are painful; essentially **two implementations** (HTML preview + Pillow export) unless you drop HTML. |

### Recommendation for this project

**Agreed (2025-06-09): use Playwright** for PNG generation. A downloadable/saveable image remains possible by displaying the generated PNG in the app (`st.image` or equivalent).

Reasons:

1. The prototype and future tuning are **HTML-first** — Playwright preserves that single source of truth.
2. Map export already established the “generate standalone HTML” pattern.
3. Tests already install Playwright; team familiarity is higher than maintaining parallel Pillow layouts.

**Fallback:** If Streamlit Cloud cannot run headless Chromium, options are:

- PNG **local install only** (Playwright), preview-only on Cloud; or
- Pillow export for **one fixed layout** only (more maintenance); or
- Client-side export (browser canvas) — possible but awkward in Streamlit.

**Decision:** ☑ Playwright  ☐ Pillow  ☐ Hybrid  ☐ Defer until Cloud checked *(Cloud verification still open)*

---

## Right-click save vs download button

**User assumption (2025-06-09):** Maybe no dedicated export button — user right-clicks the preview and uses the browser’s **Save image as…** (default browser behaviour).

### Important distinction

| Question | What it decides |
|----------|-----------------|
| **Playwright vs Pillow** | How the PNG is **generated** on the server |
| **Button vs right-click** | How the user **gets** the file — UX only |

You still need PNG generation (Playwright or Pillow) for a good save experience. The current prototype is **HTML in a `<div>`**, scaled with CSS — right-click on that does **not** reliably offer “Save image as…” for the card at full 1080px resolution. It might copy HTML, save a fragment, or do nothing useful.

For right-click save to work, the UI must show a **real image** — e.g. `st.image(png_bytes)` or `<img src="data:image/png;base64,...">` at the target size (or scaled display of that bitmap). Then desktop browsers expose Save image as… on the image itself.

### Right-click only (no button)

**Pros**

- Minimal UI — no extra control in an already busy app
- Familiar to desktop users who share screenshots and web images
- Matches “here’s your card” rather than “export workflow”

**Cons**

- **Discoverability** — many users never right-click; mobile has no right-click (long-press “Save image” on iOS/Android is inconsistent in WebViews and Streamlit)
- **Streamlit** — behaviour depends on how the image is embedded; worth testing on Cloud + phone
- No obvious filename (browser picks something generic unless you use a download link with `download=` attribute — which is basically a button under the hood)

### Download button (or link)

**Pros**

- Clear affordance — “this is meant to be saved and shared”
- Can set filename (`2025-birding-summary.png`)
- Works everywhere Streamlit serves files (`st.download_button`)
- Better on mobile

**Cons**

- Extra UI element
- Feels more “tool-like” than “here’s a card”

### Hybrid (recommended to consider)

- Render the card as a **PNG image** in the app (requires Playwright/Pillow either way).
- **No prominent button** if you prefer clean UI — optional small caption: *Right-click the image to save* (desktop).
- Optionally add a **low-emphasis** text link or icon (“Download”) for mobile and discoverability without a big primary button.

### Project note

Right-click-only is a **reasonable** choice for a desktop-first app if we accept:

1. PNG generation still required (Playwright vs Pillow unchanged).
2. Mobile / Streamlit Cloud need a quick UX test before committing.
3. A subtle hint or fallback download link may still be needed for users who don’t discover right-click.

**Decision:** ☐ Right-click only (+ hint)  ☐ Download button  ☐ Hybrid  ☑ **Defer** (revisit in phase 2; bias toward minimal UI, but phone testing may require download affordance)

---

## Mobile vs desktop (context)

The explorer is a **browser-based web app**, developed and optimised primarily for **desktop** (author workflow, wide tables, maps). README already notes mobile is usable but not optimised.

**Share summaries are different:**

- Output targets social platforms consumed on **phones**.
- Users may create a summary **on phone** after birding (upload CSV is harder on phone, but Streamlit Cloud access from mobile is real).
- Save UX (right-click, long-press, share sheet) is inherently mobile-sensitive.

**Agreed direction for this feature:**

- Design cards at fixed social sizes (already done); preview sensibly on narrow viewports.
- When Playwright PNG lands, **test save flow on iOS + Android browsers**, not just desktop right-click.
- Save UX decision waits on that testing — don’t assume desktop-only.
- Broader app mobile improvements remain a separate initiative; this feature is a good pilot for “phone matters” without rewriting the whole app.

---

## Layout catalogue (prototype)

| ID | Description | Best for |
|----|-------------|----------|
| `hero` | Title + 2×2 stat blocks | Square / portrait post |
| `tiles` | Up to 6 stat tiles | Portrait post / story |
| `minimal` | Typographic list | Story / text-heavy |
| `spotlight` | One large number + label | Single-stat shares (“47 lifers”) |

---

## Aspect ratios

| ID | Size | Typical use |
|----|------|-------------|
| `square` | 1080×1080 | Instagram / Facebook square feed |
| `portrait_post` | 1080×1350 | Instagram 4:5 portrait feed |
| `story` | 1080×1920 | Instagram / Facebook stories |

---

## Code map

| File | Role |
|------|------|
| `explorer/core/share_summary_compute.py` | Period definitions + stat computation |
| `explorer/core/share_summary_defaults.py` | Colour schemes + default stat lists for share cards |
| `explorer/presentation/share_summary_preview.py` | HTML layouts, footer logo, preview scaling + export HTML |
| `explorer/presentation/share_summary_png_export.py` | Playwright PNG pipeline + filename helper |
| `explorer/app/streamlit/defaults.py` | Re-exports share-summary defaults for Streamlit tuning |
| `explorer/app/streamlit/design_share_summary_app.py` | Design studio — sidebar controls + current card preview (mirror for #276) |
| `explorer/app/streamlit/streamlit_ui_constants.py` | `NOTEBOOK_MAIN_TAB_LABELS` — add **Social Cards** before Settings |
| `explorer/app/streamlit/app_map_working_ui.py` | Map sidebar today — refactor target for tab-aware sidebar |
| `explorer/app/streamlit/app_dashboard_shell.py` | Main tab shell — wire Social Cards fragment |
| `tests/explorer/test_share_summary_preview.py` | Preview / extraction tests |
| `tests/explorer/test_share_summary_png_export.py` | PNG dimensions + filename (Playwright) |
| `tests/explorer/test_share_summary_compute.py` | Period stats + date-range tests |

---

## Phased delivery (suggested)

| Phase | Branch (example) | Deliverable | Status | Issue |
|-------|------------------|-------------|--------|-------|
| 0 | `157-social-summary-prototype` | Design app + tracker + core modules | **Ready to commit/PR** | [#273](https://github.com/jimchurches/myebirdstuff/issues/273) |
| 1 | `157-share-summary-period-stats` | Harden compute + tests; align with main app data paths | **In PR** | [#274](https://github.com/jimchurches/myebirdstuff/issues/274) |
| 2 | `275-share-summary-png-export` | Playwright HTML→PNG; display image; hybrid save UX | **In progress** | [#275](https://github.com/jimchurches/myebirdstuff/issues/275) |
| 3 | `157-share-summary-ui` | **Social Cards** main tab (before Settings); tab-aware sidebar; preview + PNG | Not started | [#276](https://github.com/jimchurches/myebirdstuff/issues/276) |
| 4 | follow-ups | Favourite bird(s), stat picker, themes, layout tuning | Not started | [#277](https://github.com/jimchurches/myebirdstuff/issues/277) |

---

## Ideas backlog

- **World bird coverage** — reuse `compute_world_species_coverage`; status metrics row in mockup; card placement TBD.
- **Favourite bird(s)** — **pure user choice** (not algorithmic); up to **3 species** from a period-scoped picker (type-ahead over birds in range — no free-text spelling).
- **Trip title on custom range** — optional user label alongside formatted dates (see User feedback).
- **“Year birds”** spotlight card — species count with birding-friendly wording.
- **Lifer highlight card** — big lifer count on spotlight card (separate from favourite-bird user picks).
- **Carousel / multiple PNGs** — one download per stat for Instagram carousel posts.
- **Map mini-preview** — dropped v1.
- **Compare to last year** — dropped v1.
- **Watermark / @handle** — v2.
- **Mobile save UX pilot** — first feature to require phone save/share testing; informs app-wide mobile backlog.

---

## Risks / caveats

- **Lifer counts** follow explorer logic (first sighting in your export), not necessarily eBird official totals — same as Yearly Summary tab.
- **Weekly stats** use **Sun–Sat** calendar weeks (not ISO Mon–Sun).
- **Empty periods** return zeroed stats object; cards may look sparse — may need “no data” state in UI.
- Logo SVG is embedded via data URI; PNG export must bundle or inline the same asset.
- **Playwright on Streamlit Cloud** — must verify headless Chromium in production; blocks Cloud PNG if unsupported (see below).
- **Phone save behaviour** — long-press / share sheet varies by browser; design app ships secondary download button as fallback.

### Streamlit Cloud verification (#275)

**Local / CI:** `playwright` is a runtime dependency in `requirements.txt`. After `pip install -r requirements.txt`, run `python -m playwright install chromium`. Unit tests in `test_share_summary_png_export.py` assert PNG width/height; CI installs Chromium in the `unit-tests` job.

**Streamlit Cloud (not yet verified on a live deploy):**

| Check | Expected | Status |
|-------|----------|--------|
| `pip install playwright` during app deploy | Succeeds (listed in `requirements.txt`) | Assumed OK |
| `playwright install chromium` on Cloud builder | May **not** run automatically — Cloud only runs `pip install` from requirements | **Open — manual verify** |
| Headless Chromium launch at runtime | Needs browser binaries on the container filesystem (~100MB+) | **Open — manual verify** |
| PNG section in design app / future Social Cards tab | Shows `st.image` + download, or warning if Chromium missing | Implemented with graceful `RuntimeError` message |

**If Cloud blocks Chromium:** show HTML preview only on Cloud (current behaviour for scaled mockup) and document “PNG export requires local run” until a Pillow fallback or custom Cloud build step is added. Re-test save flow on iOS/Android once a Cloud deploy exists.

---

## Changelog

| Date | Change |
|------|--------|
| 2025-06-09 | Initial prototype: 3 layouts, square + story, yearly stats only |
| 2025-06-09 | User feedback: logo, portrait post, periods, spotlight layout, tracker doc, Playwright vs Pillow notes |
| 2025-06-09 | Trip title on custom date range (dates + title on card); compact date formatting |
| 2025-06-09 | Longest streak stat for year/month periods (reuses checklist stats logic) |
| 2025-06-09 | Save UX notes: right-click vs download button; clarified vs Playwright/Pillow |
| 2025-06-09 | **Decision:** Playwright for PNG; save UX deferred; mobile context for share feature documented |
| 2025-06-09 | Layout choice: Hero / Stat tiles / Minimal list / Spotlight for v1; period-aware spotlight labels |
| 2025-06-09 | Main app: **Socials** tab (WIP name) before Settings; tab-aware sidebar design notes |
| 2025-06-09 | Stats: **Birding days** + **Countries** (year); period context for when to show TBD |
| 2025-06-09 | Roadmap: **Favourite bird(s)** — user picks up to 3 highlight species (not implemented) |
| 2025-06-09 | Favourite bird(s) clarified: **user-only** choice; picker from period species (not calculated) |
| 2025-06-09 | **World bird coverage** on roadmap; mockup status row only (6.8% sample / live from taxonomy) |
| 2026-06-09 | **Decisions batch:** default stats per layout, footer-only logo, trip title → green subtitle, Sun–Sat weekly titles, countries all periods, colour schemes in defaults.py, dropped media/map/compare/watermark v1 |
| 2026-06-09 | GitHub sub-issues created: #273–#277; plan comment on #157 |
| 2026-06-11 | #274: period stats hardening — shared stats, all-time taxonomy row, current/previous period + `suggest_period_anchor` heuristics documented |
| 2026-06-11 | #275: Playwright PNG export — `share_summary_png_export.py`, design app `st.image` + download button; Cloud verification documented as open |
| 2026-06-11 | Main app tab name decided: **Social Cards** (design studio + #276); retired ~~Socials~~ working title |
| 2026-06-11 | Removed **All layouts** comparison grid from design studio; UI aligns with main app (current card + layout picker) |
| 2026-06-11 | **PNG export UX:** design studio — export inside `@st.fragment`; main app (#276) — generate on export click with spinner |
| 2026-06-11 | **Total distance (km)** — year and lifetime periods only; same column as Yearly Summary |
| 2026-06-11 | Roadmap notes: **Best day** card stat (value-only, no link); **geographic scope** (country/state filter) |

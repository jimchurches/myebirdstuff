# Issue #157 — Social media summary generator (prototype notes)

> **Living tracker:** [`issue-157-share-summary-tracker.md`](issue-157-share-summary-tracker.md) — status, open questions, changelog.

**Status:** exploratory / prototype branch (`157-social-summary-prototype`) — not intended to merge as-is.

**Issue:** [Social Media Summary Generator (Year / Month Stats)](https://github.com/jimchurches/myebirdstuff/issues/157)

---

## What the issue asks for

Generate **shareable graphics** from personal eBird data — especially year-end “birding year in review” cards for Instagram and similar platforms.

**v1 scope (from issue):**

- One layout template
- Year summary only
- Basic stats: species, checklists, locations, lifers
- Static PNG download

**Later:** month / custom range, multiple themes, map snapshot, top sightings, story vs post formats.

---

## What already exists in the app

| Area | Location | Reuse potential |
|------|----------|-----------------|
| Yearly stats | `explorer/core/stats.py` → `yearly_summary_stats` | High — same numbers as Yearly Summary tab |
| Payload | `explorer/core/checklist_stats_compute.py` | High — `ChecklistStatsPayload.yearly_rows` |
| Map export | `explorer/presentation/leaflet_map_html_export.py` | Medium — HTML map export exists; PNG snapshot would be new |
| Design utility pattern | `explorer/app/streamlit/design_map_app.py` | High — standalone Streamlit tool for tuning before shipping |

There is **no** image generation library in `requirements.txt` today (no Pillow, matplotlib, or Playwright in runtime deps — Playwright is test-only).

---

## Prototype on this branch

Run the layout explorer:

```bash
streamlit run explorer/app/streamlit/design_share_summary_app.py
```

Files:

- `explorer/presentation/share_summary_preview.py` — stat extraction + HTML layout mockups
- `explorer/app/streamlit/design_share_summary_app.py` — sidebar controls, sample or CSV data

Three layout sketches:

1. **Hero grid** — title + 2×2 big stat blocks (4 metrics)
2. **Stat tiles** — up to 6 tiles in a flex grid
3. **Minimal list** — typographic row layout

Aspect ratios rendered at true pixel size then CSS-scaled:

- **Square** 1080×1080 (Instagram post)
- **Story** 1080×1920 (Instagram story)

Palette aligns with checklist stats UI greys + a green accent placeholder (`#2d6a4f`).

---

## Implementation approaches (for discussion)

### A. HTML + CSS → PNG (recommended for v1)

**How:** Build self-contained HTML (like map export), render with headless Chromium (Playwright — already in test stack) or similar.

**Pros:** Matches existing HTML export pattern; easy to iterate on layout in browser; WYSIWYG with the design app.

**Cons:** Heavier dependency if added to runtime; font rendering consistency; Streamlit Cloud may need extra setup for headless Chrome.

### B. Pillow / programmatic drawing

**How:** Draw text and boxes with Pillow (or cairo).

**Pros:** No browser; predictable PNG output; small dependency.

**Cons:** Layout iteration is slower; wrapping/long labels awkward; doesn’t match Streamlit HTML styling automatically.

### C. In-app preview only (no PNG initially)

**How:** Show HTML card in Streamlit; user screenshots manually.

**Pros:** Fastest path to validate design.

**Cons:** Poor UX for the stated feature goal.

**Suggestion:** Use **this prototype (HTML)** to pick a layout, then implement **A or B** on a separate branch. Playwright is attractive because tests already use it; alternatively Pillow if Cloud deployment is a concern.

---

## Stats to show — brainstorm

**Strong candidates (issue + community norms):**

| Stat | In yearly summary? | Notes |
|------|-------------------|-------|
| Total species | Yes | Core |
| Lifers | Yes | Core |
| Total checklists | Yes | Core |
| Unique locations | Yes | Core |
| Days with checklist | Yes | Good “effort” metric |
| Total birding hours | Yes | If duration present in export |
| Total bird families | Yes | Nice extra |
| Countries visited | Country tab | Needs aggregation, not in yearly row today |
| Top species / high counts | Rankings | v2 — needs “most observed” for period |
| Map thumbnail | Map pipeline | v2 — filter GeoJSON by year, static snapshot |

**Default v1 set (proposal):** species, lifers, checklists, locations — four numbers fit cleanly on a square card.

---

## Visual design — what’s realistic without a designer

You don’t need complex illustration. Data-first cards work well:

- Large numerals, short labels
- Plenty of whitespace
- One accent colour + neutrals (already in app)
- Optional: small logo from `docs/explorer/assets/personal-ebird-explorer-logo.svg`
- Footer: “Personal eBird Explorer” or custom title (“My 2025 birding year”)

**Avoid for v1:** photos, charts, animations, multiple fonts, dense paragraphs.

**Story format:** same stats stacked vertically with more breathing room; room for a map strip or “top 3 lifers” later.

---

## Suggested work breakdown

| Phase | Branch (example) | Deliverable |
|-------|------------------|-------------|
| **0 — Prototype** | `157-social-summary-prototype` (this branch) | Design app + doc; pick layout |
| **1 — Data API** | `157-share-summary-period-stats` | `share_summary_stats(period)` for year/month/range; unit tests |
| **2 — PNG export** | `157-share-summary-png-export` | Download button; one layout + square |
| **3 — Main app UI** | `157-share-summary-tab` | Year picker + download in Yearly Summary or new Share section |
| **4 — Enhancements** | separate issues | Story format, themes, map, top species |

Merge order: 1 → 2 → 3. Phase 0 may be closed without merging (or squash doc + minimal module if useful).

---

## Risks and assumptions

- **Lifer definition** matches explorer yearly table (first sighting per species in dataset), not necessarily eBird official totals — same caveat as rest of app.
- **PNG on Streamlit Cloud** — verify headless browser availability before committing to Playwright in production deps.
- **Month / custom range** — needs new aggregation (yearly pipeline is calendar-year only today).
- **Map snapshot** — reuses filtered GeoJSON + tile rendering; non-trivial and likely v2.

---

## Next step

1. Run the design app with your own CSV.
2. Note which layout and stat set feel right (or what to change).
3. Decide PNG approach (Playwright vs Pillow).
4. Open sub-issues or tasks for phases 1–3 above.

# AI Context for Personal eBird Explorer

This document provides high-level context for AI coding assistants working in this repository.  
**Important:** Read this before suggesting architectural changes. (refs #48)

---

## AI Coding Rules

This repository is frequently developed using AI coding assistants (Cursor, Copilot, ChatGPT).  
The following rules help keep the codebase stable and understandable.

### Prefer small changes

Prefer incremental improvements over large rewrites.

Avoid introducing major architectural changes unless explicitly requested.

### Keep logic out of the UI

The Streamlit app acts as a **UI layer**.

Core logic should live in Python modules inside the project package.

Avoid placing complex logic directly in UI code.

### Respect the data model

The application assumes:

- a CSV dataset is loaded once
- the dataset is static during runtime

Caching strategies rely on this assumption.

Do not introduce logic that mutates the main dataframe during execution.

### Avoid unnecessary dependencies

Do not introduce new frameworks or heavy dependencies without clear benefit.

In particular avoid:

- web frameworks
- database layers
- complex UI frameworks

The project is intentionally lightweight.

**Roadmap note:** **Streamlit** is the **primary** UI in this repo ([issue #70](https://github.com/jimchurches/myebirdstuff/issues/70)). New UI work should target `explorer/app/streamlit/`. Do not add **other** full UI frameworks without maintainer agreement.

### Streamlit UI

For work in **`explorer/app/streamlit/`** and any future Streamlit-first UI ([issue #70](https://github.com/jimchurches/myebirdstuff/issues/70)). **Native widgets first**; **shared HTML formatters** for richly-linked tables where `st.dataframe` is not enough:

- **Use Streamlit primitives first** when they are enough — `st.tabs`, `st.expander`, `st.columns`, `st.dataframe`, `st.metric`, sidebar, `.streamlit/config.toml` theme. Simple **metric / key–value** blocks and uniform **URL** columns (`LinkColumn`) fit here.
- **Rankings, “Interesting lists”, and similar richly-linked tables** — These use **HTML tables** with **links in cells** (species, locations, datetimes), **mixed styling** (e.g. dotted vs solid underlines, bold counts), and **⧉** affordances. **`st.dataframe` cannot replicate that** in a maintainable way. **Approved approach:** emit the HTML from **shared module formatters** (`checklist_stats_display`, `rankings_display`, `format_checklist_stats_bundle`, maintenance/ranking helpers, etc.) and render it with **`st.markdown(..., unsafe_allow_html=True)`** or **`st.html`** (when available). **Do not duplicate** table markup inside the Streamlit adapter — extend or call the formatter. Treat this like **Folium popup HTML**: trusted formatter output; escape user-origin text **inside** the formatter.
- **Keep eBird deep links** — Do **not** drop URLs from a ported view just to stay on a plain dataframe. Prefer shared HTML for rich tables; use **`LinkColumn`** or **layout + `st.markdown` links** only where that still matches UX.
- **Ad-hoc HTML/CSS** — One-off `unsafe_allow_html` blobs **not** produced by a shared formatter are still a **conscious exception** (fragility, theming). Prefer routing table HTML through **`explorer/presentation/`** helpers so formats stay aligned.
- **When suggesting implementations**, note briefly if **`st.dataframe` would suffice** vs formatter HTML, so the choice stays explicit.
- **Defaults live in one module** — Put new or changed **user-visible defaults** (limits, colours, labels, session seeds, export filenames, etc.) in **`explorer/app/streamlit/defaults.py`**, then wire them into **`explorer/app/streamlit/app.py`** and, if the value is **persisted in settings YAML**, into **`explorer/core/settings_config.py`** (reuse the same constants for `Field(...)` defaults and allowlists). Streamlit-only HTML helpers (e.g. rankings layout) should import from **`defaults.py`** instead of inlining magic numbers. Extend **`tests/explorer/test_streamlit_defaults.py`** when the persisted schema or default payload changes so the builder and model stay aligned.

### Prefer readability over cleverness

Code should be understandable to a human reader returning to the project months later.

Avoid overly abstract patterns or unnecessary optimisation.

### Do not break caching assumptions

Performance improvements rely on simple in-memory caches.

Changes to:

- location grouping
- species filtering
- popup generation

should preserve cache correctness.

### When unsure

If a change might affect architecture, caching, or data flow:

ask or describe the proposed change before implementing it.

---

## Project purpose

Personal eBird Explorer visualises a user's personal eBird data on an interactive map.

The tool allows exploration of:

- all checklist locations
- species-specific observation locations
- visit statistics
- first/last seen dates

The primary interface is the Streamlit app that renders a Folium map.

---

## Architecture overview

Data flow:

```
CSV export from eBird
    ↓
data_loader.py
    ↓
clean canonical dataframe
    ↓
derived statistics modules
    ↓
map rendering
    ↓
Folium map displayed in Streamlit UI
```

The UI layer should stay **thin**. All core logic should live in Python modules.

---

## Roadmap: Streamlit (or similar UI)

**Long-term intent:** keep Streamlit as the primary UI and continue improving the Streamlit experience over time.

**Practical guidance for AI and contributors:**

- `explorer/app/streamlit/app.py` is where Streamlit UI work should land; reuse `explorer.core` and `explorer.presentation` modules.
- When working on **any** area of the explorer, **bias toward** patterns that make a future Streamlit app easier:
  - Put **new or refactored logic** in `explorer/core/` (or other testable modules) with **explicit inputs and return values**, not buried only in UI code.
  - Be mindful of **state boundaries** (loaded data vs filters vs display options vs caches); a future app will likely use something like session-scoped state.
- Larger migration themes (e.g. date-filter + index rebuild, map build/caches, checklist stats / yearly HTML, lifer lookups, search/autocomplete) may be tracked as separate GitHub issues or epics; follow those when implementing related work.

This section exists so assistants **remember the direction** when suggesting architecture, refactors, or where new code should live.

---

## Key design principles

The dataset is **static during runtime**.

The application assumes:

- a CSV file is loaded once
- data does not change while the app/session is running

**External API (taxonomy):** The app fetches the eBird taxonomy once at startup (no API key) to resolve species common names to eBird species/lifelist URLs. Locale is controlled by the UI setting (Streamlit env/config like `STREAMLIT_EBIRD_TAXONOMY_LOCALE` / **EBIRD_TAXONOMY_LOCALE**; e.g. `"en_AU"`, `"en_GB"`, or empty for default). On network or API failure, the UI continues without species links; do not break the run or add retries in the first version.

This allows caching of derived structures such as:

- grouped location data
- species-filtered data
- popup HTML

Caching should remain simple and in-memory.

---

## UI design

Streamlit provides the user interface.

Controls include:

- species search
- "show only selected species"
- map interactions
- export controls

The UI should remain lightweight. Avoid placing heavy logic inside Streamlit callbacks.

---

## Performance approach

Map redraw performance is improved using simple caching and double-buffered map output (draw into a hidden Output widget, then swap to show it so the visible map is never cleared).

Avoid recomputing expensive operations such as:

- dataframe groupby
- popup HTML generation
- location summaries

Prefer incremental optimisation over architectural changes.

---

## Development guidelines

When modifying the code:

- Prefer small changes over large rewrites.
- Avoid introducing new frameworks unless clearly justified.
- Maintain separation between:
  - **UI layer** (Streamlit)
  - **core logic** (modules)
- Do not move logic into the UI layer.

---

## Testing

Tests exist for:

- date parsing
- data loading
- canonicalisation logic
- map renderer helpers
- species filtering and normalisation
- path resolution
- stats and rankings
- region display (country/state names in rankings tables)
- taxonomy (species-link lookup, locale parameter, offline behaviour)

New logic should ideally be placed in modules where tests can be written.  
Avoid writing complex logic directly in UI code.

Run tests: `pytest tests/ -v`

---

## Safe areas for improvement

AI assistants may safely improve:

- documentation
- comments
- small performance improvements
- test coverage
- minor usability features

---

## Areas requiring caution

Avoid large changes to:

- data loading pipeline
- caching architecture
- map rendering structure

Discuss before implementing major refactors.

---

## Typical workflow

1. Load CSV data
2. Explore species via search
3. Filter locations
4. Inspect popup statistics
5. Optionally export map

---

## Future direction

**Committed direction (roadmap):** keep the explorer as a **Streamlit** app while keeping **core logic in modules** so behaviour is testable and reusable. See [Roadmap: Streamlit (or similar UI)](#roadmap-streamlit-or-similar-ui).

Other possible improvements include:

- improved UI controls
- better export options
- optional hosted deployment
- richer species analysis tools
- easier onboarding for non-technical users

Items beyond the Streamlit roadmap are exploratory unless tied to an issue or maintainer decision.

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

### Keep logic out of the notebook

The Jupyter notebook acts as a **UI layer**.

Core logic should live in Python modules inside the project package.

Avoid placing complex logic directly in notebook cells.

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

**Roadmap note:** **Streamlit** is the **intended future** primary UI ([issue #70](https://github.com/jimchurches/myebirdstuff/issues/70): phased prototype → parallel dev → cutover; preserve notebook/Binder until then). A **prototype** lives in `streamlit_app/` (`requirements-streamlit.txt`); keep **shipping** `requirements.txt` / Binder focused on Jupyter unless `main` explicitly switches. Do not add **other** full UI frameworks without maintainer agreement.

### Streamlit UI: prefer native components

For work in **`streamlit_app/`** and any future Streamlit-first UI:

- **Default to Streamlit primitives** — e.g. `st.tabs`, `st.expander`, `st.columns`, `st.dataframe`, `st.metric`, sidebar inputs, and theme via `.streamlit/config.toml`. This keeps layouts maintainable and consistent with Streamlit updates.
- **Treat custom HTML/CSS as a conscious exception** — Large `st.markdown(..., unsafe_allow_html=True)` blobs, inline styles, and copied notebook HTML are fine when **explicitly** chosen (e.g. comparing to the Jupyter UI, embedded Folium, or a one-off migration step), but they add fragility and bypass Streamlit’s accessibility/theming story.
- **When suggesting implementations**, if a request drifts toward bespoke HTML/CSS where native widgets would suffice, **say so briefly** and offer the Streamlit-native option first; the maintainer may still prefer HTML for a good reason.

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

The primary interface is a Jupyter notebook that renders a Folium map.

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
Folium map displayed in notebook UI
```

The notebook acts as a **thin UI layer**. All core logic should live in Python modules.

---

## Roadmap: Streamlit (or similar UI)

**Long-term intent:** move the primary user interface from **Jupyter + ipywidgets + Voila** toward **Streamlit**, following the plan in **[issue #70](https://github.com/jimchurches/myebirdstuff/issues/70)** (prototype on a feature branch, notebook unchanged on `main` until cutover, optional legacy tag/branch).

**Practical guidance for AI and contributors:**

- **Not every feature or fix will be Streamlit-related yet.** The notebook remains the default full-featured UI until migration phases in #70 complete.
- **Prototype:** `streamlit_app/app.py` — extend here for Streamlit experiments; reuse `personal_ebird_explorer` modules.
- When working on **any** area of the explorer, **bias toward** patterns that make a future Streamlit app easier:
  - Put **new or refactored logic** in `personal_ebird_explorer/` (or other testable modules) with **explicit inputs and return values**, not buried only in notebook cells.
  - Treat the notebook as **glue**: widgets, observers, and display—not the home for large orchestration, HTML compilers, or data-prep pipelines.
  - Be mindful of **state boundaries** (loaded data vs filters vs display options vs caches), even if the notebook still uses globals today; a future app will likely use something like session-scoped state instead.
- Larger migration themes (e.g. date-filter + index rebuild, map build/caches, checklist stats / yearly HTML, lifer lookups, search/autocomplete) may be tracked as separate GitHub issues or epics; follow those when implementing related work.

This section exists so assistants **remember the direction** when suggesting architecture, refactors, or where new code should live—even when the user’s immediate request is still notebook-centric.

---

## Key design principles

The dataset is **static during runtime**.

The application assumes:

- a CSV file is loaded once
- data does not change while the notebook is running

**External API (taxonomy):** The app fetches the eBird taxonomy once at startup (no API key) to resolve species common names to eBird species/lifelist URLs. Locale is controlled by the notebook user variable **EBIRD_TAXONOMY_LOCALE** (e.g. `"en_AU"`, `"en_GB"`, or empty for default). On network or API failure, the notebook continues without species links; do not break the run or add retries in the first version.

This allows caching of derived structures such as:

- grouped location data
- species-filtered data
- popup HTML

Caching should remain simple and in-memory.

---

## UI design

The notebook provides the user interface.

Controls include:

- species search
- "show only selected species"
- map interactions
- export controls

The notebook should remain lightweight. Avoid placing heavy logic inside notebook cells.

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
  - **UI layer** (notebook)
  - **core logic** (modules)
- Do not move logic into the notebook.

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
Avoid writing complex logic directly in notebook cells.

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

**Committed direction (roadmap):** migrate the explorer toward a **Streamlit**-style (or similar) app while keeping **core logic in modules** so the notebook is not the only place behaviour lives. See [Roadmap: Streamlit (or similar UI)](#roadmap-streamlit-or-similar-ui).

Other possible improvements include:

- improved UI controls (notebook and/or future app)
- better export options
- optional web deployment (e.g. Voila) for the notebook-era UI
- richer species analysis tools
- easier onboarding for non-technical users

Items beyond the Streamlit roadmap are exploratory unless tied to an issue or maintainer decision.

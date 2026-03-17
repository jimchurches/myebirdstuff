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

Possible future improvements include:

- improved UI controls
- better export options
- optional web deployment (e.g. Voila)
- richer species analysis tools
- easier onboarding for non-technical users

These are exploratory and not committed features.

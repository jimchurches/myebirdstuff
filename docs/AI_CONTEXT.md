# AI Context for Personal eBird Explorer

This document provides high-level context for AI coding assistants working in this repository.  
**Important:** Read this before suggesting architectural changes. (refs #48)

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

Map redraw performance is improved using simple caching.

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

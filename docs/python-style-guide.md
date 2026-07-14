# Python Style Guide — Personal eBird Explorer

This is the project-specific Python style guide for **myebirdstuff**.

It is the single source of truth for Python style, readability, comments, docstrings, and related code review expectations in this repository.

AI coding tools, code reviewers (human and agent), and contributors should follow this guide when writing or reviewing Python in this project.

---

## Guiding philosophy

> Write Python the way a highly regarded engineer who loves teaching would want it written:
> neat, easy to read, efficient where it matters, and easy to follow.

The aim of this guide is not strict compliance with any external standard.
The aim is code that is:

- **boring** — does what it says, no surprises;
- **explicit** — intent is clear without needing to trace through multiple layers;
- **easy to review** — a reviewer can read a function and quickly understand what it does and why;
- **easy to maintain** — someone new to the code (or returning after months away) can understand and change it safely;
- **suitable for a Streamlit app** — appropriate to the project's size, structure, and audience;
- **understandable by someone still learning Python** — do not sacrifice clarity for brevity or abstraction.

The primary references for this guide are [PEP 8](https://peps.python.org/pep-0008/), [PEP 257](https://peps.python.org/pep-0257/), and the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), used as practical references, not as strict compliance targets.

Linting is enforced by [Ruff](https://docs.astral.sh/ruff/) (see `ruff.toml`).

---

## Naming

### Use clear, descriptive names

Names should say what a thing is or does.
A reader should not need to look up a name to understand it.

```python
# Good
date_filter_status_line = build_status_line(filters)
species_visit_counts = count_visits_by_species(df)

# Avoid
dfs = build_status_line(filters)
svc = count_visits_by_species(df)
```

Abbreviations are acceptable only when they are standard and obvious in context (e.g. `df` for a pandas DataFrame, `idx` in a tight loop). When in doubt, spell it out.

### Variables and functions: `snake_case`

```python
checklist_count = 42
def get_species_list(df): ...
```

### Constants: `UPPER_SNAKE_CASE`

```python
DEFAULT_MAP_ZOOM = 10
MAX_SPECIES_DISPLAY = 50
```

### Classes: `PascalCase`

```python
class ChecklistFilter: ...
```

### Module-level names

Module names should be lowercase, short, and use underscores if needed.
Avoid names that shadow built-ins or standard library modules.

---

## Functions

### Keep functions small and single-purpose

A function should do one thing.
If you need to add a comment to explain what a section of a function is doing, that section is a candidate for its own function.

### Prefer explicit return values over side effects

Functions that compute something should return a value.
Functions that change state should say so clearly in their name (`update_`, `set_`, `reset_`).

### Avoid deep nesting

Prefer early returns or guard clauses to reduce indentation depth.

```python
# Good
def get_species_label(row):
    if row is None:
        return ""
    return row["common_name"]

# Avoid
def get_species_label(row):
    if row is not None:
        return row["common_name"]
    else:
        return ""
```

### Default arguments

Do not use mutable objects as default arguments.

```python
# Good
def build_filter(options=None):
    if options is None:
        options = {}

# Avoid
def build_filter(options={}):
```

---

## Comments

### Write comments that explain *why*, not *what*

The code shows what it does.
Comments should explain decisions, constraints, or context that is not obvious from the code.

```python
# Good — explains a non-obvious constraint
# eBird exports use "Date" not "Datetime"; time is always midnight UTC in the raw CSV.
checklist_date = pd.to_datetime(row["Date"])

# Avoid — just restates the code
# Convert the date
checklist_date = pd.to_datetime(row["Date"])
```

### Comment Streamlit session state interactions

Streamlit session state behaviour can be surprising.
A short comment on why state is being read or written here is worth adding.

```python
# Clear cached map data when the file is reloaded so stale pins are not shown.
st.session_state.pop("map_geojson", None)
```

### Use `TODO` and `FIXME` sparingly and usefully

Include a brief explanation of what is needed and, where appropriate, a GitHub issue reference.

```python
# TODO (#295): Replace this linear scan with a dict lookup once the species index is built.
```

Do not leave `TODO` comments that just say "fix this" or "improve this" without context.

---

## Docstrings

### Use docstrings for all public functions and modules

Every function that is called from outside its own module should have a docstring.
A short one-line docstring is better than none.

Follow [PEP 257](https://peps.python.org/pep-0257/) conventions:

```python
def count_checklists(df):
    """Return the total number of unique checklists in the dataframe."""
    return df["Submission ID"].nunique()
```

For functions with multiple parameters, non-obvious return values, or edge cases, use a multi-line docstring:

```python
def get_species_for_location(df, location_id):
    """Return a sorted list of species observed at a given location.

    Args:
        df: The canonical eBird dataframe (not filtered).
        location_id: The eBird location ID string (e.g. "L12345").

    Returns:
        A sorted list of common name strings. Returns an empty list if the
        location has no observations.
    """
```

### Module docstrings

Add a brief module docstring at the top of each module to explain its purpose:

```python
"""Builds GeoJSON feature collections for the all-locations map.

Input is the canonical eBird dataframe. Output is a dict ready to pass
to the Leaflet map component.
"""
```

---

## Imports

### Standard import order

Follow PEP 8 import order, separated by blank lines:

1. Standard library
2. Third-party packages
3. Local/project modules

```python
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from explorer.core import data_loader
from explorer.app.streamlit import defaults
```

Ruff enforces import hygiene (unused imports, undefined names) and import order (`I` rules, isort). The order described above is checked by CI.

### Do not use wildcard imports

```python
# Avoid
from explorer.core.utils import *
```

---

## Formatting

### Line length

Long lines in docstrings and Streamlit markup are tolerated (see `ruff.toml`).
In logic code, prefer lines under 100 characters where practical.
Wrap long function calls across lines for readability:

```python
result = some_function(
    first_argument,
    second_argument,
    third_argument=True,
)
```

### Indentation

4 spaces. No tabs.

### Trailing commas in multi-line collections

Use trailing commas in multi-line function calls and data structures.
This makes diffs cleaner when items are added or removed.

```python
ALLOWED_COLOURS = [
    "red",
    "blue",
    "green",
]
```

---

## Type hints

### Use type hints where they help readability

Type hints are encouraged for function signatures in core logic modules, especially when the types are not obvious from the name or context.
They are not required everywhere, and should not be used when they add clutter without adding clarity.

```python
def get_visit_count(df: pd.DataFrame, species: str) -> int:
    """Return the number of visits where the species was recorded."""
    return int(df[df["Common Name"] == species].shape[0])
```

Avoid complex generic types (e.g. `dict[str, list[tuple[int, str]]]`) unless the structure genuinely needs to be pinned. A short comment is often clearer.

Do not add type hints to every variable. Reserve them for function signatures and cases where the type is ambiguous.

---

## Error handling

### Be explicit about what can go wrong

When a function can fail in a predictable way, handle it explicitly and provide a useful message.

```python
if df is None or df.empty:
    st.warning("No data loaded. Please upload an eBird export.")
    st.stop()
```

### Avoid bare `except`

Always specify the exception type. A bare `except` can swallow unexpected errors silently.

```python
# Good
try:
    taxonomy = fetch_taxonomy()
except requests.RequestException as e:
    st.warning(f"Taxonomy fetch failed: {e}. Continuing without links.")

# Avoid
try:
    taxonomy = fetch_taxonomy()
except:
    pass
```

---

## Streamlit-specific patterns

### Keep the UI thin

Streamlit files should handle layout and user interaction.
Data transformation, filtering, and computation belong in modules under `explorer/core/` or `explorer/app/`.

### Do not hardcode tunable values in UI files

Use `explorer/app/streamlit/defaults.py` for developer-tweakable values (sizes, colours, zoom bounds).
Use `explorer/app/streamlit/streamlit_ui_constants.py` for fixed UI strings (labels, tab names, spinner text).

See `docs/AI_CONTEXT.md` for the full defaults hierarchy.

### Cache with care

In-memory caching relies on the dataframe being static during runtime.
Do not mutate the canonical dataframe.
Be careful when changing grouping logic, filtering, or popup generation — these affect cache correctness.

---

## Constants and magic values

### Name magic values

Do not scatter raw strings or numbers through logic code.
Give them a name in the appropriate constants file.

```python
# Good
if zoom_level < MIN_CLUSTER_ZOOM:
    ...

# Avoid
if zoom_level < 8:
    ...
```

### Where constants live

- **Developer tweakables** (map/UI defaults, marker colour scheme *literals*): `explorer/app/streamlit/defaults.py`
- **Fixed UI strings**: `explorer/app/streamlit/streamlit_ui_constants.py`
- **Persisted settings schema defaults**: `explorer/core/settings_schema_defaults.py`
- **Feature-domain defaults** (e.g. share summary): `explorer/core/*_defaults.py` (often re-exported from `defaults.py` as façade only)
- **Map marker scheme dataclasses** (shapes, not preset hex): `explorer/core/map_marker_scheme_model.py`
- **Basemaps**: `explorer/data/basemaps.yaml`

See `docs/AI_CONTEXT.md` § Defaults for ownership vs re-export rules.

---

## What this guide does not require

This guide does not require:

- strict compliance with every rule in the Google Python Style Guide;
- type hints on every function or variable;
- heavy abstraction or design patterns;
- refactoring working code purely to satisfy this guide;
- formatting-only churn mixed into feature work.

---

## Adoption

This guide applies to new code and to code that is directly touched during development.

**Do not** rewrite existing modules purely to satisfy this guide.
**Do** apply the guide locally when editing nearby code — rename an unclear variable, improve a docstring, simplify an overly nested block.

If broader cleanup is worthwhile, open a separate issue so it can be reviewed on its own.

---

## References

- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Ruff documentation](https://docs.astral.sh/ruff/)

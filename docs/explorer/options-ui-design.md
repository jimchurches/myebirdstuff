# Options / Settings UI — Design Discussion

Design ideas for exposing user-configurable options in the Personal eBird Explorer notebook via an options tab or similar UI, while respecting current architecture and constraints.

---

## 1. Categorising current options

Split options by **when** they matter and **what** they affect:

| Category | Examples | When they matter | Can change at runtime? |
|----------|----------|------------------|-------------------------|
| **Bootstrap** | `DATA_FOLDER_HARDCODED`, `EBIRD_DATA_FILE_NAME`, `EBIRD_TAXONOMY_LOCALE` | Before/at data load | No — need re-run from load cell |
| **Data prep** | `FILTER_BY_DATE`, `FILTER_START_DATE`, `FILTER_END_DATE` | When building `df`, `records_by_loc`, etc. | No — need re-run from data prep |
| **Display / map** | `MAP_STYLE`, pin colours, `MARK_LIFER`, `MARK_LAST_SEEN`, `POPUP_SORT_ORDER`, `POPUP_SCROLL_HINT` | When drawing the map or building HTML | Yes, if we re-draw using current variables |
| **UI behaviour** | `RANKINGS_TABLE_VISIBLE_ROWS`, `TOP_N_TABLE_LIMIT`, `CLOSE_LOCATION_METERS` | When rendering rankings/maintenance | Partly — some only on next render of that section |

So we have: (1) options that require a full “restart” (re-run from load or data prep), (2) options that can be “dynamic” if we re-invoke the right builders with the same data, and (3) options that take effect “next time we build this panel” or on restart depending on structure.

---

## 2. Static vs dynamic: the real constraint

The app’s design principle is **dataset static at runtime**. So:

- **Static (write variable, restart):** Easiest to implement and to reason about. No half-applied state. If we add an “Options” tab that only writes to the same variables the code already uses, we can label it clearly: “Settings — re-run notebook from ‘Load data’ to apply.” That sets correct expectations.

- **Dynamic (change takes effect now):** Only safe for things that don’t change data or data-derived caches. Good candidates: `MAP_STYLE`, pin colours, `POPUP_SORT_ORDER`, `POPUP_SCROLL_HINT` — i.e. “how we draw” not “what we load.” We’d wire: “Options tab changes variable → if map is visible, call `draw_map_with_species_overlay()` again with same data.” For rankings/maintenance, “dynamic” might mean “next time this tab/section is rendered, use new value” — which might already happen if we rebuild HTML from current variables when the user switches tab or clicks something.

So a **hybrid** is natural: bootstrap and data-prep options stay “set then re-run from here.” Display options we can make “change now” where we re-draw using existing data. Anything that affects `df` or `records_by_loc` or taxonomy load stays “re-run from Data prep / Load” with no promise of immediate effect from an options UI.

---

## 3. Where options live: hybrid is usually best

- **Keep in code (and/or config_secret.py):** Data path / file name (security and environment-specific). Optionally taxonomy locale if we’re happy for it to stay “edit and re-run” only.

- **Expose in UI (Options tab or similar):** Display (map style, pin colours, lifer/last-seen toggles, popup sort/scroll), behaviour (date filter on/off and range, rankings visible rows, maintenance distance, etc.). For bootstrap we have two patterns: (A) “Config first” — notebook starts, no data path (or no file found); first thing user sees is an “Options / Setup” area with data folder (or path), maybe file name; “Load data” button or instruction: “Set path above, then run the cell below.” So “options” can include path but it’s still “set then run,” not dynamic. (B) “Code + optional UI mirror” — path stays in code/config only; Options tab only shows things that are safe to change at runtime (or “change then re-run from here” with a clear label). No expectation that path is editable in UI unless we add a dedicated “first-time setup” flow.

---

## 4. Making “restart required” obvious

If we add an options UI we should **group by “when it applies”** (e.g. “Data & load” vs “Map display” vs “Tables & lists”) and add a **short hint** where it matters (e.g. under date filter: “Changing these requires re-running from the ‘Data prep’ cell”). One line at top of options: “Changes to data path or date filter require re-running the notebook from the appropriate cell. Map and display options may apply on next refresh.” That keeps the “static dataset” and “restart when needed” story visible without blocking a friendlier UI.

---

## 5. Best practice fit with our stack

- **Jupyter:** Variables are global; changing a variable and re-running later cells is normal. An “Options” tab that only **sets those same variables** (e.g. `MAP_STYLE = dropdown.value`) keeps everything in one place and doesn’t require persistence unless we want it.

- **Voila:** Same idea — widgets can set variables; re-run is “restart app” or “run these cells again.” So “static” options (write variable, re-run) still make sense; “dynamic” only where we explicitly re-invoke the map/rankings builders.

- **Persistence (optional later):** If we want options to survive restarts we could write a small JSON (or use a single “options” module) when user clicks “Save options,” and have the first cell read that file and set variables. That’s an enhancement; not required for a first version.

- **Validation:** For path, “check path exists and file exists” in the load cell is enough. For date range, “start ≤ end” and a note like “Re-run from Data prep” keeps behaviour clear.

---

## 6. Suggested direction (summary)

- **Options tab (or “Settings” tab):** One place for “user-friendly” controls. Group into: Data / load (path if we expose it, taxonomy locale), Date filter, Map display, Tables & lists, etc.

- **Semantics:** Bootstrap / data-prep options: “Set above, then re-run from the ‘Load config and data’ (or ‘Data prep’) cell.” No promise of dynamic behaviour. Display options (map style, colours, popup, etc.): implement as “dynamic” where easy (e.g. redraw map when widget changes), or “apply on next redraw” with one sentence of explanation. Others: explicit “Re-run from … to apply” where they affect computed state.

- **Data path:** Either keep in code only, or expose in Options as a “first-time setup” with a clear “Re-run from top” message. Don’t imply that changing path mid-session is supported without re-run.

- **Implementation order:** (1) Add an Options/Settings tab that only **sets the same variables** the code already uses, with clear “re-run from …” for non-dynamic ones. (2) Optionally wire map-style (and similar) to a redraw so those feel “dynamic.” (3) Later: persistence or “load defaults from file” if we want.

This keeps our architecture (dataset static, notebook as thin UI, logic in modules), avoids over-promising “dynamic” behaviour, and still makes options more discoverable and easier to change than editing raw code.

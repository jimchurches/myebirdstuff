# Settings UI — Design Discussion

Design for exposing user-configurable options in the Personal eBird Explorer notebook via a **Settings** tab (issue [#38](https://github.com/jimchurches/myebirdstuff/issues/38)), while respecting current architecture and constraints.

---

## 0. Design decisions and preferences (from discussion)

- **Naming:** Use **Settings** (not Options) — more current and familiar.
- **Persistence:** Not in scope for the first version. Assume it’s on the roadmap; phase 2 could add optional JSON in the config file (only when the user already uses that config for path). Updating running code from within the app is not a goal; “set variable then re-run” remains the model for non-dynamic settings.
- **Date filter:** Map-centric only. It does not drive other tabs (e.g. tables); future roadmap may change that. Resetting the map must **not** reset the date filter. Changing the date filter should update the map. This control can live in **map controls** (recommended) so it stays next to the map and doesn’t imply it affects other panels.
- **Dynamic where possible:** Date filter and map style should take effect without a notebook restart when feasible (e.g. re-apply filter and redraw map for date; redraw map for style).
- **Pin colours:** Simple only — named colours (e.g. `"lightgreen"`, `"pink"`). No hex/RGB or custom colour picker.
- **Path:** Shown in Settings. Handle different sources: config file, hardcoded, or not configured (CSV in notebook folder). How to edit (code vs UI) to be discussed; display is the first step.
- **Restart required:** Make it obvious which settings require a re-run (e.g. “Re-run from Load” or “Re-run from Data prep”).

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

- **Expose in UI (Settings tab):** Display (map style, pin colours, lifer/last-seen toggles, popup sort/scroll), behaviour (rankings visible rows, maintenance distance, etc.). **Date filter** lives in **map controls** so it stays map-centric and visible where it applies. For bootstrap: path is **visible** in Settings (read-only or with source: hardcoded / config / notebook folder); changing path stays “edit code or config, then re-run from Load.”

---

## 4. Making “restart required” obvious

Group settings by “when it applies” and add a **clear “Re-run from …”** for any that need it (e.g. “Re-run from Load” for path/file name; “Re-run from Data prep” only if date filter were not dynamic). For dynamic settings (map style, date filter in map controls), no restart hint. One line at top of Settings: “Some changes require re-running from the ‘Load config and data’ or ‘Data prep’ cell; those are marked below.”

---

## 5. Best practice fit with our stack

- **Jupyter:** Variables are global; changing a variable and re-running later cells is normal. A Settings tab that only **sets those same variables** (e.g. `MAP_STYLE = dropdown.value`) keeps everything in one place and doesn’t require persistence unless we want it.

- **Voila:** Same idea — widgets can set variables; re-run is “restart app” or “run these cells again.” So “static” options (write variable, re-run) still make sense; “dynamic” only where we explicitly re-invoke the map/rankings builders.

- **Persistence (phase 2):** Not in scope for v1. Later we could write optional JSON into the config file the user already uses for path (only when that config exists), and have the first cell read it and set variables. To be decided when we add persistence.

- **Validation:** For path, “check path exists and file exists” in the load cell is enough. For date range, “start ≤ end” and a note like “Re-run from Data prep” keeps behaviour clear.

---

## 6. Suggested direction (summary)

- **Settings tab:** One place for user-friendly controls. Groups: **Data & path** (path visible, source, file name, taxonomy locale — all “Re-run from Load”), **Map display** (style, pin colours, mark lifer/last seen, popup — dynamic where we redraw), **Tables & lists** (rankings rows, maintenance distance — “Re-run from …” or next render as applicable).

- **Date filter:** In **map controls** (not Settings), so it stays map-centric. Dynamic: when user changes it, re-apply filter and redraw map; reset map does **not** reset the date filter.

- **Path:** Visible in Settings (current path and source: hardcoded / config / notebook folder). Change path only via code or config; “Re-run from Load” to apply.

- **Implementation order:** (1) Add Settings tab; wire variables with clear “Re-run from …” for non-dynamic. (2) Add date filter to map controls and make it dynamic (refactor filter + map-data build so it can be re-run on change). (3) Wire map style and pin colours to redraw (dynamic). (4) Later: persistence if desired (e.g. optional JSON in config).

This keeps the architecture (dataset static, notebook as thin UI, logic in modules), makes “restart required” obvious, and makes options discoverable without editing code.

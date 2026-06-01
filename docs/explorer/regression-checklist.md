# Regression Checklist

Run before merging refactor branches to `main`.

## Startup
- **Release / build id:** When cutting a GitHub release, bump [`explorer/app/streamlit/explorer_build_version.txt`](../../explorer/app/streamlit/explorer_build_version.txt) to match the tag (see Explorer README — optional update notice). Before merging to **`main`**, CI requires the embedded **base date** to match **today (Australia/Sydney)** and the id must **not** be behind GitHub’s latest release tag.
- Streamlit app launches locally
- Streamlit app loads successfully
- Dataset loads successfully
- Eight tabs available and data displayed (`Map`, `Checklist Statistics`, `Ranking & Lists`, `Bird Families`, `Yearly Summary`, `Country`, `Maintenance`, `Settings`)

## Map
- Visit times: if the export has missing times, popups may show **23:59** as a documented placeholder — see [explorer README — Missing checklist times](README.md#missing-checklist-times-synthetic-2359)
- **Map view** dropdown: All locations / Species locations / Lifer locations / Family locations (#71, #222)
- Lifer-only mode: one marker per lifer site, lifer marker style, popups list lifers at site + visits
- **Lifer locations** marker clustering: respects **Group nearby markers** / Settings (on by default); tune via `MAP_LIFER_LOCATION_CLUSTER_*` in `defaults.py` if needed
- Renders all locations
- Species search works (matches, highlighting, clear) when **Selected species** is active
- Species overlay works
- “Show only selected species” toggle works (only in Selected species mode)
- Basic stats banner correct for:
  - All species
  - Single species
- Legend displays
- eBird checklist links open in new tab
- Map redraw time acceptable
- **Perf (optional):** `./scripts/run_post_leaflet_perf_baseline.sh` on fixture; warm return to **All locations** should show `payload_cache_hit` on `map.all_locations_leaflet.payload` (~0 ms). Species/Family: manual run per `docs/explorer/issue-222-section-8-baseline.md`.

## Checklist Statistics
- Checklist stats load without errors
- “eBirding with others” numbers look reasonable
- eBird checklist links open

## Yearly Summary
- Yearly stats load
- Values look sane for:
  - Total species / individuals / lifers
  - Traveling / stationary / incidental counts
  - Completed / incomplete checklists
  - Days with checklist / cumulative days eBird on
  - Shared checklists / days birding with others

## Country
- Per-country accordions load (export needs `Country` and/or `State/Province`); headings in **A–Z** order by display name (`Unknown` last)
- Year columns are only those with data for that country (no wide empty years); **Total** column when more than one year
- Initial statistic rows present (e.g. Lifers world/country, totals, days, cumulative days in country)
- For **2-letter country keys**, **Lifers (country)** has **⧉** → eBird region life list (`lifelist?r=…`); **Total checklists** has **⧉** → `mychecklists/<CODE>`; **Unknown** / non-ISO keys have no links

## Ranking & Lists
- Ranking & Lists load (nested **Top Lists** / **Interesting Lists** only)
- **Interesting Lists:** **Species: Coverage** is the first expander (#262); table shows species in eBird taxonomy, observed species, and observed %; footnote mentions extinct-species handling
- Species tables (Most individuals, Most checklists, Subspecies occurrence, Seen only once) render correctly
- Links work (locations and checklists)

## Bird Families
- Bird Families tab loads (main tab, not under Ranking & Lists)
- Family summary grid and overview / species detail behave as before
- **Family coverage overview** (no family selected): *Total species* under Taxonomy; *Observed species* and *Observed species (%)* under Coverage (#262)
- Footnote covers eBird/Clements taxonomy and extinct-species inclusion/exclusion; eBird species links work in family detail

## Settings
- **Tables & lists:** Country tab sorting dropdown (Alphabetically / By life birds / By total species) reorders Country accordions only

## Maintenance
- **Location Maintenance**
  - Duplicate location detection works
  - Close locations list looks reasonable
- **Incomplete checklists**
  - Years/accordion render correctly
  - Dates and times look correct
  - eBird checklist links open
- **Sex notation in checklist comments** (if Observation Details column present and has matching strings)
  - Section appears; table columns: Date, Protocol, Species, Sex Notation, Location (link to checklist)
  - Location links open the checklist on eBird

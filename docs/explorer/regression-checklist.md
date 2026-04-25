# Regression Checklist

Run before merging refactor branches to `main`.

## Startup
- **Release / build id:** When cutting a GitHub release, bump [`explorer/app/streamlit/explorer_build_version.txt`](../../explorer/app/streamlit/explorer_build_version.txt) to match the tag (see Explorer README — optional update notice). Before merging to **`main`**, CI fails if this file is still behind GitHub’s latest release tag.
- Streamlit app launches locally
- Streamlit app loads successfully
- Dataset loads successfully
- Seven tabs available and data displayed (`Map`, `Checklist Statistics`, `Rankings & lists`, `Yearly Summary`, `Country`, `Maintenance`, `Settings`)

## Map
- Visit times: if the export has missing times, popups may show **23:59** as a documented placeholder — see [explorer README — Missing checklist times](README.md#missing-checklist-times-synthetic-2359)
- **Map view** dropdown: All locations / Selected species / Lifer locations (#71)
- Lifer-only mode: one pin per lifer site, lifer pin style, popups list lifers at site + visits
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

## Rankings & lists
- Rankings and lists load
- Species tables (Most individuals, Most checklists, Subspecies occurrence, Seen only once) render correctly
- Links work (locations and checklists)

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

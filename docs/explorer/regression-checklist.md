# Regression Checklist

Run before merging refactor branches to `main`.

## Startup
- Notebook launches locally
- Notebook launches on Binder
- Dataset loads successfully
- Five tabs available and data displayed (`Map`, `Checklist Statistics`, `Yearly Summary`, `Rankings & lists`, `Maintenance`)

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

## Rankings & lists
- Rankings and lists load
- Species tables (Most individuals, Most checklists, Subspecies occurrence, Seen only once) render correctly
- Links work (locations and checklists)

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

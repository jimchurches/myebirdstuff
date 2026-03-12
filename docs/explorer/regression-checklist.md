# Regression Checklist

Run before merging refactor branches to `main`.

## Startup
- Notebook launches locally
- Notebook launches on Binder
- Dataset loads successfully
- Five tabs available and data displayed (`Map`, `Checklist Statistics`, `Yearly Summary`, `Rankings & lists`, `Maintenance`)

## Map
- Renders all locations
- Species search works (matches, highlighting, clear)
- Species overlay works
- “Show only selected species” toggle works
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

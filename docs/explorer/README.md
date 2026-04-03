<p align="center">
  <img src="assets/personal-ebird-explorer-logo.svg" alt="Personal eBird Explorer logo" width="96" />
</p>

# Personal eBird Explorer

#### Documentation

- *Personal eBird Explorer*: [`docs/explorer/README.md`](README.md)
- *Getting started*: [`docs/explorer/getting-started.md`](getting-started.md)
- *Install*: [`docs/explorer/install.md`](install.md)
- *Feedback*: [`docs/explorer/feedback.md`](feedback.md)

## What it does

Personal eBird Explorer helps you explore your own eBird data.

While eBird excels at surfacing community data, tools for analysing your personal dataset are limited. This application focuses on filling that gap.

### Maps

  * All checklist locations
  * Species location map
  * Type-ahead species search
  * Lifer location map
  * Rich linking back to eBird
  * Optional date filters
  * Optional sub-species views
  * Ability to export maps to HTML

### Data tables

  * Checklist statistics
  * Top 200 listings of various data (configurable)
  * Location summaries
  * Species summaries
  * Country summaries
  * Yearly summaries
  * Bird family/group summaries
  * Rich linking back to eBird


>See the application to fully appreciate the different information summarised from your personal eBird data.

### Maintenance data

Some simple detections that may help in keeping your eBird records and locations
in good shape.

  * Duplicate location detection
  * Close locations detection (configurable)
  * Age & sex notation detection
  * Incomplete checklist detection

>See the **Maintenance** tab for more details.

### Application Settings and State

Map and data table behaviour can be customised within the application.

For local use, settings can be saved between sessions. With a configuration file configured, your data file path is also retained, so no upload is required at startup.

>See the `Settings` tab for details.

## Notes

### Missing checklist times (synthetic 23:59)

Some checklists in your eBird export do not include a recorded time (for example, entries from Merlin or generalised locations).

To keep sorting consistent, the explorer assigns these checklists a synthetic time of *23:59*.

This has minimal impact on most cases, but may occasionally affect time-based ordering within a day.

### More lifers reported than eBird

eBird excludes some species (for example, escaped or introduced birds) from its official lifer totals.

These exclusions are not flagged in the personal data export, so the explorer cannot apply the same rules.

As a result, lifer counts and occationaly other counts in the explorer may be slightly higher than those shown in eBird.

---

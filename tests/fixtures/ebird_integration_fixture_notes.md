# eBird Integration Fixture Notes

## Purpose

This fixture is intended for **integration-style tests** for the Personal eBird Explorer project.

It is designed to sit between:

- small synthetic **unit test** data, and
- a full personal eBird export

The aim is to provide a **human-readable, realistic mini-export** that exercises the end-to-end plumbing from:

CSV → loader → canonical datetime → species logic → statistics → duplicate handling → map preparation

## Source and privacy

This fixture is based on real public eBird export data supplied by the project owner.

To reduce noise and avoid named personal references, these columns were removed:

- `Observation Details`
- `Checklist Comments`
- `Area Covered (ha)`
- `Breeding Code`

Real bird names and real place names are intentionally preserved.

## Fixture design

This fixture is **mostly realistic**, with a deliberate mix of:

- multiple countries and states/provinces
- multiple years
- multiple protocols
- complete and incomplete checklists
- subspecies / form rows
- spuh rows
- slash-species rows
- domestic-type rows
- hybrid rows
- exact duplicate locations
- near-duplicate locations
- missing-time rows

A separate malformed-data fixture was **not** created at this stage.

For cases like missing dates or malformed times, the recommended test approach is:
- load this base fixture
- write a temporary modified copy inside the test
- assert the expected loader or downstream behaviour

## Files

Main fixture:

- `tests/fixtures/ebird_integration_fixture.csv`

Suggested companion documentation:

- this file

## High-level coverage

### Dataset size

- rows: **150**
- checklists: **15**
- unique location IDs: **15**

### Countries present

AU, ID, IN

### State / province codes present

AU-ACT, AU-NSW, AU-QLD, AU-WA, ID-NU, IN-GA

### Protocols present

- Traveling: 98 rows
- Stationary: 37 rows
- Casual / Incidental: 15 rows

### Checklist completeness

- complete rows (`All Obs Reported = 1`): 116
- incomplete rows (`All Obs Reported = 0`): 34

### Taxon edge-case rows

- species: 135
- subspecies / form: 7
- spuh: 5
- slash species: 1
- domestic type: 1
- hybrid: 1

## Canonical datetime expectations

Raw input:

- rows with missing `Time`: **3**

After loader normalisation:

- rows that should receive synthetic canonical time `23:59`: **3**
- rows with `datetime = NaT`: **0**

Notes:

- The current project behaviour treats missing/blank eBird export times as **synthetic 23:59** in the canonical datetime column.
- This allows missing-time rows to sort to the end of the day.
- Missing **dates** are not present in this fixture.

## Countable-species expectations

Using the current `countable_species_vectorized()` logic:

- total countable life species in fixture: **107**

### Countable species by year

- 2022: 17
- 2023: 21
- 2024: 29
- 2025: 39
- 2026: 29

### Lifer count by year

- 2022: 17
- 2023: 21
- 2024: 22
- 2025: 29
- 2026: 18

### Yearly summary — Total checklists per year

Cross-check: these values sum to the dataset checklist count (**15**).

- 2022: 4
- 2023: 1
- 2024: 4
- 2025: 3
- 2026: 3

## Country summary expectations (`country_summary_stats`)

Grouping uses **`State/Province`** prefixes (`AU-…`, `ID-…`, `IN-…`) via `checklist_country_keys()` — same idea as rankings location tables. The fixture has **no** standalone `Country` column, so keys are **AU**, **ID**, **IN**.

Integration tests assert:

- exactly **three** country blocks, in keys **AU**, **ID**, **IN**
- per-country **Total checklists** and **Total species** rows (including **Total** column when a country has more than one year)

### Years present per country

| Country key | Years (columns) |
|-------------|-----------------|
| AU | 2022, 2023, 2024, 2025, 2026 |
| ID | 2022, 2024 |
| IN | 2025 |

### Total checklists row (year cells + `Total` when multi-year)

| Country | Values |
|---------|--------|
| AU | 3, 1, 3, 1, 3, **11** |
| ID | 1, 1, **2** |
| IN | 2 |

The final value per row is the **Total** column (or the only cell for single-year **IN**). Sum of those finals: 11 + 2 + 2 = **15** (matches dataset checklists).

### Total species row (same column layout)

| Country | Values |
|---------|--------|
| AU | 3, 21, 11, 17, 29, **64** |
| ID | 14, 18, **29** |
| IN | 23 |

(Other rows — lifers, individuals, days, cumulative days — follow the same implementation as the Country tab; change the fixture only if you intentionally alter country/year coverage.)

### Unknown or unresolvable country codes (display)

**Computation** uses stable keys (`AU`, `_UNKNOWN`, `_R:…` for state-only strings, etc.). **Display** in the Country tab uses `country_for_display()` from `region_display` (same as rankings): ISO alpha-2 codes map to common names via **pycountry** when available; otherwise the **code is shown as-is** (e.g. invalid `XX`). Accordion titles are HTML-escaped. No crash if pycountry is missing — names fall back to the raw key.

For ISO alpha-2 keys only, the **Lifers (country)** row includes **⧉** → `https://ebird.org/lifelist?r=<CODE>` and **Total checklists** includes **⧉** → `https://ebird.org/mychecklists/<CODE>` (e.g. AU, ID, IN for this fixture). `_UNKNOWN` and `_R:…` blocks omit those links.

## Duplicate-location expectations

Using the current duplicate logic and a **200 m** threshold:

- exact duplicate location groups returned: **1**
- near-duplicate location pairs returned: **1**

Current expected exact duplicate result:

- `Bodalla ( -36.0924, 150.043724 )` appears as an exact duplicate coordinate group with **2** location IDs

Current expected near-duplicate result:

- one near-duplicate pair around **Gunderbooka** is present within the threshold

## Suggested integration-test targets

This fixture is well suited to tests around:

1. loading and required columns
2. canonical datetime creation
3. missing-time handling → synthetic `23:59`
4. countable species logic
5. slash/spuh/hybrid/domestic exclusion logic
6. year counts
7. life counts
8. yearly **Total checklists** sum vs dataset total
9. country summary: all expected countries, years, and anchor statistic rows
10. duplicate and near-duplicate detection
11. location grouping for popups
12. map-preparation functions using real-looking data

## Fixture groups

The fixture is grouped using the `Fixture Group` column.

Rows per group:

- `baseline_act_2023_hybrid`: 22 rows
- `baseline_bali_2022`: 16 rows
- `baseline_qld_stationary_2025`: 17 rows
- `baseline_wa_travel_2026`: 20 rows
- `domestic_taxon_stationary_2024`: 5 rows
- `exact_duplicate_pair_a_2026`: 6 rows
- `exact_duplicate_pair_b_2026`: 6 rows
- `goa_slash_species_2025`: 15 rows
- `goa_stationary_subspecies_2025`: 11 rows
- `incomplete_bali_2024`: 19 rows
- `missing_time_case_1`: 1 rows
- `missing_time_case_2`: 1 rows
- `missing_time_case_3`: 1 rows
- `near_duplicate_pair_a_2024`: 6 rows
- `near_duplicate_pair_b_2024`: 4 rows

## Recommended testing approach

Use this fixture for **integration-style tests** that assert known outputs.

Keep malformed-data tests separate by creating temporary modified copies inside tests rather than corrupting the main fixture.

Examples of good additional tests built from this fixture:

- blank/missing `Time` → canonical `datetime` becomes `23:59`
- missing required column → `load_dataset()` raises `ValueError`
- deliberately blank `Date` in a temporary copy → downstream behaviour is explicit and tested
- species filter for a known taxon returns expected rows and locations
- duplicate detection returns the known Bodalla and Gunderbooka cases

## Notes for future maintainers

Integration tests in `tests/explorer/test_integration_fixture.py` assert the expected values in this file. If you change the fixture CSV, update this notes file and the constants in the test module together so the tests remain the single source of truth.

This fixture is intentionally **not random**.

It is a curated mini-export designed to provide:
- realistic data variety
- stable expected outputs
- readable edge-case coverage

If it is changed later, update this notes file and the expected integration-test assertions at the same time.

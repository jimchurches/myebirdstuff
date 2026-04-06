"""
Integration-style tests using the curated eBird fixture CSV.

Validates that the fixture flows through the pipeline and produces expected
outputs. All expected values (row counts, checklist counts, countable species,
lifer-by-year, yearly totals, country-summary tables, duplicate counts,
missing-time behaviour) are taken from
tests/fixtures/ebird_integration_fixture_notes.md.

Refs #53.
"""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from explorer.core.data_loader import load_dataset, REQUIRED_COLUMNS
from explorer.core.lifer_last_seen_prep import aggregate_lifer_sites, prepare_lifer_last_seen
from explorer.core.species_logic import base_species_for_lifer, countable_species_vectorized, filter_species
from explorer.core.stats import (
    checklist_country_keys,
    compute_rankings,
    country_summary_stats,
    safe_count,
    yearly_summary_stats,
)
from explorer.core.duplicate_checks import get_map_maintenance_data
from explorer.core.working_set import rebuild_working_set_from_date_filter


# ---------------------------------------------------------------------------
# Fixture path (from fixture notes: tests/fixtures/ebird_integration_fixture.csv)
# ---------------------------------------------------------------------------

def _fixture_csv_path():
    """Path to the integration fixture CSV (repo-relative)."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "tests" / "fixtures" / "ebird_integration_fixture.csv"


@pytest.fixture(scope="module")
def fixture_df():
    """Load the integration fixture once per module; fails if file missing."""
    path = _fixture_csv_path()
    if not path.exists():
        pytest.fail(
            f"Integration fixture not found: {path}. "
            "Required for integration tests; commit tests/fixtures/ebird_integration_fixture.csv."
        )
    return load_dataset(path)


@pytest.fixture(scope="module")
def fixture_checklists(fixture_df):
    """Checklist-level view (one row per Submission ID)."""
    return fixture_df.drop_duplicates(subset=["Submission ID"]).copy()


# ---------------------------------------------------------------------------
# Expected values (from ebird_integration_fixture_notes.md)
# ---------------------------------------------------------------------------

EXPECTED_ROWS = 150
EXPECTED_CHECKLISTS = 15
EXPECTED_UNIQUE_LOCATION_IDS = 15
EXPECTED_COUNTABLE_LIFE_SPECIES = 107
EXPECTED_COUNTABLE_BY_YEAR = {2022: 17, 2023: 21, 2024: 29, 2025: 39, 2026: 29}
EXPECTED_LIFER_BY_YEAR = {2022: 17, 2023: 21, 2024: 22, 2025: 29, 2026: 18}
EXPECTED_MISSING_TIME_ROWS_CANONICAL_2359 = 3
EXPECTED_DATETIME_NAT_COUNT = 0
EXPECTED_EXACT_DUPLICATE_GROUPS = 1
EXPECTED_EXACT_DUPLICATE_LOCATION_IDS_IN_GROUP = 2
EXPECTED_NEAR_DUPLICATE_PAIRS = 1
DUPLICATE_DETECTION_THRESHOLD_M = 200
# Exact duplicate in fixture: one coordinate group at this lat/lon (notes)
EXPECTED_EXACT_DUPLICATE_LAT = -36.0924
EXPECTED_EXACT_DUPLICATE_LON = 150.043724

# Country summary (country_summary_stats on full fixture); see ebird_integration_fixture_notes.md
EXPECTED_COUNTRY_KEYS_SORTED = ("AU", "ID", "IN")
EXPECTED_COUNTRY_YEARS = {
    "AU": [2022, 2023, 2024, 2025, 2026],
    "ID": [2022, 2024],
    "IN": [2025],
}
# Per-country "Total checklists" row (year columns + Total when multi-year)
EXPECTED_COUNTRY_TOTAL_CHECKLISTS_ROW = {
    "AU": ["3", "1", "3", "1", "3", "11"],
    "ID": ["1", "1", "2"],
    "IN": ["2"],
}
EXPECTED_COUNTRY_TOTAL_SPECIES_ROW = {
    "AU": ["3", "21", "11", "17", "29", "64"],
    "ID": ["14", "18", "29"],
    "IN": ["23"],
}
EXPECTED_YEARLY_TOTAL_CHECKLISTS_PER_YEAR = ["4", "1", "4", "3", "3"]  # sums to EXPECTED_CHECKLISTS

# ---------------------------------------------------------------------------
# #103: subspecies-first lifer representation invariants (fixture derived)
# ---------------------------------------------------------------------------
EXPECTED_TAXON_LIFER_ENTRIES = 5
EXPECTED_BOTH_LIFER_ENTRIES = 5
EXPECTED_TAXON_LIFER_ENTRIES_WITH_LT3_SCI_PARTS = 0


# ---------------------------------------------------------------------------
# 0. Fixture file must exist (fail fast; do not skip)
# ---------------------------------------------------------------------------

def test_integration_fixture_file_exists():
    """Integration tests require the fixture CSV; fail if it is missing."""
    path = _fixture_csv_path()
    assert path.exists(), (
        f"Integration fixture not found: {path}. "
        "Commit tests/fixtures/ebird_integration_fixture.csv to run integration tests."
    )


# ---------------------------------------------------------------------------
# 1. Loading and required columns
# ---------------------------------------------------------------------------

def test_integration_load_dataset_succeeds(fixture_df):
    """load_dataset() loads the fixture and returns a DataFrame with required columns and datetime."""
    assert isinstance(fixture_df, pd.DataFrame)
    for col in REQUIRED_COLUMNS:
        assert col in fixture_df.columns, f"missing required column {col}"
    assert "datetime" in fixture_df.columns
    assert pd.api.types.is_datetime64_any_dtype(fixture_df["datetime"])


def test_integration_fixture_row_count(fixture_df):
    """Fixture has expected number of rows (from notes)."""
    assert len(fixture_df) == EXPECTED_ROWS


def test_integration_fixture_checklist_count(fixture_checklists):
    """Fixture has expected number of checklists."""
    assert len(fixture_checklists) == EXPECTED_CHECKLISTS


def test_integration_fixture_unique_location_ids(fixture_df):
    """Fixture has expected number of unique location IDs."""
    assert fixture_df["Location ID"].nunique() == EXPECTED_UNIQUE_LOCATION_IDS


# ---------------------------------------------------------------------------
# 2. Canonical datetime creation
# ---------------------------------------------------------------------------

def test_integration_datetime_column_created(fixture_df):
    """Canonical datetime column is present and has no NaT (notes: 0 NaT expected)."""
    assert (fixture_df["datetime"].isna()).sum() == EXPECTED_DATETIME_NAT_COUNT


def test_integration_missing_time_rows_receive_2359(fixture_df):
    """Rows with missing Time receive synthetic 23:59 in canonical datetime (notes: 3 such rows)."""
    # After loader: missing/empty/00:00 times become 23:59
    time_part = fixture_df["datetime"].dt.strftime("%H:%M")
    rows_2359 = (time_part == "23:59").sum()
    assert rows_2359 == EXPECTED_MISSING_TIME_ROWS_CANONICAL_2359


# ---------------------------------------------------------------------------
# 3. Countable species totals
# ---------------------------------------------------------------------------

def test_integration_countable_life_species_total(fixture_df):
    """Total countable life species in fixture matches notes (107)."""
    countable = countable_species_vectorized(fixture_df)
    unique_countable = countable.dropna().nunique()
    assert unique_countable == EXPECTED_COUNTABLE_LIFE_SPECIES


def test_integration_countable_species_by_year(fixture_df):
    """Countable species per year matches notes (2022–2026)."""
    countable = countable_species_vectorized(fixture_df)
    fixture_df = fixture_df.copy()
    fixture_df["_base"] = countable
    fixture_df["_year"] = pd.to_datetime(fixture_df["Date"]).dt.year
    by_year = fixture_df.dropna(subset=["_base"]).groupby("_year")["_base"].nunique()
    for year, expected in EXPECTED_COUNTABLE_BY_YEAR.items():
        assert by_year.get(year, 0) == expected, f"year {year} countable species"


def test_integration_lifer_count_by_year(fixture_df):
    """Lifer count per year matches notes (first-seen per species per year)."""
    countable = countable_species_vectorized(fixture_df)
    df = fixture_df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["_base"] = countable
    df["_year"] = df["Date"].dt.year
    first_seen = df.dropna(subset=["_base"]).groupby("_base")["Date"].min()
    first_seen_year = first_seen.dt.year
    lifers_per_year = first_seen_year.value_counts()
    for year, expected in EXPECTED_LIFER_BY_YEAR.items():
        assert lifers_per_year.get(year, 0) == expected, f"year {year} lifers"


def test_integration_lifer_subspecies_representation_flags(fixture_df):
    """#103: Fixture-derived expectations for subspecies-first lifer aggregation.

    This ensures subspecies lifer detection is derived from scientific-name structure
    (3+ parts) and correctly identifies 'both' lifer entries for subspecies-first cases.
    """
    prep = prepare_lifer_last_seen(fixture_df, base_species_fn=base_species_for_lifer)
    by_loc, _ = aggregate_lifer_sites(
        prep.lifer_lookup_df,
        prep.true_lifer_locations,
        prep.true_lifer_locations_taxon,
    )

    taxon_lifer_entries = 0
    both_lifer_entries = 0
    taxon_lifer_entries_with_lt3_parts = 0
    for _lid, entries in by_loc.items():
        for e in entries:
            if e["is_taxon_lifer"]:
                taxon_lifer_entries += 1
                parts = str(e["scientific_name"]).strip().split()
                if len(parts) < 3:
                    taxon_lifer_entries_with_lt3_parts += 1
                if e["is_base_lifer"] and e["is_taxon_lifer"]:
                    both_lifer_entries += 1

    assert taxon_lifer_entries == EXPECTED_TAXON_LIFER_ENTRIES
    assert both_lifer_entries == EXPECTED_BOTH_LIFER_ENTRIES
    assert taxon_lifer_entries_with_lt3_parts == EXPECTED_TAXON_LIFER_ENTRIES_WITH_LT3_SCI_PARTS


# ---------------------------------------------------------------------------
# 4. Duplicate and near-duplicate detection
# ---------------------------------------------------------------------------

def test_integration_exact_duplicate_detection(fixture_checklists):
    """Exact duplicate: 1 group, 2 location IDs at same coordinates (detection is by lat/lon)."""
    exact_rows, near_pairs = get_map_maintenance_data(
        fixture_checklists, threshold_m=DUPLICATE_DETECTION_THRESHOLD_M
    )
    assert len(exact_rows) == EXPECTED_EXACT_DUPLICATE_GROUPS
    assert exact_rows[0][2] == EXPECTED_EXACT_DUPLICATE_LOCATION_IDS_IN_GROUP
    # Detection is by coordinates; assert the expected group coords (from notes)
    lat, lon = exact_rows[0][3], exact_rows[0][4]
    assert round(lat, 4) == EXPECTED_EXACT_DUPLICATE_LAT
    assert round(lon, 6) == EXPECTED_EXACT_DUPLICATE_LON


def test_integration_near_duplicate_detection(fixture_checklists):
    """Near-duplicate: 1 pair within 200 m (detection is by lat/lon distance, not name)."""
    exact_rows, near_pairs = get_map_maintenance_data(
        fixture_checklists, threshold_m=DUPLICATE_DETECTION_THRESHOLD_M
    )
    assert len(near_pairs) == EXPECTED_NEAR_DUPLICATE_PAIRS
    # One pair of two distinct locations; each entry is (lid, name, lat, lon)
    pair = near_pairs[0]
    assert pair[0][0] != pair[1][0], "near-duplicate pair must be two different location IDs"
    assert pair[0][2] is not None and pair[0][3] is not None
    assert pair[1][2] is not None and pair[1][3] is not None


# ---------------------------------------------------------------------------
# 5. Species filtering (representative cases)
# ---------------------------------------------------------------------------

def test_integration_filter_species_returns_expected_rows(fixture_df):
    """Filter for a known species returns expected row count and locations."""
    # Grey Teal appears in baseline_act_2023_hybrid (West Belconnen Pond)
    filtered = filter_species(fixture_df, "Anas gracilis")
    assert len(filtered) >= 1
    assert "Anas gracilis" in filtered["Scientific Name"].values
    assert filtered["Location ID"].nunique() >= 1


def test_integration_filter_species_slash_exact_match(fixture_df):
    """Filter with slash (species-level) matches only that taxon."""
    # Fixture has "Egretta/Ardea sp." in incomplete_bali_2024
    filtered = filter_species(fixture_df, "egretta/ardea sp.")
    assert len(filtered) >= 1
    assert filtered["Scientific Name"].str.lower().str.contains("egretta/ardea", na=False).all()


# ---------------------------------------------------------------------------
# 6. Representative statistics outputs
# ---------------------------------------------------------------------------

def test_integration_full_pipeline_headline_numbers(fixture_df, fixture_checklists):
    """End-to-end: load → checklist → rankings + yearly stats → headline numbers match notes."""
    dur_col = "Duration (Min)" if "Duration (Min)" in fixture_df.columns else None
    dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in fixture_df.columns else None
    # Same flow: checklist-level df, then stats
    assert len(fixture_checklists) == EXPECTED_CHECKLISTS
    countable = countable_species_vectorized(fixture_df)
    assert countable.dropna().nunique() == EXPECTED_COUNTABLE_LIFE_SPECIES
    rankings = compute_rankings(
        fixture_df, fixture_checklists, limit=200, dur_col=dur_col, dist_col=dist_col
    )
    years_list, yearly_rows, _ = yearly_summary_stats(
        fixture_df, fixture_checklists, dur_col, dist_col
    )
    assert len(rankings["time"]) > 0
    idx_lifers = next(i for i, (label, _) in enumerate(yearly_rows) if label == "Lifers")
    lifer_vals = yearly_rows[idx_lifers][1]
    for i, yr in enumerate(years_list):
        assert int(lifer_vals[i].replace(",", "")) == EXPECTED_LIFER_BY_YEAR.get(yr, 0), f"year {yr} lifers"


def test_integration_compute_rankings_returns_expected_structure(fixture_df, fixture_checklists):
    """compute_rankings() returns dict with expected keys and non-empty rankings."""
    dur_col = "Duration (Min)" if "Duration (Min)" in fixture_df.columns else None
    dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in fixture_df.columns else None
    rankings = compute_rankings(
        fixture_df, fixture_checklists, limit=200, dur_col=dur_col, dist_col=dist_col
    )
    assert isinstance(rankings, dict)
    expected_keys = {
        "time",
        "dist",
        "species",
        "individuals",
        "species_loc",
        "individuals_loc",
        "visited",
        "seen_once",
        "species_individuals",
        "species_checklists",
        "subspecies",
        "not_seen_recently",
    }
    for k in expected_keys:
        assert k in rankings, f"missing key {k}"
    assert len(rankings["time"]) > 0
    assert len(rankings["species_loc"]) > 0
    assert len(rankings["not_seen_recently"]) > 0
    assert "ebird.org/checklist/" in rankings["not_seen_recently"][0][1]


def test_integration_yearly_summary_stats_structure(fixture_df, fixture_checklists):
    """yearly_summary_stats() returns years and rows with Total species and Lifers."""
    dur_col = "Duration (Min)" if "Duration (Min)" in fixture_df.columns else None
    dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in fixture_df.columns else None
    years_list, yearly_rows, incomplete_by_year = yearly_summary_stats(
        fixture_df, fixture_checklists, dur_col, dist_col
    )
    assert len(years_list) >= 1
    labels = [r[0] for r in yearly_rows]
    assert "Total species" in labels
    assert "Lifers" in labels
    # Values for first year should match our expected counts
    idx_species = next(i for i, (label, _) in enumerate(yearly_rows) if label == "Total species")
    idx_lifers = next(i for i, (label, _) in enumerate(yearly_rows) if label == "Lifers")
    species_vals = yearly_rows[idx_species][1]
    lifer_vals = yearly_rows[idx_lifers][1]
    assert len(species_vals) == len(years_list)
    assert len(lifer_vals) == len(years_list)
    for i, yr in enumerate(years_list):
        assert int(species_vals[i].replace(",", "")) == EXPECTED_COUNTABLE_BY_YEAR.get(yr, 0), f"year {yr} total species"
        assert int(lifer_vals[i].replace(",", "")) == EXPECTED_LIFER_BY_YEAR.get(yr, 0), f"year {yr} lifers"


def test_integration_yearly_total_checklists_sum_to_dataset_total(fixture_df, fixture_checklists):
    """Yearly 'Total checklists' columns sum to dataset checklist count (cross-check)."""
    dur_col = "Duration (Min)" if "Duration (Min)" in fixture_df.columns else None
    dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in fixture_df.columns else None
    years_list, yearly_rows, _ = yearly_summary_stats(
        fixture_df, fixture_checklists, dur_col, dist_col
    )
    idx_cl = next(i for i, (label, _) in enumerate(yearly_rows) if label == "Total checklists")
    vals = yearly_rows[idx_cl][1]
    assert vals == EXPECTED_YEARLY_TOTAL_CHECKLISTS_PER_YEAR
    assert sum(int(v.replace(",", "")) for v in vals) == EXPECTED_CHECKLISTS


def test_integration_country_keys_from_state_province(fixture_checklists):
    """Checklist-level country keys derived from State/Province match fixture countries (AU, ID, IN)."""
    keys = checklist_country_keys(fixture_checklists)
    uniq = sorted(str(x) for x in keys.dropna().unique())
    assert tuple(uniq) == EXPECTED_COUNTRY_KEYS_SORTED


def test_integration_country_summary_matches_fixture_notes(fixture_df, fixture_checklists):
    """country_summary_stats finds all three countries and per-country tables match documented values."""
    blocks = country_summary_stats(fixture_df, fixture_checklists)
    by_key = {
        ck: ([int(y) for y in years], {label: vals for label, vals in rows})
        for ck, years, rows in blocks
    }
    assert tuple(sorted(by_key)) == EXPECTED_COUNTRY_KEYS_SORTED
    for ck in EXPECTED_COUNTRY_KEYS_SORTED:
        years, rowdict = by_key[ck]
        assert years == EXPECTED_COUNTRY_YEARS[ck], f"{ck} years"
        assert rowdict["Total checklists"] == EXPECTED_COUNTRY_TOTAL_CHECKLISTS_ROW[ck], f"{ck} checklists"
        assert rowdict["Total species"] == EXPECTED_COUNTRY_TOTAL_SPECIES_ROW[ck], f"{ck} species"
    # Per-country total checklist counts sum to dataset total (11 + 2 + 2 = 15)
    totals = []
    for ck in EXPECTED_COUNTRY_KEYS_SORTED:
        vals = by_key[ck][1]["Total checklists"]
        totals.append(int(vals[-1].replace(",", "")))
    assert sum(totals) == EXPECTED_CHECKLISTS


# ---------------------------------------------------------------------------
# 7. Malformed-data (temporary copies; do not modify main fixture)
# ---------------------------------------------------------------------------

def test_integration_malformed_time_in_temp_copy():
    """Temporary copy with unparseable Time: canonical datetime behaviour is explicit (NaT or 23:59)."""
    path = _fixture_csv_path()
    if not path.exists():
        pytest.fail(f"Integration fixture not found: {path}. Required for integration tests.")
    df = pd.read_csv(path, encoding="utf-8")
    # One row with gibberish time; loader uses format="mixed", errors="coerce" -> unparseable becomes NaT
    df.loc[df.index[0], "Time"] = "not-a-time"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        try:
            df.to_csv(f.name, index=False, encoding="utf-8")
            loaded = load_dataset(f.name)
            # With unparseable time, that row gets NaT in datetime (date+time parse fails)
            assert loaded["datetime"].isna().sum() >= 1
        finally:
            os.unlink(f.name)


def test_integration_missing_required_column_raises():
    """Loading a copy of the fixture missing a required column raises ValueError."""
    path = _fixture_csv_path()
    if not path.exists():
        pytest.fail(f"Integration fixture not found: {path}. Required for integration tests.")
    df = pd.read_csv(path, encoding="utf-8")
    # Drop one required column
    df_no_count = df.drop(columns=["Count"], errors="ignore")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        try:
            df_no_count.to_csv(f.name, index=False, encoding="utf-8")
            with pytest.raises(ValueError, match="Dataset missing required columns"):
                load_dataset(f.name)
        finally:
            os.unlink(f.name)


def test_integration_blank_date_in_temp_copy():
    """Temporary copy with one blank Date: datetime gets NaT for that row (explicit behaviour)."""
    path = _fixture_csv_path()
    if not path.exists():
        pytest.fail(f"Integration fixture not found: {path}. Required for integration tests.")
    df = pd.read_csv(path, encoding="utf-8")
    # Force one row to have blank date
    df.loc[df.index[0], "Date"] = ""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        try:
            df.to_csv(f.name, index=False, encoding="utf-8")
            loaded = load_dataset(f.name)
            # That row should have NaT in datetime
            assert loaded["datetime"].isna().sum() >= 1
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# 8. Working-set / Reset View consistency (refs #66, #68)
# ---------------------------------------------------------------------------

def test_integration_working_set_full_view_matches_checklist_locations(fixture_df):
    """Reset View structures should be derived from the same checklist-eligible locations.

    Regression for Bug 1 in `rebuild_working_set_from_date_filter`:
    when df_full contains location IDs that have no checklist rows, the
    "full view" groupings/totals used by Reset View must exclude those
    locations. This traps mismatches where map popups and banner totals
    disagree after toggling date filters.
    """
    df_mod = fixture_df.copy()

    # Pick a location and simulate "no checklist rows" by nulling Submission ID.
    # This ensures that location is not part of `location_ids_with_checklists`,
    # but it remains present in df_mod so the regression would be observable.
    bad_lid = df_mod["Location ID"].iloc[0]
    df_mod.loc[df_mod["Location ID"] == bad_lid, "Submission ID"] = None

    location_ids_with_checklists = set(
        df_mod.dropna(subset=["Submission ID"])["Location ID"].unique()
    )
    assert bad_lid not in location_ids_with_checklists

    ws = rebuild_working_set_from_date_filter(
        df_mod,
        location_ids_with_checklists,
        filter_by_date=True,
        filter_start_date="2024-01-01",
        filter_end_date="2024-12-31",
        whoosh_index=None,
        map_caches=None,
    )
    assert ws is not None

    df_expected_full = df_mod[
        df_mod["Location ID"].isin(location_ids_with_checklists)
    ]
    expected_lids = set(df_expected_full["Location ID"].unique())

    assert set(ws.records_by_loc_full.keys()) == expected_lids
    assert ws.total_checklists_full == df_expected_full["Submission ID"].nunique()
    assert ws.total_individuals_full == int(
        df_expected_full["Count"].apply(safe_count).sum()
    )
    assert ws.total_species_full == int(
        countable_species_vectorized(df_expected_full).dropna().nunique()
    )

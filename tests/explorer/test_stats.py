"""Tests for explorer.core.stats module."""

import numpy as np
import pandas as pd
import pytest

from explorer.core.stats import (
    checklist_country_keys,
    country_summary_stats,
    safe_count,
    longest_streak,
    region_column,
    format_region_parts,
    compute_rankings,
    yearly_summary_stats,
    rankings_by_individuals,
    rankings_by_checklists,
    rankings_subspecies_hierarchical,
    rankings_seen_once,
    rankings_by_visits,
    rankings_by_value,
    rankings_by_location,
    rankings_not_seen_recently,
    rankings_high_counts,
)


# ---------------------------------------------------------------------------
# safe_count
# ---------------------------------------------------------------------------

class TestSafeCount:
    def test_integer_string(self):
        assert safe_count("5") == 5

    def test_x_means_present(self):
        assert safe_count("X") == 0

    def test_nan_returns_zero(self):
        assert safe_count(float("nan")) == 0

    def test_none_returns_zero(self):
        assert safe_count(None) == 0

    def test_plain_int(self):
        assert safe_count(42) == 42


# ---------------------------------------------------------------------------
# format_region_parts
# ---------------------------------------------------------------------------

class TestFormatRegionParts:
    def test_dash_splits(self):
        assert format_region_parts("AU-NSW") == ("AU", "NSW")

    def test_no_dash_returns_state_only(self):
        assert format_region_parts("NSW") == (None, "NSW")

    def test_none_input(self):
        assert format_region_parts(None) == (None, None)

    def test_empty_string(self):
        assert format_region_parts("") == (None, None)

    def test_nan_float(self):
        assert format_region_parts(float("nan")) == (None, None)


# ---------------------------------------------------------------------------
# region_column
# ---------------------------------------------------------------------------

class TestRegionColumn:
    def test_finds_country_when_preferred(self):
        df = pd.DataFrame({"Country": ["AU"], "State/Province": ["NSW"]})
        assert region_column(df, prefer_country=True) == "Country"

    def test_falls_back_to_state(self):
        df = pd.DataFrame({"State/Province": ["NSW"], "Other": [1]})
        assert region_column(df, prefer_country=True) == "State/Province"

    def test_prefers_state_when_not_prefer_country(self):
        df = pd.DataFrame({"Country": ["AU"], "State/Province": ["NSW"]})
        assert region_column(df, prefer_country=False) == "State/Province"

    def test_returns_none_when_no_match(self):
        df = pd.DataFrame({"Foo": [1]})
        assert region_column(df) is None


# ---------------------------------------------------------------------------
# longest_streak
# ---------------------------------------------------------------------------

def _make_cl(dates, locations=None, sids=None):
    """Build a minimal checklist DataFrame for streak tests."""
    n = len(dates)
    return pd.DataFrame({
        "Date": pd.to_datetime(dates),
        "Location": locations or [f"Loc{i}" for i in range(n)],
        "Submission ID": sids or [f"S{i}" for i in range(n)],
    })


class TestLongestStreak:
    def test_empty_dates(self):
        streak, *_ = longest_streak([], pd.DataFrame())
        assert streak == 0

    def test_single_day(self):
        dates = pd.to_datetime(["2025-01-01"])
        cl = _make_cl(["2025-01-01"])
        streak, start, start_loc, _, _, end, end_loc, _, _ = longest_streak(dates, cl)
        assert streak == 1
        assert start == end

    def test_three_consecutive_days(self):
        dates = pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"])
        cl = _make_cl(["2025-01-01", "2025-01-02", "2025-01-03"])
        streak, *_ = longest_streak(dates, cl)
        assert streak == 3

    def test_gap_splits_streak(self):
        dates = pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-05", "2025-01-06", "2025-01-07"])
        cl = _make_cl(["2025-01-01", "2025-01-02", "2025-01-05", "2025-01-06", "2025-01-07"])
        streak, *_ = longest_streak(dates, cl)
        assert streak == 3

    def test_locations_populated(self):
        dates = pd.to_datetime(["2025-03-01", "2025-03-02"])
        cl = _make_cl(["2025-03-01", "2025-03-02"], locations=["Park A", "Park B"], sids=["S100", "S101"])
        streak, start_date, start_loc, start_sid, start_lid, end_date, end_loc, end_sid, end_lid = longest_streak(
            dates, cl
        )
        assert streak == 2
        assert start_loc == "Park A"
        assert end_loc == "Park B"
        assert start_sid == "S100"
        assert end_sid == "S101"
        assert start_lid == ""
        assert end_lid == ""

    def test_location_ids_populated(self):
        dates = pd.to_datetime(["2025-03-01", "2025-03-02"])
        cl = pd.DataFrame(
            {
                "Date": dates,
                "Location": ["Park A", "Park B"],
                "Location ID": ["L100", "L200"],
                "Submission ID": ["S100", "S101"],
            }
        )
        _, _, _, _, start_lid, _, _, _, end_lid = longest_streak(dates, cl)
        assert start_lid == "L100"
        assert end_lid == "L200"


# ---------------------------------------------------------------------------
# rankings helpers — use minimal DataFrames
# ---------------------------------------------------------------------------

def _obs_df(rows):
    """Build observation DataFrame from list of dicts."""
    defaults = {
        "Submission ID": "S1",
        "Date": pd.Timestamp("2025-01-01"),
        "Time": "06:00",
        "Count": 1,
        "Location ID": "L1",
        "Location": "Test Location",
        "Scientific Name": "Anas gracilis",
        "Common Name": "Grey Teal",
        "Latitude": -35.0,
        "Longitude": 149.0,
    }
    data = []
    for r in rows:
        row = {**defaults, **r}
        data.append(row)
    return pd.DataFrame(data)


class TestRankingsByIndividuals:
    def test_empty_df(self):
        assert rankings_by_individuals(pd.DataFrame(), limit=10) == []

    def test_single_species(self):
        df = _obs_df([{"Count": 5}])
        rows = rankings_by_individuals(df, limit=10)
        assert len(rows) == 1
        assert rows[0][0] == "Grey Teal"
        assert rows[0][2] == "5"

    def test_excludes_spuhs(self):
        df = _obs_df([
            {"Scientific Name": "Anas sp.", "Common Name": "duck sp.", "Count": 10},
            {"Scientific Name": "Anas gracilis", "Common Name": "Grey Teal", "Count": 3},
        ])
        rows = rankings_by_individuals(df, limit=10)
        assert len(rows) == 1
        assert rows[0][0] == "Grey Teal"


class TestRankingsByChecklists:
    def test_two_checklists_same_species(self):
        df = _obs_df([
            {"Submission ID": "S1"},
            {"Submission ID": "S2"},
        ])
        rows = rankings_by_checklists(df, limit=10)
        assert len(rows) == 1
        assert rows[0][2] == "2"


class TestRankingsSubspecies:
    def test_hierarchical_subspecies_only_when_present(self):
        df = _obs_df(
            [
                {"Scientific Name": "Anas gracilis gracilis", "Common Name": "Grey Teal (gracilis)", "Count": 5},
                {"Scientific Name": "Anas gracilis", "Common Name": "Grey Teal", "Count": 10},
            ]
        )
        blocks = rankings_subspecies_hierarchical(df)
        assert len(blocks) == 1
        block = blocks[0]
        assert block["species_common"] == "Grey Teal"
        assert block["total_individuals"] == 15
        assert block["species_only_individuals"] == 10
        assert block["subspecies_total_individuals"] == 5
        assert block["subspecies_fraction"] == 5 / 15
        assert len(block["subspecies"]) == 1
        assert "gracilis" in block["subspecies"][0]["subspecies_common"].lower()

    def test_hierarchical_empty_df(self):
        assert rankings_subspecies_hierarchical(pd.DataFrame()) == []


class TestRankingsSeenOnce:
    def test_species_seen_twice_excluded(self):
        df = _obs_df([
            {"Submission ID": "S1", "Scientific Name": "Anas gracilis", "Common Name": "Grey Teal"},
            {"Submission ID": "S2", "Scientific Name": "Anas gracilis", "Common Name": "Grey Teal"},
            {"Submission ID": "S3", "Scientific Name": "Anas castanea", "Common Name": "Chestnut Teal"},
        ])
        rows = rankings_seen_once(df)
        assert len(rows) == 1
        assert "Chestnut Teal" in rows[0][0]


class TestRankingsByVisits:
    def test_most_visited(self):
        cl = pd.DataFrame({
            "Submission ID": ["S1", "S2", "S3"],
            "Location ID": ["L1", "L1", "L2"],
            "Location": ["Park A", "Park A", "Park B"],
            "Date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        })
        rows = rankings_by_visits(cl, limit=10)
        assert len(rows) == 2
        assert "Park A" in rows[0][0]
        assert "ebird.org/mychecklists/L1" in rows[0][0]
        assert rows[0][5] == "2"


class TestRankingsHighCounts:
    def test_picks_last_by_default_when_tied(self):
        df = _obs_df(
            [
                {
                    "Scientific Name": "Anas gracilis",
                    "Common Name": "Grey Teal",
                    "Submission ID": "S_old",
                    "Date": pd.Timestamp("2020-01-01"),
                    "Count": 12,
                    "Location": "Old Lake",
                    "Location ID": "L_old",
                },
                {
                    "Scientific Name": "Anas gracilis",
                    "Common Name": "Grey Teal",
                    "Submission ID": "S_new",
                    "Date": pd.Timestamp("2024-01-01"),
                    "Count": 12,
                    "Location": "New Lake",
                    "Location ID": "L_new",
                },
            ]
        )
        rows = rankings_high_counts(df)
        assert len(rows) == 1
        assert "S_new" in rows[0][4]

    def test_can_pick_first_when_tied(self):
        df = _obs_df(
            [
                {
                    "Scientific Name": "Anas gracilis",
                    "Common Name": "Grey Teal",
                    "Submission ID": "S_old",
                    "Date": pd.Timestamp("2020-01-01"),
                    "Count": 12,
                },
                {
                    "Scientific Name": "Anas gracilis",
                    "Common Name": "Grey Teal",
                    "Submission ID": "S_new",
                    "Date": pd.Timestamp("2024-01-01"),
                    "Count": 12,
                },
            ]
        )
        rows = rankings_high_counts(df, tie_break="first")
        assert len(rows) == 1
        assert "S_old" in rows[0][4]

    def test_can_sort_alphabetically(self):
        df = _obs_df(
            [
                {
                    "Scientific Name": "Anas platyrhynchos",
                    "Common Name": "Mallard",
                    "Submission ID": "S1",
                    "Date": pd.Timestamp("2024-01-01"),
                    "Count": 50,
                },
                {
                    "Scientific Name": "Anas gracilis",
                    "Common Name": "Grey Teal",
                    "Submission ID": "S2",
                    "Date": pd.Timestamp("2024-01-02"),
                    "Count": 10,
                },
            ]
        )
        rows = rankings_high_counts(df, sort_mode="alphabetical")
        assert [r[0] for r in rows] == ["Grey Teal", "Mallard"]


# ---------------------------------------------------------------------------
# rankings_not_seen_recently
# ---------------------------------------------------------------------------

class TestRankingsNotSeenRecently:
    def test_empty(self):
        assert rankings_not_seen_recently(pd.DataFrame(), reference_date=pd.Timestamp("2025-01-01")) == []

    def test_orders_longest_gap_first_among_eligible(self):
        ref = pd.Timestamp("2025-06-01")
        df = _obs_df([
            {
                "Scientific Name": "Anas gracilis",
                "Common Name": "Grey Teal",
                "Submission ID": "S1",
                "Date": pd.Timestamp("2020-01-01"),
            },
            {
                "Scientific Name": "Anas castanea",
                "Common Name": "Chestnut Teal",
                "Submission ID": "S2",
                "Date": pd.Timestamp("2025-01-01"),
            },
        ])
        rows = rankings_not_seen_recently(df, reference_date=ref)
        # Chestnut Teal last seen within trailing 12 months — excluded
        assert len(rows) == 1
        assert rows[0][0] == "Grey Teal"
        assert "S1" in rows[0][1]

    def test_excludes_species_seen_within_past_year(self):
        ref = pd.Timestamp("2025-06-01")
        df = _obs_df([{"Date": pd.Timestamp("2024-08-01")}])
        assert rankings_not_seen_recently(df, reference_date=ref) == []

    def test_last_observation_row_for_checklist_link(self):
        ref = pd.Timestamp("2025-06-01")
        df = _obs_df([
            {
                "Submission ID": "S_old",
                "Date": pd.Timestamp("2019-01-01"),
            },
            {
                "Submission ID": "S_new",
                "Date": pd.Timestamp("2024-01-01"),
            },
        ])
        rows = rankings_not_seen_recently(df, reference_date=ref)
        assert len(rows) == 1
        assert "S_new" in rows[0][1]


# ---------------------------------------------------------------------------
# compute_rankings (integration)
# ---------------------------------------------------------------------------

class TestComputeRankings:
    def test_returns_all_keys(self):
        df = _obs_df([
            {"Submission ID": "S1", "Count": 5, "Date": pd.Timestamp("2025-01-01")},
        ])
        cl = df.drop_duplicates(subset=["Submission ID"]).copy()
        cl["Date"] = pd.to_datetime(cl["Date"])
        result = compute_rankings(df, cl, limit=10, dur_col=None, dist_col=None)
        expected_keys = {"time", "dist", "species", "individuals", "species_loc", "individuals_loc",
                         "visited", "species_individuals", "species_checklists", "species_high_counts", "seen_once", "subspecies",
                         "not_seen_recently"}
        assert set(result.keys()) == expected_keys

    def test_empty_df(self):
        df = pd.DataFrame(columns=["Submission ID", "Date", "Count", "Scientific Name", "Common Name",
                                    "Location ID", "Location"])
        cl = df.copy()
        result = compute_rankings(df, cl, limit=10, dur_col=None, dist_col=None)
        for key in result:
            assert result[key] == []


# ---------------------------------------------------------------------------
# yearly_summary_stats
# ---------------------------------------------------------------------------

class TestYearlySummaryStats:
    def _minimal_data(self):
        data = {
            "Submission ID": ["S1", "S2"],
            "Date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2026-06-15")],
            "Time": ["06:00", "07:00"],
            "Count": [3, 5],
            "Location ID": ["L1", "L2"],
            "Location": ["Park A", "Park B"],
            "Scientific Name": ["Anas gracilis", "Anas castanea"],
            "Common Name": ["Grey Teal", "Chestnut Teal"],
            "Latitude": [-35.0, -36.0],
            "Longitude": [149.0, 150.0],
            "Protocol": ["Traveling", "Stationary"],
            "Duration (Min)": [30, 20],
            "Distance Traveled (km)": [1.5, 0.0],
            "All Obs Reported": [1, 1],
            "Number of Observers": [1, 2],
        }
        df = pd.DataFrame(data)
        cl = df.drop_duplicates(subset=["Submission ID"]).copy()
        cl["Date"] = pd.to_datetime(cl["Date"])
        return df, cl

    def test_returns_years_and_rows(self):
        df, cl = self._minimal_data()
        years, rows, incomplete = yearly_summary_stats(df, cl, "Duration (Min)", "Distance Traveled (km)")
        assert years == [2025, 2026]
        assert len(rows) > 0
        labels = [r[0] for r in rows]
        assert "Total species" in labels
        assert "Total checklists" in labels

    def test_empty_cl(self):
        df = pd.DataFrame(columns=["Submission ID", "Date"])
        cl = df.copy()
        years, rows, incomplete = yearly_summary_stats(df, cl, None, None)
        assert years == []
        assert rows == []

    def test_incomplete_by_year(self):
        data = {
            "Submission ID": ["S1"],
            "Date": [pd.Timestamp("2025-03-01")],
            "Time": ["06:00"],
            "Count": [1],
            "Location ID": ["L1"],
            "Location": ["Park A"],
            "Scientific Name": ["Anas gracilis"],
            "Common Name": ["Grey Teal"],
            "Protocol": ["Traveling"],
            "All Obs Reported": [0],
        }
        df = pd.DataFrame(data)
        cl = df.drop_duplicates(subset=["Submission ID"]).copy()
        cl["Date"] = pd.to_datetime(cl["Date"])
        years, rows, incomplete = yearly_summary_stats(df, cl, None, None)
        assert 2025 in incomplete
        assert len(incomplete[2025]) == 1

    def test_get_sex_notation_by_year_empty_no_column(self):
        df = pd.DataFrame({"Date": [pd.Timestamp("2024-01-01")], "Submission ID": ["S1"]})
        from explorer.core.stats import get_sex_notation_by_year
        result = get_sex_notation_by_year(df)
        assert result == {}

    def test_get_sex_notation_by_year_matches_standalone_strings(self):
        from explorer.core.stats import get_sex_notation_by_year
        df = pd.DataFrame({
            "Date": [pd.Timestamp("2024-06-01"), pd.Timestamp("2024-06-02"), pd.Timestamp("2023-01-15")],
            "Submission ID": ["S1", "S2", "S3"],
            "Location": ["Loc A", "Loc B", "Loc C"],
            "Common Name": ["Grey Teal", "Pacific Black Duck", "Cockatoo"],
            "Protocol": ["Traveling", "Stationary", "Incidental"],
            "Observation Details": ["MF", "MFFF", "MFFJ?"],
        })
        df["datetime"] = df["Date"]
        result = get_sex_notation_by_year(df)
        assert 2024 in result
        assert 2023 in result
        assert len(result[2024]) == 2
        assert len(result[2023]) == 1
        sid, date_str, loc, species, protocol, notation = result[2024][0]
        assert notation == "MF"
        assert species == "Grey Teal"
        assert sid == "S1"
        assert result[2023][0][5] == "MFFJ?"

    def test_get_sex_notation_by_year_ignores_non_matching(self):
        from explorer.core.stats import get_sex_notation_by_year
        df = pd.DataFrame({
            "Date": [pd.Timestamp("2024-06-01")],
            "Submission ID": ["S1"],
            "Location": ["Loc A"],
            "Common Name": ["Grey Teal"],
            "Protocol": ["Traveling"],
            "Observation Details": ["2 males, 1 female"],
        })
        result = get_sex_notation_by_year(df)
        assert result == {}

    def test_get_sex_notation_by_year_spaced_and_count_tokens_refs_58(self):
        """Issue #58: 1M 1F, M + F, 2M2F2?, MFMM?? (last already legacy)."""
        from explorer.core.stats import get_sex_notation_by_year
        df = pd.DataFrame({
            "Date": [
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-01-02"),
                pd.Timestamp("2024-01-03"),
                pd.Timestamp("2024-01-04"),
            ],
            "Submission ID": ["Sa", "Sb", "Sc", "Sd"],
            "Location": ["A", "B", "C", "D"],
            "Common Name": ["S1", "S2", "S3", "S4"],
            "Protocol": ["Traveling"] * 4,
            "Observation Details": ["1M 1F", "M + F", "2M2F2?", "MFMM??"],
        })
        df["datetime"] = df["Date"]
        result = get_sex_notation_by_year(df)
        assert 2024 in result
        notations = {row[5] for row in result[2024]}
        assert notations == {"1M 1F", "M + F", "2M2F2?", "MFMM??"}

    def test_get_sex_notation_by_year_rejects_prose_and_partial_refs_58(self):
        """Conservative: whole field must match; no substring matches in sentences."""
        from explorer.core.stats import get_sex_notation_by_year
        df = pd.DataFrame({
            "Date": [
                pd.Timestamp("2024-06-01"),
                pd.Timestamp("2024-06-02"),
                pd.Timestamp("2024-06-03"),
            ],
            "Submission ID": ["Sx", "Sy", "Sz"],
            "Location": ["A", "B", "C"],
            "Common Name": ["X", "Y", "Z"],
            "Protocol": ["Traveling"] * 3,
            "Observation Details": [
                "Seen MF today in flock",
                "About 2M distance",
                "Male and female present",
            ],
        })
        result = get_sex_notation_by_year(df)
        assert result == {}


# ---------------------------------------------------------------------------
# Country summary (Country tab)
# ---------------------------------------------------------------------------


class TestChecklistCountryKeys:
    def test_derives_iso_from_state_province(self):
        cl = pd.DataFrame({"State/Province": ["AU-NSW", "US-CA", "XX-YY"]})
        k = checklist_country_keys(cl)
        assert list(k) == ["AU", "US", "XX"]

    def test_unknown_when_no_region_columns(self):
        cl = pd.DataFrame({"Submission ID": ["a"], "Date": [pd.Timestamp("2025-01-01")]})
        k = checklist_country_keys(cl)
        assert list(k) == ["_UNKNOWN"]


class TestCountrySummaryStats:
    def test_lifers_world_vs_country_across_two_countries(self):
        """World lifer attributed to first country/year; country lifer when species is new there."""
        df = pd.DataFrame(
            {
                "Submission ID": ["S1", "S2", "S3"],
                "Date": [
                    pd.Timestamp("2025-01-01"),
                    pd.Timestamp("2025-01-02"),
                    pd.Timestamp("2026-03-01"),
                ],
                "Count": [1, 1, 1],
                "Scientific Name": ["Foo barbatus", "Baz qux", "Foo barbatus"],
                "Common Name": ["a", "b", "a"],
                "State/Province": ["US-CA", "AU-NSW", "AU-NSW"],
            }
        )
        cl = df.copy()
        blocks = country_summary_stats(df, cl)
        by_key = {k: (years, {label: vals for label, vals in rows}) for k, years, rows in blocks}
        assert set(by_key) == {"AU", "US"}

        us = by_key["US"][1]
        assert us["Lifers (world)"] == ["1"]
        assert us["Lifers (country)"] == ["1"]
        assert us["Total checklists"] == ["1"]

        au = by_key["AU"][1]
        assert by_key["AU"][0] == [2025, 2026]
        # Multi-year blocks include a Total column
        assert au["Lifers (world)"] == ["1", "0", "1"]
        assert au["Lifers (country)"] == ["1", "1", "2"]
        assert au["Total species"] == ["1", "1", "2"]
        assert au["Total individuals"] == ["1", "1", "2"]
        assert au["Total checklists"] == ["1", "1", "2"]
        assert au["Days with a checklist"] == ["1", "1", "2"]
        assert au["Cumulative days eBird on"] == ["1", "2", "2"]

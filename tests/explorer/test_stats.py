"""Tests for personal_ebird_explorer.stats module."""

import numpy as np
import pandas as pd
import pytest

from personal_ebird_explorer.stats import (
    safe_count,
    longest_streak,
    region_column,
    format_region_parts,
    compute_rankings,
    yearly_summary_stats,
    rankings_by_individuals,
    rankings_by_checklists,
    rankings_subspecies,
    rankings_seen_once,
    rankings_by_visits,
    rankings_by_value,
    rankings_by_location,
)


# ---------------------------------------------------------------------------
# safe_count
# ---------------------------------------------------------------------------

class TestSafeCount:
    def test_integer_string(self):
        assert safe_count("5") == 5

    def test_x_means_present(self):
        assert safe_count("X") == 1

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
        streak, start, start_loc, _, end, end_loc, _ = longest_streak(dates, cl)
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
        streak, start_date, start_loc, start_sid, end_date, end_loc, end_sid = longest_streak(dates, cl)
        assert streak == 2
        assert start_loc == "Park A"
        assert end_loc == "Park B"
        assert start_sid == "S100"
        assert end_sid == "S101"


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
    def test_only_subspecies_returned(self):
        df = _obs_df([
            {"Scientific Name": "Anas gracilis gracilis", "Common Name": "Grey Teal (gracilis)", "Count": 5},
            {"Scientific Name": "Anas gracilis", "Common Name": "Grey Teal", "Count": 10},
        ])
        rows = rankings_subspecies(df)
        assert len(rows) == 1
        assert "gracilis" in rows[0][0]

    def test_empty_df(self):
        assert rankings_subspecies(pd.DataFrame()) == []


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
        assert rows[0][5] == "2"


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
                         "visited", "species_individuals", "species_checklists", "seen_once", "subspecies"}
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

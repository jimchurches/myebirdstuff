"""Tests for personal_ebird_explorer.duplicate_checks module."""

import pandas as pd
import pytest

from personal_ebird_explorer.duplicate_checks import get_map_maintenance_data


# ---------------------------------------------------------------------------
# Exact duplicates
# ---------------------------------------------------------------------------

def test_exact_duplicates_detected():
    """Two Location IDs at the same coordinates are exact duplicates."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2"],
        "Location": ["Alpha", "Alpha duplicate"],
        "Latitude": [-35.0, -35.0],
        "Longitude": [149.0, 149.0],
    })
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert len(exact_rows) == 2
    names = {row[0] for row in exact_rows}
    assert names == {"Alpha", "Alpha duplicate"}
    for _, _, count, lat, lon in exact_rows:
        assert count == 2
        assert lat == -35.0
        assert lon == 149.0


def test_exact_duplicates_same_name_listed_once():
    """Same name at same coords appears as one row (not duplicated per Location ID)."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2"],
        "Location": ["Same Name", "Same Name"],
        "Latitude": [-35.0, -35.0],
        "Longitude": [149.0, 149.0],
    })
    exact_rows, _ = get_map_maintenance_data(data, threshold_m=10)
    assert len(exact_rows) == 1
    assert exact_rows[0][0] == "Same Name"
    assert exact_rows[0][2] == 2


def test_three_exact_duplicates_count_is_three():
    """Three Location IDs at the same coordinates give count=3."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2", "L3"],
        "Location": ["A", "B", "C"],
        "Latitude": [-35.0, -35.0, -35.0],
        "Longitude": [149.0, 149.0, 149.0],
    })
    exact_rows, _ = get_map_maintenance_data(data, threshold_m=10)
    assert len(exact_rows) == 3
    for _, _, count, _, _ in exact_rows:
        assert count == 3


# ---------------------------------------------------------------------------
# Near duplicates
# ---------------------------------------------------------------------------

def test_near_duplicates_within_threshold():
    """Two locations within threshold are returned as a near pair."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2"],
        "Location": ["Bravo", "Bravo-near"],
        "Latitude": [-35.0010, -35.00105],
        "Longitude": [149.0010, 149.00105],
    })
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert len(near_pairs) == 1
    assert {near_pairs[0][0][0], near_pairs[0][1][0]} == {"L1", "L2"}


def test_near_duplicates_beyond_threshold():
    """Two locations farther than the threshold produce no near pairs."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2"],
        "Location": ["Far1", "Far2"],
        "Latitude": [-35.0, -35.01],
        "Longitude": [149.0, 149.02],
    })
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert near_pairs == []


def test_exact_duplicates_excluded_from_near_pairs():
    """Exact duplicates (distance ≈ 0) do not appear in the near-pairs list."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2"],
        "Location": ["Same", "Same Copy"],
        "Latitude": [-35.0, -35.0],
        "Longitude": [149.0, 149.0],
    })
    _, near_pairs = get_map_maintenance_data(data, threshold_m=100)
    assert near_pairs == []


# ---------------------------------------------------------------------------
# Combined exact + near
# ---------------------------------------------------------------------------

def test_combined_exact_and_near():
    """Mixed fixture: exact duplicates and near pairs returned correctly."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2", "L3", "L4"],
        "Location": ["Alpha", "Alpha duplicate", "Bravo", "Bravo-near"],
        "Latitude": [-35.0, -35.0, -35.0010, -35.00105],
        "Longitude": [149.0, 149.0, 149.0010, 149.00105],
    })
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert len(exact_rows) == 2
    assert len(near_pairs) == 1
    assert {near_pairs[0][0][0], near_pairs[0][1][0]} == {"L3", "L4"}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_single_location_returns_empty():
    data = pd.DataFrame({
        "Location ID": ["L1"],
        "Location": ["Solo"],
        "Latitude": [-35.0],
        "Longitude": [149.0],
    })
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert near_pairs == []


def test_missing_coords_ignored():
    """Rows with None lat/lon are dropped; remaining single location gives empty results."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2"],
        "Location": ["Valid", "Missing coords"],
        "Latitude": [-35.0, None],
        "Longitude": [149.0, None],
    })
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert near_pairs == []


def test_missing_location_column_returns_empty():
    """DataFrame without a Location column returns empty results."""
    data = pd.DataFrame({
        "Location ID": ["L1"],
        "Latitude": [-35.0],
        "Longitude": [149.0],
    })
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert near_pairs == []


def test_empty_dataframe_returns_empty():
    data = pd.DataFrame(columns=["Location ID", "Location", "Latitude", "Longitude"])
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert near_pairs == []


def test_duplicate_location_ids_deduplicated():
    """If loc_df has multiple rows for the same Location ID, only one is kept."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L1", "L2"],
        "Location": ["Park A", "Park A", "Park B"],
        "Latitude": [-35.0, -35.0, -36.0],
        "Longitude": [149.0, 149.0, 150.0],
    })
    exact_rows, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert near_pairs == []


def test_near_pair_tuples_contain_coords():
    """Each element of a near pair includes (lid, name, lat, lon)."""
    data = pd.DataFrame({
        "Location ID": ["L1", "L2"],
        "Location": ["A", "B"],
        "Latitude": [-35.0010, -35.00105],
        "Longitude": [149.0010, 149.00105],
    })
    _, near_pairs = get_map_maintenance_data(data, threshold_m=10)
    assert len(near_pairs) == 1
    for loc_tuple in near_pairs[0]:
        lid, name, lat, lon = loc_tuple
        assert lid in ("L1", "L2")
        assert isinstance(lat, float)
        assert isinstance(lon, float)

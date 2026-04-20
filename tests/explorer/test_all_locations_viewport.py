"""Tests for :mod:`explorer.core.all_locations_viewport`."""

import pandas as pd

from explorer.core.all_locations_viewport import (
    ALL_LOCATIONS_FOCUS_ALL,
    coordinate_pairs_for_viewport,
    filter_location_rows_by_focus_country,
    location_id_to_country_map,
    mean_center_from_pairs,
    sorted_country_labels_from_work,
)


def test_location_id_to_country_map_first_non_null():
    df = pd.DataFrame(
        {
            "Location ID": ["A", "A", "B"],
            "Country": ["NZ", None, "Australia"],
        }
    )
    m = location_id_to_country_map(df)
    assert m["A"] == "NZ"
    assert m["B"] == "Australia"


def test_location_id_to_country_map_from_state_province_when_no_country_col():
    """eBird exports often include State/Province but not Country (aligns with Country tab keys)."""
    df = pd.DataFrame(
        {
            "Location ID": ["L1", "L2"],
            "State/Province": ["AU-NSW", "US-CA"],
        }
    )
    m = location_id_to_country_map(df)
    assert m["L1"] == "AU"
    assert m["L2"] == "US"


def test_location_id_to_country_map_missing_column():
    df = pd.DataFrame({"Location ID": ["A"]})
    assert location_id_to_country_map(df) == {}


def test_sorted_country_labels_from_work():
    df = pd.DataFrame(
        {
            "Location ID": ["x", "y"],
            "Country": ["Brazil", "argentina"],
        }
    )
    assert sorted_country_labels_from_work(df) == ["argentina", "Brazil"]


def test_filter_focus_empty_means_all_rows():
    loc = pd.DataFrame(
        {
            "Location ID": ["1", "2"],
            "Latitude": [0.0, 1.0],
            "Longitude": [0.0, 1.0],
        }
    )
    m = {"1": "X", "2": "Y"}
    out = filter_location_rows_by_focus_country(
        loc, location_id_to_country=m, focus_country=ALL_LOCATIONS_FOCUS_ALL
    )
    assert len(out) == 2


def test_coordinate_pairs_for_viewport_focus():
    loc = pd.DataFrame(
        {
            "Location ID": ["1", "2"],
            "Latitude": [10.0, 20.0],
            "Longitude": [-50.0, -40.0],
        }
    )
    m = {"1": "US", "2": "CA"}
    pairs = coordinate_pairs_for_viewport(
        loc, location_id_to_country=m, focus_country="CA"
    )
    assert pairs == [[20.0, -40.0]]


def test_coordinate_pairs_for_viewport_no_country_map():
    loc = pd.DataFrame(
        {
            "Location ID": ["1"],
            "Latitude": [1.0],
            "Longitude": [2.0],
        }
    )
    assert coordinate_pairs_for_viewport(loc, location_id_to_country={}, focus_country="US") == []


def test_mean_center_from_pairs():
    assert mean_center_from_pairs([[0.0, 0.0], [2.0, 4.0]]) == (1.0, 2.0)
    assert mean_center_from_pairs([]) is None

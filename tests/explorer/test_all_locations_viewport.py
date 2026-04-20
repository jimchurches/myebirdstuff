"""Tests for :mod:`explorer.core.all_locations_viewport`."""

import pandas as pd

from explorer.core.all_locations_viewport import (
    ALL_LOCATIONS_FOCUS_ALL,
    ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ALL_LOCATIONS_FRAMING_FIT_ALL,
    ALL_LOCATIONS_SCOPE_FOCUSED,
    all_locations_scope_option_values,
    coordinate_pairs_focused_viewport,
    coordinate_pairs_for_viewport,
    observation_row_counts_by_country_key,
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


def test_observation_row_counts_by_country_key():
    df = pd.DataFrame(
        {
            "Country": ["US", "US", "NZ"],
            "Location ID": ["a", "b", "c"],
        }
    )
    assert observation_row_counts_by_country_key(df) == {"US": 2, "NZ": 1}


def test_coordinate_pairs_focused_viewport_includes_high_observation_country():
    """Quantile trim drops a geographic outlier; country threshold adds that pin back."""
    rows = [[f"L{i}", i * 0.001, i * 0.001] for i in range(100)] + [["L100", 89.0, 179.0]]
    eff = pd.DataFrame(rows, columns=["Location ID", "Latitude", "Longitude"])
    loc_c = {f"L{i}": "NZ" for i in range(100)} | {"L100": "US"}
    obs = {"NZ": 5, "US": 25}
    out = coordinate_pairs_focused_viewport(
        eff,
        location_id_to_country=loc_c,
        observation_counts_by_country=obs,
        quantile_low=0.01,
        quantile_high=0.99,
        min_observations_full_country=20,
    )
    assert len(out) == 100
    assert any(abs(float(lat) - 89.0) < 0.01 for lat, _ in out)


def test_all_locations_scope_option_values_order():
    df = pd.DataFrame(
        {
            "Location ID": ["a", "b"],
            "Country": ["US", "NZ"],
        }
    )
    opts = all_locations_scope_option_values(df)
    assert opts[0] == ALL_LOCATIONS_FRAMING_FIT_ALL
    assert opts[1] == ALL_LOCATIONS_SCOPE_FOCUSED
    assert opts[2] == ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY
    assert set(opts[3:]) == {"NZ", "US"}

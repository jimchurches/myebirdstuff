"""Tests for Streamlit map context prep (refs #70)."""

from collections import OrderedDict

import pandas as pd
import pytest

from explorer.core.map_controller import build_species_overlay_map
from explorer.core.species_logic import base_species_for_lifer
from explorer.core.map_prep import (
    data_signature_for_caches,
    mean_center_from_location_data,
    prepare_all_locations_map_context,
)


def _tiny_df():
    return pd.DataFrame(
        {
            "Submission ID": ["S1"],
            "Date": [pd.Timestamp("2025-01-01")],
            "Time": ["06:15"],
            "datetime": [pd.Timestamp("2025-01-01 06:15")],
            "Count": [3],
            "Location ID": ["L1"],
            "Location": ["Test Location"],
            "Scientific Name": ["Anas gracilis"],
            "Common Name": ["Grey Teal"],
            "Latitude": [-35.0],
            "Longitude": [149.0],
            "Protocol": ["Traveling"],
            "Duration (Min)": [30],
            "Distance Traveled (km)": [1.5],
            "All Obs Reported": [1],
            "Number of Observers": [2],
        }
    )


def test_prepare_all_locations_map_context_matches_controller_contract():
    df = _tiny_df()
    ctx = prepare_all_locations_map_context(df)
    r = build_species_overlay_map(
        **ctx,
        selected_species="",
        popup_html_cache={},
        filtered_by_loc_cache=OrderedDict(),
        species_url_fn=None,
        base_species_fn=base_species_for_lifer,
        map_view_mode="all",
    )
    assert r.warning is None
    assert r.map is not None
    html = r.map._repr_html_()
    assert "Test Location" in html or "L1" in html


def test_prepare_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        prepare_all_locations_map_context(pd.DataFrame())


def test_data_signature_for_caches():
    df = _tiny_df()
    assert data_signature_for_caches(df, "disk") == ("disk", 1, "S1")


def test_mean_center_from_location_data():
    df = _tiny_df()
    ctx = prepare_all_locations_map_context(df)
    c = mean_center_from_location_data(ctx["effective_location_data"])
    assert c is not None
    assert c[0] == pytest.approx(-35.0)
    assert c[1] == pytest.approx(149.0)


def test_mean_center_from_location_data_empty_returns_none():
    assert mean_center_from_location_data(pd.DataFrame()) is None
    assert mean_center_from_location_data(None) is None

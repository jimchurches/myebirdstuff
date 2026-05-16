"""Tests for :mod:`explorer.core.lifer_locations_geojson` + viewport helper."""

import pandas as pd

from explorer.app.streamlit.defaults import active_map_marker_colour_scheme
from explorer.core.lifer_locations_geojson import build_lifer_locations_geojson_payload
from explorer.core.map_overlay_lifer_map import lifer_leaflet_viewport_recipe
from explorer.core.map_prep import prepare_all_locations_map_context
from explorer.core.settings_schema_defaults import MAP_MARKER_COLOUR_SCHEME_DEFAULT
from explorer.core.species_logic import base_species_for_lifer


def test_lifer_leaflet_viewport_single_point():
    vp = lifer_leaflet_viewport_recipe([[10.0, 20.0]])
    assert vp["v"] == 1
    assert vp["mode"] == "fit_bounds"
    assert vp["single_point"] is True
    assert vp["lat"] == 10.0
    assert vp["lon"] == 20.0


def test_lifer_leaflet_viewport_empty_falls_back():
    vp = lifer_leaflet_viewport_recipe([])
    assert vp["mode"] == "center_zoom"


def test_build_lifer_geojson_minimal():
    """One species lifer at one location produces one feature + structured popup lines."""
    df = pd.DataFrame(
        {
            "Submission ID": ["S1"],
            "Date": [pd.Timestamp("2024-06-01")],
            "Time": ["08:00"],
            "datetime": [pd.Timestamp("2024-06-01 08:00")],
            "Location ID": ["L1"],
            "Location": ["Patch A"],
            "Latitude": [-33.0],
            "Longitude": [151.0],
            "Scientific Name": ["Anas gracilis"],
            "Common Name": ["Grey Teal"],
            "Count": [2],
        }
    )
    ctx = prepare_all_locations_map_context(df, full_df=df)
    sch = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    rev, gj, warn, framing = build_lifer_locations_geojson_payload(
        full_location_data=ctx["full_location_data"],
        lifer_lookup_df=ctx["lifer_lookup_df"],
        true_lifer_locations=ctx["true_lifer_locations"],
        true_lifer_locations_taxon=ctx["true_lifer_locations_taxon"],
        show_subspecies_lifers=False,
        base_species_fn=base_species_for_lifer,
        visit_marker_scheme=sch,
        revision_extra="{}",
    )
    assert warn is None
    assert rev is not None
    assert gj is not None
    assert len(gj["features"]) >= 1
    props = gj["features"][0]["properties"]
    assert "lifer_popup_v1" in props
    assert props["lifer_popup_v1"]["v"] == 1
    assert "circle_pin" in props
    assert len(framing) >= 1

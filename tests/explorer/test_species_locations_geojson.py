"""Tests for :mod:`explorer.core.species_locations_geojson` + viewport helper."""

import pandas as pd

from explorer.app.streamlit.defaults import active_map_marker_colour_scheme
from explorer.core.map_overlay_visit_map import species_leaflet_viewport_recipe
from explorer.core.map_prep import prepare_all_locations_map_context
from explorer.core.settings_schema_defaults import MAP_MARKER_COLOUR_SCHEME_DEFAULT
from explorer.core.species_locations_geojson import build_species_locations_geojson_payload
from explorer.core.species_logic import base_species_for_lifer


def test_species_leaflet_viewport_single_point():
    vp = species_leaflet_viewport_recipe([[10.0, 20.0]])
    assert vp["v"] == 1
    assert vp["mode"] == "fit_bounds"
    assert vp["single_point"] is True


def test_species_leaflet_viewport_blank_center_zoom():
    vp = species_leaflet_viewport_recipe(
        [],
        blank_viewport_recipe={"mode": "center_zoom", "center": [1.0, 2.0], "zoom": 5},
    )
    assert vp["mode"] == "center_zoom"
    assert vp["center"] == [1.0, 2.0]
    assert vp["zoom"] == 5


def test_build_species_geojson_with_match_and_background_pin():
    df = pd.DataFrame(
        {
            "Submission ID": ["S1", "S2"],
            "Date": [pd.Timestamp("2024-06-01"), pd.Timestamp("2024-07-01")],
            "Time": ["08:00", "09:00"],
            "datetime": [
                pd.Timestamp("2024-06-01 08:00"),
                pd.Timestamp("2024-07-01 09:00"),
            ],
            "Location ID": ["L1", "L2"],
            "Location": ["Patch A", "Patch B"],
            "Latitude": [-33.0, -34.0],
            "Longitude": [151.0, 152.0],
            "Scientific Name": ["Anas gracilis", "Corvus brachyrhynchos"],
            "Common Name": ["Grey Teal", "American Crow"],
            "Count": [2, 1],
        }
    )
    ctx = prepare_all_locations_map_context(df, full_df=df)
    sch = active_map_marker_colour_scheme(MAP_MARKER_COLOUR_SCHEME_DEFAULT)
    rev, gj, warn, framing, roles = build_species_locations_geojson_payload(
        df=ctx["df"],
        location_data=ctx["location_data"],
        records_by_loc=ctx["records_by_loc"],
        selected_species="Anas gracilis",
        true_lifer_locations=ctx["true_lifer_locations"],
        true_lifer_locations_taxon=ctx["true_lifer_locations_taxon"],
        true_last_seen_locations=ctx["true_last_seen_locations"],
        true_last_seen_locations_taxon=ctx["true_last_seen_locations_taxon"],
        hide_non_matching_locations=False,
        mark_lifer=False,
        mark_last_seen=False,
        base_species_fn=base_species_for_lifer,
        visit_marker_scheme=sch,
        popup_visit_dates_ascending=True,
        revision_extra="{}",
    )
    assert warn is None
    assert rev is not None
    assert gj is not None
    assert len(gj["features"]) == 2
    props_match = next(
        f["properties"]
        for f in gj["features"]
        if f["properties"]["location_id"] == "L1"
    )
    assert "species_popup_v1" in props_match
    assert props_match["species_popup_v1"]["v"] == 1
    assert "circle_pin" in props_match
    props_bg = next(
        f["properties"]
        for f in gj["features"]
        if f["properties"]["location_id"] == "L2"
    )
    assert "popup_v1" in props_bg
    assert "visited" in props_bg["popup_v1"]
    assert len(framing) == 1
    assert "Species" in roles
    assert "Locations" in roles

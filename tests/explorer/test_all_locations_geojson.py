"""Tests for experimental All locations GeoJSON payload (#221)."""

from __future__ import annotations

import pandas as pd

from explorer.core.all_locations_experimental_marker_style import (
    experimental_default_scheme_circle_marker_props,
)
from explorer.core.all_locations_geojson import build_all_locations_geojson_payload


def test_build_all_locations_geojson_payload_stable_revision() -> None:
    df = pd.DataFrame(
        {
            "Location ID": ["L2", "L1"],
            "Location": ["Beta", "Alpha"],
            "Latitude": [-35.0, -34.0],
            "Longitude": [149.0, 150.0],
        }
    )
    counts = {"L1": 3, "L2": 1}
    rev1, gj1 = build_all_locations_geojson_payload(
        df,
        checklist_counts_by_location=counts,
        pin_fill_hex="#abc123",
    )
    rev2, gj2 = build_all_locations_geojson_payload(
        df,
        checklist_counts_by_location=counts,
        pin_fill_hex="#abc123",
    )
    assert rev1 == rev2
    assert gj1 == gj2
    assert gj1["type"] == "FeatureCollection"
    assert len(gj1["features"]) == 2
    # Sorted by Location ID string
    assert gj1["features"][0]["properties"]["location_id"] == "L1"
    assert gj1["features"][0]["geometry"]["coordinates"] == [150.0, -34.0]
    assert gj1["features"][0]["properties"]["lifelist_url"] == "https://ebird.org/lifelist/L1"
    assert gj1["features"][0]["properties"]["visit_checklists"] == 3
    assert gj1["features"][0]["properties"]["colour"] == "#abc123"
    pop = gj1["features"][0]["properties"]["popup_v1"]
    assert pop["v"] == 1
    assert pop["summary_lines"] == ["Checklists: 3"]
    assert pop["links"] == [{"label": "Lifelist", "href": "https://ebird.org/lifelist/L1"}]


def test_build_all_locations_geojson_payload_omit_pin_colour() -> None:
    df = pd.DataFrame(
        {
            "Location ID": ["L1"],
            "Location": ["Alpha"],
            "Latitude": [-34.0],
            "Longitude": [150.0],
        }
    )
    _, gj = build_all_locations_geojson_payload(df, omit_pin_colour=True)
    assert "colour" not in gj["features"][0]["properties"]


def test_experimental_default_scheme_circle_marker_props_matches_folium_resolver() -> None:
    d = experimental_default_scheme_circle_marker_props()
    assert {"fill_hex", "stroke_hex", "radius_px", "stroke_weight", "fill_opacity"}.issubset(d.keys())
    assert str(d["fill_hex"]).startswith("#")
    assert str(d["stroke_hex"]).startswith("#")
    assert int(d["radius_px"]) >= 1
    assert int(d["stroke_weight"]) >= 1


def test_build_all_locations_geojson_payload_revision_extra_changes_revision() -> None:
    df = pd.DataFrame(
        {
            "Location ID": ["L1"],
            "Location": ["Alpha"],
            "Latitude": [-34.0],
            "Longitude": [150.0],
        }
    )
    r_a, _ = build_all_locations_geojson_payload(df, revision_extra='{"x": 1}')
    r_b, _ = build_all_locations_geojson_payload(df, revision_extra='{"x": 2}')
    assert r_a != r_b

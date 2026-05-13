"""Tests for experimental All locations GeoJSON payload (#221)."""

from __future__ import annotations

import pandas as pd

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

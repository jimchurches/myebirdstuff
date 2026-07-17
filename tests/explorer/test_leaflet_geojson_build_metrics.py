"""Leaflet GeoJSON build metrics for perf JSONL."""

from __future__ import annotations

import pandas as pd

from explorer.core.all_locations_geojson import build_all_locations_geojson_payload
from explorer.core.leaflet_geojson_build_metrics import merge_leaflet_build_metrics_into


def test_build_all_locations_geojson_payload_emits_build_metrics() -> None:
    loc_df = pd.DataFrame(
        {
            "Location ID": ["loc1", "loc2"],
            "Location": ["A", "B"],
            "Latitude": [-37.0, -38.0],
            "Longitude": [145.0, 146.0],
        }
    )
    revision, gj, metrics = build_all_locations_geojson_payload(
        loc_df,
        checklist_counts_by_location={"loc1": 1, "loc2": 0},
    )
    assert revision is not None and len(revision) == 24
    assert gj["type"] == "FeatureCollection"
    assert {
        feature["properties"]["location_id"]: feature["geometry"]["coordinates"]
        for feature in gj["features"]
    } == {"loc1": [145.0, -37.0], "loc2": [146.0, -38.0]}
    assert set(metrics) == {
        "marker_count",
        "popup_build_count",
        "popup_build_total_ms",
    }
    assert metrics["marker_count"] == 2
    assert metrics["popup_build_count"] == 0
    assert metrics["popup_build_total_ms"] >= 0.0


def test_merge_leaflet_build_metrics_into_perf_extra() -> None:
    extra: dict = {"payload_cache_hit": False}
    merge_leaflet_build_metrics_into(
        extra,
        {"marker_count": 3, "popup_build_count": 2, "popup_build_total_ms": 1.23456},
    )
    assert extra["marker_count"] == 3
    assert extra["popup_build_count"] == 2
    assert extra["popup_build_total_ms"] == 1.235
    assert extra["payload_cache_hit"] is False

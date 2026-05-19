"""Counters for Leaflet GeoJSON payload builds (I1/I2 parity after Folium removal, #222 §8.4)."""

from __future__ import annotations

from typing import Any, TypedDict


class LeafletGeoJsonBuildMetrics(TypedDict):
    """Emitted in perf ``extra`` on ``map.*.leaflet.payload`` cache misses."""

    marker_count: int
    popup_build_count: int
    popup_build_total_ms: float


def empty_leaflet_geojson_build_metrics() -> LeafletGeoJsonBuildMetrics:
    return {
        "marker_count": 0,
        "popup_build_count": 0,
        "popup_build_total_ms": 0.0,
    }


def merge_leaflet_build_metrics_into(extra: dict[str, Any], metrics: LeafletGeoJsonBuildMetrics) -> None:
    """Copy build metrics into a perf span ``extra`` dict (rounded for JSONL)."""
    extra["marker_count"] = int(metrics["marker_count"])
    extra["popup_build_count"] = int(metrics["popup_build_count"])
    extra["popup_build_total_ms"] = round(float(metrics["popup_build_total_ms"]), 3)

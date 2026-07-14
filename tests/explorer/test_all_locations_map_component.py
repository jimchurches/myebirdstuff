"""Tests for the All locations Leaflet Streamlit component wrapper."""

from __future__ import annotations


from explorer.components.all_locations_map import render_all_locations_map_component


def test_render_all_locations_map_component_passes_zoom_debug_flag(monkeypatch):
    """``show_zoom_debug`` mirrors ``MAP_DEBUG_SHOW_ZOOM_LEVEL`` for the Leaflet component."""
    captured: dict = {}

    def fake_component(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "explorer.components.all_locations_map._component_callable",
        lambda: fake_component,
    )
    monkeypatch.setattr(
        "explorer.components.all_locations_map.MAP_DEBUG_SHOW_ZOOM_LEVEL",
        True,
    )

    render_all_locations_map_component(
        revision="rev",
        geojson={"type": "FeatureCollection", "features": []},
        height=400,
        key="k",
    )

    assert captured.get("show_zoom_debug") is True


def test_render_all_locations_map_component_passes_render_contract(monkeypatch):
    captured: dict = {}

    def fake_component(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "explorer.components.all_locations_map._component_callable",
        lambda: fake_component,
    )

    geojson = {"type": "FeatureCollection", "features": [{"type": "Feature"}]}
    render_all_locations_map_component(
        revision="rev-123",
        geojson=geojson,
        height=401.9,
        key="map-key",
        map_style="voyager",
        cluster_options={"enabled": True},
        circle_marker_style={"radius_px": 7},
        cluster_icon_style={"small": {"fill": "#123456"}},
        viewport={"mode": "center_zoom", "center": [-35.0, 149.0], "zoom": 8},
        map_theme_css="<style>.map{}</style>",
        map_popup_width_script="<script>width()</script>",
        popup_scroll_hint="both",
        popup_scroll_to_bottom=True,
        banner_html="<div>Banner</div>",
        legend_html="<div>Legend</div>",
    )

    assert captured == {
        "revision": "rev-123",
        "geojson": geojson,
        "height": 401,
        "map_style": "voyager",
        "cluster_options": {"enabled": True},
        "circle_marker_style": {"radius_px": 7},
        "cluster_icon_style": {"small": {"fill": "#123456"}},
        "viewport": {"mode": "center_zoom", "center": [-35.0, 149.0], "zoom": 8},
        "map_theme_css": "<style>.map{}</style>",
        "map_popup_width_script": "<script>width()</script>",
        "popup_scroll_hint": "both",
        "popup_scroll_to_bottom": True,
        "banner_html": "<div>Banner</div>",
        "legend_html": "<div>Legend</div>",
        "show_zoom_debug": False,
        "key": "map-key",
    }

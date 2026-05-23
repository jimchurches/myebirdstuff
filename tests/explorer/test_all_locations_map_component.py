"""Tests for the All locations Leaflet Streamlit component wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock

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


def test_render_all_locations_map_component_passes_popup_scroll_settings(monkeypatch):
    captured: dict = {}

    def fake_component(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "explorer.components.all_locations_map._component_callable",
        lambda: fake_component,
    )

    render_all_locations_map_component(
        revision="rev",
        geojson={"type": "FeatureCollection", "features": []},
        height=400,
        key="k",
        popup_scroll_hint="both",
        popup_scroll_to_bottom=True,
    )

    assert captured.get("popup_scroll_hint") == "both"
    assert captured.get("popup_scroll_to_bottom") is True

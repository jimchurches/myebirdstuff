"""Tests for Leaflet export HTML session cache keys."""

from __future__ import annotations

from explorer.presentation.leaflet_map_export_cache import leaflet_export_html_cache_key


def _base_key(**overrides):
    defaults = dict(
        leaflet_revision="rev1",
        map_height=500,
        map_style="default",
        cluster_options={"enabled": True},
        circle_marker_style={"fill_hex": "#3388ff"},
        cluster_icon_style={},
        viewport={"v": 1, "mode": "center_zoom", "center": [0, 0], "zoom": 5},
        map_theme_css="<style>.x{}</style>",
        banner_html="<motion class='pebird-map-banner'>",
        legend_html="<div class='pebird-map-legend'>",
    )
    defaults.update(overrides)
    return leaflet_export_html_cache_key(**defaults)


def test_cache_key_stable_for_same_inputs():
    assert _base_key() == _base_key()


def test_cache_key_changes_when_revision_changes():
    assert _base_key(leaflet_revision="rev1") != _base_key(leaflet_revision="rev2")


def test_cache_key_changes_when_banner_changes():
    assert _base_key(banner_html="a") != _base_key(banner_html="b")

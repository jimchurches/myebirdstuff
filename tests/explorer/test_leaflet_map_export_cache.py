"""Tests for Leaflet export HTML session cache keys."""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    ("override", "first", "second"),
    [
        ("leaflet_revision", "rev1", "rev2"),
        ("map_height", 500, 501),
        ("map_style", "default", "voyager"),
        ("cluster_options", {"enabled": True}, {"enabled": False}),
        ("circle_marker_style", {"fill_hex": "#3388ff"}, {"fill_hex": "#ff0000"}),
        ("cluster_icon_style", {}, {"small": {"fill": "#123456"}}),
        (
            "viewport",
            {"v": 1, "mode": "center_zoom", "center": [0, 0], "zoom": 5},
            {"v": 1, "mode": "center_zoom", "center": [1, 0], "zoom": 5},
        ),
        ("map_theme_css", "<style>.x{}</style>", "<style>.y{}</style>"),
        ("banner_html", "a", "b"),
        ("legend_html", "a", "b"),
    ],
)
def test_cache_key_changes_for_every_export_input(override, first, second):
    assert _base_key(**{override: first}) != _base_key(**{override: second})


def test_cache_key_is_stable_for_equivalent_dict_ordering():
    first = {"enabled": True, "radius": 5}
    second = {"radius": 5, "enabled": True}
    assert _base_key(cluster_options=first) == _base_key(cluster_options=second)

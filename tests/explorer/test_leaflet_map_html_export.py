"""Tests for standalone Leaflet map HTML export (#222 §7)."""

from __future__ import annotations

from explorer.presentation.leaflet_map_html_export import leaflet_map_to_html_bytes
from explorer.presentation.popup_v1_export_html import popup_export_html_from_properties


def test_popup_export_html_all_locations_visited():
    html = popup_export_html_from_properties(
        {
            "name": "Test Reserve",
            "lifelist_url": "https://ebird.org/lifelist/L123",
            "popup_v1": {
                "v": 1,
                "visited": {
                    "label": "Visited:",
                    "entries": [{"label": "2024-01-01", "href": "https://ebird.org/checklist/S1"}],
                },
            },
        }
    )
    assert "Test Reserve" in html
    assert "Visited:" in html
    assert "pebird-map-popup__visit-dates" in html


def test_leaflet_map_to_html_bytes_includes_viewer_and_geojson():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [145.0, -37.0]},
                "properties": {
                    "name": "Pin A",
                    "popup_v1": {"v": 1, "summary_lines": ["Checklists: 1"], "links": []},
                },
            }
        ],
    }
    raw = leaflet_map_to_html_bytes(
        geojson=geojson,
        height=400,
        map_style="default",
        cluster_options={"enabled": False},
        circle_marker_style={"fill_hex": "#3388ff", "stroke_hex": "#1c2630", "radius_px": 7},
        viewport={"v": 1, "mode": "center_zoom", "center": [-37.0, 145.0], "zoom": 10},
        map_theme_css="<style>.pebird-map-popup { color: #000; }</style>",
    )
    text = raw.decode("utf-8")
    assert "leaflet@1.9.4" in text
    assert "leaflet.markercluster" in text
    assert "pebird-map-export-config" in text
    assert "export_popup_html" in text
    assert "Pin A" in text
    assert "pebird-export-map" in text
    assert "pebird-export-map-host" in text
    assert "pebird-export-shell" in text

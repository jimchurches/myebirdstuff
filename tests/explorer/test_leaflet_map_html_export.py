"""Tests for standalone Leaflet map HTML export (#222 §7)."""

from __future__ import annotations

from explorer.presentation.leaflet_map_html_export import leaflet_map_to_html_bytes
from explorer.presentation.popup_v1_export_html import popup_export_html_from_properties


def test_popup_export_html_blocks_javascript_href():
    html = popup_export_html_from_properties(
        {
            "name": "Evil",
            "lifelist_url": "https://ebird.org/lifelist/L1",
            "popup_v1": {
                "v": 1,
                "visited": {
                    "label": "Visited:",
                    "entries": [{"label": "bad", "href": "javascript:alert(1)"}],
                },
            },
        }
    )
    assert "javascript:" not in html
    assert "pebird-map-popup__visit-link-text" in html


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
    assert "pebird-map-popup__heading-row" in html
    assert 'class="pebird-map-popup__location-heading"' in html
    assert "popup-scroll-wrapper" in html


def test_popup_export_html_visited_truncated_hint():
    html = popup_export_html_from_properties(
        {
            "name": "Busy Hotspot",
            "lifelist_url": "https://ebird.org/lifelist/L42",
            "popup_v1": {
                "v": 1,
                "visited": {
                    "label": "Visited:",
                    "entries": [
                        {
                            "label": f"2024-01-{d:02d}",
                            "href": f"https://ebird.org/checklist/S{d}",
                        }
                        for d in range(1, 6)
                    ],
                },
                "visited_truncated": True,
                "visited_total": 50,
                "visited_omitted": 45,
            },
        }
    )
    assert "pebird-map-popup__trunc-hint" in html
    assert "5 of 50 checklists shown" in html
    assert "Open lifelist" in html
    assert "(45 more)" in html
    assert 'href="https://ebird.org/lifelist/L42"' in html


def test_popup_export_html_long_location_heading_wraps_in_row():
    long_name = (
        "Lake Gilles Conservation Park--Track off Lake Gilles Rd at -33.0123, 137.4567"
    )
    html = popup_export_html_from_properties(
        {
            "name": long_name,
            "lifelist_url": "https://ebird.org/lifelist/L999",
            "popup_v1": {
                "v": 1,
                "visited": {
                    "label": "Visited:",
                    "entries": [{"label": "2025-12-19 08:57", "href": "https://ebird.org/checklist/S9"}],
                },
            },
        }
    )
    assert long_name in html
    assert "pebird-map-popup__heading-row" in html
    assert "pebird-map-popup__visited-block" in html


def test_popup_export_html_lifer_popup_v1():
    html = popup_export_html_from_properties(
        {
            "name": "Lifer Site",
            "lifelist_url": "https://ebird.org/lifelist/L55",
            "lifer_popup_v1": {
                "v": 1,
                "lines": [
                    {
                        "label": "Superb Fairywren",
                        "date": "2024-06-01",
                        "checklist_href": "https://ebird.org/checklist/S55",
                    }
                ],
            },
        }
    )
    assert "Lifer Site" in html
    assert "Superb Fairywren" in html
    assert "pebird-map-popup__visit-dates" in html
    assert "popup-scroll-wrapper" in html


def test_popup_export_html_family_popup_v1():
    html = popup_export_html_from_properties(
        {
            "name": "Family Hotspot",
            "lifelist_url": "https://ebird.org/lifelist/L66",
            "family_popup_v1": {
                "v": 1,
                "species_lines": [
                    {
                        "name": "Australian Magpie",
                        "species_href": "https://ebird.org/species/ausmag1",
                    }
                ],
            },
        }
    )
    assert "Family Hotspot" in html
    assert "Australian Magpie" in html
    assert "pebird-map-popup__species-line" in html
    assert "pebird-map-popup__scroll" in html


def test_popup_export_html_species_popup_v1():
    html = popup_export_html_from_properties(
        {
            "name": "Species Reserve",
            "lifelist_url": "https://ebird.org/lifelist/L77",
            "species_popup_v1": {
                "v": 1,
                "location_heading_margin_px": 6,
                "species_sections": [
                    {
                        "common_name": "Hooded Robin",
                        "observation_count": 1,
                        "open_by_default": True,
                        "observations": [
                            {
                                "datetime_label": "2025-01-01 09:00",
                                "observed_count": "1",
                                "checklist_href": "https://ebird.org/checklist/S77",
                                "media_href": "",
                            }
                        ],
                    }
                ],
                "visits": {
                    "summary_label": "Visited: (1)",
                    "open_by_default": True,
                    "entries": [{"label": "2025-01-01", "href": "https://ebird.org/checklist/S77"}],
                },
            },
        }
    )
    assert "Species Reserve" in html
    assert "Hooded Robin" in html
    assert "pebird-map-popup__species-seen" in html
    assert "pebird-map-popup__obs-line" in html
    assert "pebird-map-popup__all-visits" in html


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
    assert "shrinkPebirdLeafletPopups" in text
    assert "scheduleShrinkPebirdLeafletPopups" in text

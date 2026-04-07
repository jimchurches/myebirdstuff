"""Tests for Family Map Folium builder (refs #138)."""

from explorer.core.family_map_compute import FamilyLocationPin, FamilyMapBannerMetrics
from explorer.core.family_map_folium import (
    build_family_composition_folium_map,
    build_family_map_banner_element_html,
    build_family_map_banner_overlay_html,
    build_family_map_legend_overlay_html_for_pins,
    family_map_marker_style,
)


def _sample_pins():
    return (
        FamilyLocationPin(
            location_id="L1",
            location_name="Site One",
            latitude=-35.0,
            longitude=149.0,
            distinct_base_species_count=2,
            density_band_index=1,
            common_name_lines=("A", "B"),
            highlight_match=False,
        ),
        FamilyLocationPin(
            location_id="L2",
            location_name="Site Two",
            latitude=-34.0,
            longitude=150.0,
            distinct_base_species_count=1,
            density_band_index=0,
            common_name_lines=("C",),
            highlight_match=True,
        ),
    )


def test_family_map_marker_style_highlight_uses_amber_stroke():
    p = _sample_pins()[1]
    fill, stroke, w = family_map_marker_style(p)
    assert p.highlight_match
    assert stroke == "#FF7F11"
    assert w == 3


def test_build_family_composition_folium_map_html_contains_markers():
    pins = _sample_pins()
    banner = build_family_map_banner_overlay_html(
        FamilyMapBannerMetrics(
            family_name="Whistlers",
            total_species_taxonomy=12,
            species_recorded_user=5,
            locations_with_records=2,
        )
    )
    legend = build_family_map_legend_overlay_html_for_pins(pins, highlight_label="Rufous Whistler")
    m = build_family_composition_folium_map(
        pins,
        banner_html=banner,
        legend_html=legend,
        location_page_url_fn=lambda lid: f"https://ebird.org/hotspot/{lid}" if lid else None,
        species_url_fn=lambda c: f"https://ebird.org/species/x/{c}" if c == "A" else None,
    )
    html = m._repr_html_()
    assert "Site One" in html
    assert "Site Two" in html
    assert "CircleMarker" in html or "circle" in html.lower()
    assert "Whistlers" in html
    assert "12 in taxonomy" in html
    assert "Highlight: Rufous Whistler" in html
    assert "fitBounds" in html
    assert "maxZoom" in html and "6" in html


def test_build_family_map_empty_pins_still_returns_map():
    m = build_family_composition_folium_map(())
    html = m._repr_html_()
    assert "folium" in html.lower() or "map" in html.lower()


def test_build_family_map_banner_element_html_escapes():
    h = build_family_map_banner_element_html('Birds & more <script>')
    assert "&amp;" in h or "Birds" in h
    assert "<script>" not in h or "&lt;" in h

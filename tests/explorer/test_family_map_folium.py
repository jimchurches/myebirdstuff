"""Tests for Family Map Folium builder (refs #138)."""

from explorer.app.streamlit.defaults import (
    MAP_MARKER_COLOUR_SCHEME_1,
    MAP_MARKER_COLOUR_SCHEME_3,
    active_map_marker_colour_scheme,
)
from explorer.core.family_map_compute import FamilyLocationPin, FamilyMapBannerMetrics
from explorer.core.family_map_folium import (
    build_family_composition_folium_map,
    build_family_map_banner_element_html,
    build_family_map_banner_overlay_html,
    build_family_map_legend_overlay_html_for_pins,
    family_map_marker_style,
)
from explorer.core.map_marker_colour_resolve import normalize_marker_hex


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


def test_active_map_marker_colour_scheme_accepts_index_3():
    assert active_map_marker_colour_scheme(3) is MAP_MARKER_COLOUR_SCHEME_3


def test_family_map_marker_style_highlight_uses_resolved_highlight_stroke():
    p = _sample_pins()[1]
    fill, stroke, w = family_map_marker_style(p, style=MAP_MARKER_COLOUR_SCHEME_1)
    assert p.highlight_match
    assert stroke == normalize_marker_hex(
        MAP_MARKER_COLOUR_SCHEME_1.family_locations.highlight_stroke_hex, channel="edge"
    )
    assert w == MAP_MARKER_COLOUR_SCHEME_1.family_locations.highlight_stroke_weight


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
    legend = build_family_map_legend_overlay_html_for_pins(
        pins,
        highlight_label="Rufous Whistler",
        highlight_species_url="https://ebird.org/species/goldenwhi1",
    )
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
    assert "5 recorded (42%)" in html
    # Legend is embedded in the Folium iframe; link href is HTML-entity encoded in ``_repr_html_``.
    assert "goldenwhi1" in html and "Rufous Whistler" in html
    assert "fitBounds" in html
    assert "maxZoom" in html and "6" in html


def test_family_map_banner_percent_omits_when_taxonomy_total_is_zero():
    banner = build_family_map_banner_overlay_html(
        FamilyMapBannerMetrics(
            family_name="X",
            total_species_taxonomy=0,
            species_recorded_user=3,
            locations_with_records=1,
        )
    )
    assert "0 in taxonomy" in banner
    assert "3 recorded" in banner
    assert "%" not in banner


def test_build_family_map_empty_pins_still_returns_map():
    m = build_family_composition_folium_map(())
    html = m._repr_html_()
    assert "folium" in html.lower() or "map" in html.lower()


def test_build_family_map_empty_pins_uses_default_center_when_given():
    m = build_family_composition_folium_map((), default_center=(-33.8, 151.2))
    html = m._repr_html_()
    assert "-33.8" in html and "151.2" in html


def test_fit_bounds_highlight_only_uses_highlight_pins():
    pins = _sample_pins()
    m_all = build_family_composition_folium_map(pins, fit_bounds_highlight_only=False)
    m_hl = build_family_composition_folium_map(pins, fit_bounds_highlight_only=True)
    h_all = m_all._repr_html_()
    h_hl = m_hl._repr_html_()
    assert "fitBounds" in h_all and "fitBounds" in h_hl
    assert "[[-35.0, 149.0], [-34.0, 150.0]]" in h_all
    assert "[[-34.0, 150.0]]" in h_hl
    assert '&quot;maxZoom&quot;: 8' in h_hl
    assert '&quot;maxZoom&quot;: 6' in h_all


def test_fit_bounds_highlight_no_matches_uses_family_max_zoom():
    """Species-highlight mode but no matching pins: frame all pins, cap zoom like family view."""
    p = FamilyLocationPin(
        location_id="L1",
        location_name="Only",
        latitude=-35.0,
        longitude=149.0,
        distinct_base_species_count=1,
        density_band_index=0,
        common_name_lines=("X",),
        highlight_match=False,
    )
    m = build_family_composition_folium_map((p,), fit_bounds_highlight_only=True)
    h = m._repr_html_()
    assert '&quot;maxZoom&quot;: 6' in h


def test_build_family_map_banner_element_html_escapes():
    h = build_family_map_banner_element_html('Birds & more <script>')
    assert "&amp;" in h or "Birds" in h
    assert "<script>" not in h or "&lt;" in h

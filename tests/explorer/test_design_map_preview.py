"""Tests for the map marker design preview builder."""

from explorer.presentation.design_map_preview import (
    MAP_SCOPE_ALL_LOCATIONS,
    MAP_SCOPE_FAMILY_LOCATIONS,
    build_design_preview_map,
    normalize_hex_colour,
    scheme_seed_config,
)


def test_normalize_hex_colour_accepts_hash_six() -> None:
    assert normalize_hex_colour("#aabbcc") == "#aabbcc"
    assert normalize_hex_colour("FF0000") == "#FF0000"


def test_normalize_hex_colour_invalid_falls_back() -> None:
    assert normalize_hex_colour("not-a-colour") == "#FFFFFF"
    assert normalize_hex_colour("") == "#FFFFFF"


def test_scheme_seed_config_matches_active_scheme_family_colours() -> None:
    from explorer.app.streamlit.defaults import active_map_marker_colour_scheme

    sch = active_map_marker_colour_scheme(2)
    cfg = scheme_seed_config(2)
    assert cfg.family_fill_hex == sch.density_fill_hex
    assert cfg.family_stroke_hex == sch.density_stroke_hex
    assert cfg.family_highlight_stroke_hex == sch.highlight_stroke_hex
    assert cfg.default_edge == sch.marker_location_visit_edge_hex
    assert cfg.species_edge == sch.marker_species_edge_hex
    assert cfg.marker_default_fill_hex == sch.marker_default_fill_hex


def test_build_design_preview_map_returns_folium_with_markers() -> None:
    cfg = scheme_seed_config(1)
    m = build_design_preview_map(cfg, position_seed=7)
    html = m._repr_html_()
    assert "CircleMarker" in html or "circle" in html.lower()
    assert "-35" in html  # Canberra latitude area


def test_all_locations_scope_has_only_default_pins() -> None:
    cfg = scheme_seed_config(1, preview_scope=MAP_SCOPE_ALL_LOCATIONS)
    m = build_design_preview_map(cfg, position_seed=3)
    html = m._repr_html_()
    assert html.count("All locations") >= 4
    assert "species at location" not in html


def test_family_scope_has_only_family_labels() -> None:
    cfg = scheme_seed_config(1, preview_scope=MAP_SCOPE_FAMILY_LOCATIONS)
    m = build_design_preview_map(cfg, position_seed=3)
    html = m._repr_html_()
    assert html.count("species at location") >= 4
    assert "Last seen" not in html
    assert "pebird-map-legend" in html


def test_build_includes_legend_overlay() -> None:
    cfg = scheme_seed_config(1)
    m = build_design_preview_map(cfg, position_seed=1)
    html = m._repr_html_()
    assert "pebird-map-legend" in html

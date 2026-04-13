"""Tests for the map marker design preview builder."""

from explorer.app.streamlit.defaults import (
    MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK,
    MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)
from explorer.core.map_marker_colour_resolve import MAP_MARKER_CATCHALL_EDGE_HEX
from explorer.presentation.design_map_preview import (
    MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY,
    MAP_SCOPE_ALL_LOCATIONS,
    MAP_SCOPE_FAMILY_LOCATIONS,
    build_design_preview_map,
    normalize_hex_colour,
    scheme_seed_config,
)


def test_clamp_map_marker_circle_radius_px() -> None:
    assert clamp_map_marker_circle_radius_px(99) == MAP_MARKER_CIRCLE_RADIUS_PX_MAX
    assert clamp_map_marker_circle_radius_px(0) == 1
    assert clamp_map_marker_circle_radius_px(5) == 5
    assert clamp_map_marker_circle_radius_px(None) == MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK


def test_clamp_map_marker_circle_fill_opacity() -> None:
    fb = MARKER_SCHEME_FALLBACK_DEFAULT_FILL_OPACITY
    assert clamp_map_marker_circle_fill_opacity(1.5, fallback=fb) == 1.0
    assert clamp_map_marker_circle_fill_opacity(-0.1, fallback=fb) == 0.0
    assert clamp_map_marker_circle_fill_opacity(None, fallback=fb) == fb


def test_normalize_hex_colour_accepts_hash_six() -> None:
    assert normalize_hex_colour("#aabbcc") == "#aabbcc"
    assert normalize_hex_colour("FF0000") == "#FF0000"


def test_normalize_hex_colour_invalid_falls_back() -> None:
    assert normalize_hex_colour("not-a-colour") == MAP_MARKER_CATCHALL_EDGE_HEX
    assert normalize_hex_colour("") == MAP_MARKER_CATCHALL_EDGE_HEX


def test_scheme_seed_config_matches_active_scheme_family_colours() -> None:
    from explorer.app.streamlit.defaults import active_map_marker_colour_scheme
    from explorer.core.map_marker_colour_resolve import (
        normalize_marker_hex,
        resolve_family_band_colours,
        resolve_lifer_colours,
        resolve_last_seen_colours,
        resolve_location_visit_colours,
        resolve_marker_global_colours,
        resolve_species_colours,
    )

    sch = active_map_marker_colour_scheme(2)
    cfg = scheme_seed_config(2)
    for i in range(4):
        ef, es = resolve_family_band_colours(sch, i)
        assert cfg.family_fill_hex[i] == ef
        assert cfg.family_stroke_hex[i] == es
    assert cfg.family_highlight_stroke_hex == normalize_marker_hex(sch.highlight_stroke_hex, channel="edge")
    vf, ve = resolve_location_visit_colours(sch)
    assert cfg.default_fill == vf
    assert cfg.default_edge == ve
    spf, spe = resolve_species_colours(sch)
    assert cfg.species_fill == spf
    assert cfg.species_edge == spe
    gf, ge = resolve_marker_global_colours(sch)
    assert cfg.marker_default_fill_hex == gf
    assert cfg.marker_default_edge_hex == ge
    lf, le = resolve_lifer_colours(sch)
    assert cfg.lifer_fill == lf
    assert cfg.lifer_edge == le
    lsf, lse = resolve_last_seen_colours(sch)
    assert cfg.last_seen_fill == lsf
    assert cfg.last_seen_edge == lse


def test_build_design_preview_map_returns_folium_with_markers() -> None:
    cfg = scheme_seed_config(1)
    m = build_design_preview_map(cfg, position_seed=7)
    html = m._repr_html_()
    assert "CircleMarker" in html or "circle" in html.lower()
    assert "-35" in html  # Canberra latitude area
    # Design utility: default-location markers use fixed white fill + cream edge (not scheme colours).
    h = html.lower()
    assert "fff8e7" in h
    assert "#ffffff" in h or "ffffff" in h


def test_all_locations_scope_has_only_default_pins() -> None:
    cfg = scheme_seed_config(1, preview_scope=MAP_SCOPE_ALL_LOCATIONS)
    m = build_design_preview_map(cfg, position_seed=3)
    html = m._repr_html_()
    assert html.count("All locations") >= 8
    assert "species at location" not in html


def test_family_scope_shows_only_family_markers() -> None:
    cfg = scheme_seed_config(1, preview_scope=MAP_SCOPE_FAMILY_LOCATIONS)
    m = build_design_preview_map(cfg, position_seed=3)
    html = m._repr_html_()
    assert html.count("species at location") >= 8
    assert "Default location marker" not in html
    assert "All locations" not in html
    assert "Last seen" not in html
    assert "pebird-map-legend" in html


def test_build_includes_legend_overlay() -> None:
    cfg = scheme_seed_config(1)
    m = build_design_preview_map(cfg, position_seed=1)
    html = m._repr_html_()
    assert "pebird-map-legend" in html

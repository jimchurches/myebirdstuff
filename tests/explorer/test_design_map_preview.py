"""Tests for the map marker design preview builder."""

from explorer.app.streamlit.defaults import (
    MAP_MARKER_CIRCLE_RADIUS_PX_FALLBACK,
    MAP_MARKER_CIRCLE_RADIUS_PX_MAX,
    MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT,
    clamp_map_marker_circle_fill_opacity,
    clamp_map_marker_circle_radius_px,
)
from explorer.core.map_marker_colour_resolve import MAP_MARKER_CATCHALL_STROKE_HEX
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
    assert normalize_hex_colour("not-a-colour") == MAP_MARKER_CATCHALL_STROKE_HEX
    assert normalize_hex_colour("") == MAP_MARKER_CATCHALL_STROKE_HEX


def test_scheme_seed_config_matches_active_scheme_family_colours() -> None:
    from explorer.app.streamlit.defaults import active_map_marker_colour_scheme
    from explorer.core.map_marker_colour_resolve import (
        resolve_family_band_colours,
        resolve_family_highlight_stroke_hex,
        resolve_last_seen_colours,
        resolve_lifer_map_lifer_colours,
        resolve_lifer_map_subspecies_colours,
        resolve_location_visit_colours,
        resolve_marker_global_colours,
        resolve_species_colours,
        resolve_species_map_lifer_colours,
    )

    sch = active_map_marker_colour_scheme(2)
    cfg = scheme_seed_config(2)
    for i in range(4):
        ef, es = resolve_family_band_colours(sch, i)
        assert cfg.family_fill_hex[i] == ef
        assert cfg.family_stroke_hex[i] == es
    assert cfg.family_highlight_stroke_hex == resolve_family_highlight_stroke_hex(sch)
    vf, ve = resolve_location_visit_colours(sch)
    assert cfg.default_fill_hex == vf
    assert cfg.default_stroke_hex == ve
    spf, spe = resolve_species_colours(sch)
    assert cfg.species_fill_hex == spf
    assert cfg.species_stroke_hex == spe
    gf, ge = resolve_marker_global_colours(sch)
    assert cfg.marker_default_fill_hex == gf
    assert cfg.marker_default_stroke_hex == ge
    smlf, smle = resolve_species_map_lifer_colours(sch)
    assert cfg.species_lifer_fill_hex == smlf
    assert cfg.species_lifer_stroke_hex == smle
    lmlf, lmle = resolve_lifer_map_lifer_colours(sch)
    assert cfg.lifer_map_lifer_fill_hex == lmlf
    assert cfg.lifer_map_lifer_stroke_hex == lmle
    lmsf, lmse = resolve_lifer_map_subspecies_colours(sch)
    assert cfg.lifer_map_subspecies_fill_hex == lmsf
    assert cfg.lifer_map_subspecies_stroke_hex == lmse
    lsf, lse = resolve_last_seen_colours(sch)
    assert cfg.last_seen_fill_hex == lsf
    assert cfg.last_seen_stroke_hex == lse
    assert cfg.marker_cluster_tier_icon_hex is None
    assert cfg.marker_cluster_inner_fill_opacity == MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT


def test_build_design_preview_map_returns_folium_with_markers() -> None:
    cfg = scheme_seed_config(1)
    m = build_design_preview_map(cfg, position_seed=7)
    html = m._repr_html_()
    assert "CircleMarker" in html or "circle" in html.lower()
    assert "-35" in html  # Canberra latitude area
    # Scheme 1 (``defaults.py``): visit pins inherit global_defaults fill/stroke (Eucalypt palette).
    h = html.lower()
    assert "c2d6be" in h
    assert "4f8e4a" in h


def test_all_locations_scope_has_only_default_pins() -> None:
    cfg = scheme_seed_config(1, preview_scope=MAP_SCOPE_ALL_LOCATIONS)
    m = build_design_preview_map(cfg, position_seed=3)
    html = m._repr_html_()
    assert html.count("All locations") >= 8
    assert "species at location" not in html


def test_all_locations_scope_includes_seq_cluster_demo() -> None:
    cfg = scheme_seed_config(1, preview_scope=MAP_SCOPE_ALL_LOCATIONS)
    m = build_design_preview_map(cfg, position_seed=3)
    html = m._repr_html_()
    assert "SEQ cluster demo" in html
    assert "Gold Coast (small tier)" in html
    assert "-27" in html or "-28" in html


def test_family_scope_excludes_seq_cluster_demo() -> None:
    cfg = scheme_seed_config(1, preview_scope=MAP_SCOPE_FAMILY_LOCATIONS)
    m = build_design_preview_map(cfg, position_seed=3)
    html = m._repr_html_()
    assert "SEQ cluster demo" not in html


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

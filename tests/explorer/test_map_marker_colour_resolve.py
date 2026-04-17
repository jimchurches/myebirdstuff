"""Tests for :mod:`explorer.core.map_marker_colour_resolve` (hierarchical marker hex)."""

from dataclasses import replace

from explorer.app.streamlit.defaults import (
    MAP_MARKER_COLOUR_SCHEME_1,
    MAP_MARKER_COLOUR_SCHEME_3,
    active_map_marker_colour_scheme,
)
from explorer.core.map_marker_colour_resolve import (
    MAP_MARKER_CATCHALL_FILL_HEX,
    MAP_MARKER_CATCHALL_STROKE_HEX,
    MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
    MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
    family_map_resolved_circle_radius_px,
    family_map_resolved_fill_opacity,
    is_valid_hex_colour,
    normalize_marker_hex,
    resolve_family_band_colours,
    resolve_family_highlight_stroke_hex,
    resolve_location_visit_colours,
    resolve_marker_global_colours,
    resolve_species_map_background_colours,
)


def test_catchall_matches_scheme_defaults() -> None:
    assert MAP_MARKER_CATCHALL_FILL_HEX == MAP_MARKER_SCHEME_DEFAULT_FILL_HEX
    assert MAP_MARKER_CATCHALL_STROKE_HEX == MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX


def test_normalize_marker_hex_channel_fallback() -> None:
    assert normalize_marker_hex("", channel="fill") == MAP_MARKER_CATCHALL_FILL_HEX
    assert normalize_marker_hex("not-a-colour", channel="edge") == MAP_MARKER_CATCHALL_STROKE_HEX


def test_resolve_scheme_1_visit_matches_legacy_globals() -> None:
    sch = MAP_MARKER_COLOUR_SCHEME_1
    vf, ve = resolve_location_visit_colours(sch)
    gf, ge = resolve_marker_global_colours(sch)
    assert vf == gf == "#D3D3D3"
    assert ve == ge == "#008000"


def test_resolve_species_map_background_colours_scheme3_distinct_from_all_locations() -> None:
    """Bundled scheme 3 keeps species-map background separate from all-locations."""
    sch = active_map_marker_colour_scheme(3)
    al = resolve_location_visit_colours(sch)
    sm = resolve_species_map_background_colours(sch)
    assert al != sm
    assert sm == ("#EBE9ED", "#CCC7D1")


def test_resolve_experimental_visit_distinct_from_global() -> None:
    sch = active_map_marker_colour_scheme(3)
    vf, ve = resolve_location_visit_colours(sch)
    assert vf == "#D3D3D3"
    assert ve == "#857891"
    gf, _ge = resolve_marker_global_colours(sch)
    assert vf != gf


def test_is_valid_hex_colour() -> None:
    assert is_valid_hex_colour("#fff")
    assert is_valid_hex_colour("#FFFFFF")
    assert not is_valid_hex_colour("")
    assert not is_valid_hex_colour("nope")


def test_family_map_resolved_fill_opacity_experimental_scheme() -> None:
    """Experimental (scheme 3) sets both sparse and legacy family fill to 0.85."""
    assert family_map_resolved_fill_opacity(MAP_MARKER_COLOUR_SCHEME_3) == 0.85


def test_family_map_resolved_fill_opacity_prefers_family_fill_opacity_override() -> None:
    sch = replace(
        MAP_MARKER_COLOUR_SCHEME_1,
        family_locations=replace(
            MAP_MARKER_COLOUR_SCHEME_1.family_locations,
            fill_opacity_override=0.4,
        ),
    )
    assert family_map_resolved_fill_opacity(sch) == 0.4


def test_family_map_resolved_circle_radius_px_uses_marker_default_without_families_override() -> None:
    assert family_map_resolved_circle_radius_px(MAP_MARKER_COLOUR_SCHEME_3) == 5


def test_resolve_family_band_colours_omitted_density_strokes_use_global_edge() -> None:
    """When ``density_stroke_hex`` is unset, band edge matches ``global_defaults.stroke_hex``."""
    sch = replace(
        MAP_MARKER_COLOUR_SCHEME_1,
        family_locations=replace(
            MAP_MARKER_COLOUR_SCHEME_1.family_locations,
            density_stroke_hex=None,
        ),
    )
    ge = resolve_marker_global_colours(sch)[1]
    for i in range(4):
        _f, s = resolve_family_band_colours(sch, i)
        assert s == ge


def test_resolve_family_highlight_stroke_hex_inherits_global_when_unset() -> None:
    sch = replace(
        MAP_MARKER_COLOUR_SCHEME_1,
        family_locations=replace(
            MAP_MARKER_COLOUR_SCHEME_1.family_locations,
            highlight_stroke_hex=None,
        ),
    )
    assert resolve_family_highlight_stroke_hex(sch) == resolve_marker_global_colours(sch)[1]

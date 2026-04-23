"""Tests for :mod:`explorer.core.map_marker_colour_resolve` (hierarchical marker hex)."""

from dataclasses import replace

from explorer.app.streamlit.defaults import MAP_MARKER_COLOUR_SCHEME_1, active_map_marker_colour_scheme
from explorer.core.map_marker_colour_resolve import (
    MAP_MARKER_CATCHALL_FILL_HEX,
    MAP_MARKER_CATCHALL_STROKE_HEX,
    MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
    MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX,
    family_map_resolved_circle_radius_px,
    family_map_resolved_fill_opacity,
    family_map_resolved_highlight_halo_fill_opacity,
    family_map_resolved_highlight_halo_radius_px,
    family_map_resolved_highlight_halo_stroke_opacity,
    family_map_resolved_highlight_halo_stroke_weight,
    family_map_has_highlight_halo,
    is_valid_hex_colour,
    normalize_marker_hex,
    resolve_family_band_colours,
    resolve_family_highlight_halo_fill_hex,
    resolve_family_highlight_halo_stroke_hex,
    family_map_resolved_highlight_pin_stroke_hex,
    resolve_family_highlight_stroke_hex,
    resolve_location_visit_colours,
    resolve_marker_global_colours,
    resolve_species_map_background_colours,
)

from tests.colour_scheme_test_utils import BUNDLED_COLOUR_SCHEME_INDICES


def test_catchall_matches_scheme_defaults() -> None:
    assert MAP_MARKER_CATCHALL_FILL_HEX == MAP_MARKER_SCHEME_DEFAULT_FILL_HEX
    assert MAP_MARKER_CATCHALL_STROKE_HEX == MAP_MARKER_SCHEME_DEFAULT_STROKE_HEX


def test_normalize_marker_hex_channel_fallback() -> None:
    assert normalize_marker_hex("", channel="fill") == MAP_MARKER_CATCHALL_FILL_HEX
    assert normalize_marker_hex("not-a-colour", channel="edge") == MAP_MARKER_CATCHALL_STROKE_HEX


def test_resolve_location_visit_and_globals_are_valid_hex_for_all_bundled_schemes() -> None:
    for idx in BUNDLED_COLOUR_SCHEME_INDICES:
        sch = active_map_marker_colour_scheme(idx)
        vf, ve = resolve_location_visit_colours(sch)
        gf, ge = resolve_marker_global_colours(sch)
        assert is_valid_hex_colour(vf)
        assert is_valid_hex_colour(ve)
        assert is_valid_hex_colour(gf)
        assert is_valid_hex_colour(ge)


def test_resolve_species_map_background_colours_valid_for_all_bundled_schemes() -> None:
    for idx in BUNDLED_COLOUR_SCHEME_INDICES:
        sch = active_map_marker_colour_scheme(idx)
        f, s = resolve_species_map_background_colours(sch)
        assert is_valid_hex_colour(f)
        assert is_valid_hex_colour(s)


def test_is_valid_hex_colour() -> None:
    assert is_valid_hex_colour("#fff")
    assert is_valid_hex_colour("#FFFFFF")
    assert not is_valid_hex_colour("")
    assert not is_valid_hex_colour("nope")


def test_family_map_resolved_fill_opacity_within_bounds_for_all_bundled_schemes() -> None:
    for idx in BUNDLED_COLOUR_SCHEME_INDICES:
        sch = active_map_marker_colour_scheme(idx)
        fo = family_map_resolved_fill_opacity(sch)
        assert 0.0 <= fo <= 1.0


def test_family_map_resolved_fill_opacity_prefers_family_fill_opacity_override() -> None:
    sch = replace(
        MAP_MARKER_COLOUR_SCHEME_1,
        family_locations=replace(
            MAP_MARKER_COLOUR_SCHEME_1.family_locations,
            fill_opacity_override=0.4,
        ),
    )
    assert family_map_resolved_fill_opacity(sch) == 0.4


def test_family_map_resolved_circle_radius_px_matches_global_when_no_family_radius_override() -> None:
    checked = 0
    for idx in BUNDLED_COLOUR_SCHEME_INDICES:
        sch = active_map_marker_colour_scheme(idx)
        fam = sch.family_locations
        if getattr(fam, "radius_px_override", None) is not None or getattr(fam, "radius_px", None) is not None:
            continue
        md = sch.global_defaults.radius_px
        assert family_map_resolved_circle_radius_px(sch) == md
        checked += 1
    assert checked >= 1


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


def test_resolve_family_highlight_stroke_hex_uses_legend_band_edge_when_unset() -> None:
    sch = replace(
        MAP_MARKER_COLOUR_SCHEME_1,
        family_locations=replace(
            MAP_MARKER_COLOUR_SCHEME_1.family_locations,
            highlight_stroke_hex=None,
        ),
    )
    sw_i = sch.family_locations.legend_highlight_band_index
    _, edge = resolve_family_band_colours(sch, sw_i)
    assert resolve_family_highlight_stroke_hex(sch) == edge


def test_family_map_resolved_highlight_pin_stroke_hex_uses_band_edge_when_unset() -> None:
    sch = replace(
        MAP_MARKER_COLOUR_SCHEME_1,
        family_locations=replace(
            MAP_MARKER_COLOUR_SCHEME_1.family_locations,
            highlight_stroke_hex=None,
        ),
    )
    _, edge1 = resolve_family_band_colours(sch, 1)
    assert family_map_resolved_highlight_pin_stroke_hex(sch, 1) == edge1


def test_family_highlight_halo_defaults_and_overrides() -> None:
    base = MAP_MARKER_COLOUR_SCHEME_1
    sch = replace(
        base,
        family_locations=replace(
            base.family_locations,
            highlight_halo_fill_hex="#ABCDEF",
            highlight_halo_stroke_hex="#123456",
            highlight_halo_radius_delta_px=3,
            highlight_halo_fill_opacity=0.91,
            highlight_halo_stroke_opacity=0.62,
            highlight_halo_stroke_weight=5,
        ),
    )
    assert resolve_family_highlight_halo_fill_hex(sch) == "#ABCDEF"
    assert resolve_family_highlight_halo_stroke_hex(sch) == "#123456"
    assert family_map_resolved_highlight_halo_radius_px(sch) == family_map_resolved_circle_radius_px(sch) + 3
    assert family_map_resolved_highlight_halo_fill_opacity(sch) == 0.91
    assert family_map_resolved_highlight_halo_stroke_opacity(sch) == 0.62
    assert family_map_resolved_highlight_halo_stroke_weight(sch) == 5
    assert family_map_has_highlight_halo(sch)


def test_family_highlight_halo_disabled_when_unset() -> None:
    sch = replace(
        MAP_MARKER_COLOUR_SCHEME_1,
        family_locations=replace(
            MAP_MARKER_COLOUR_SCHEME_1.family_locations,
            highlight_halo_fill_hex=None,
            highlight_halo_stroke_hex=None,
            highlight_halo_radius_delta_px=None,
            highlight_halo_fill_opacity=None,
            highlight_halo_stroke_opacity=None,
            highlight_halo_stroke_weight=None,
        ),
    )
    assert not family_map_has_highlight_halo(sch)


def test_family_highlight_halo_stroke_opacity_defaults_to_one_when_unset() -> None:
    sch = replace(
        MAP_MARKER_COLOUR_SCHEME_1,
        family_locations=replace(
            MAP_MARKER_COLOUR_SCHEME_1.family_locations,
            highlight_halo_fill_hex="#FFFFFF",
            highlight_halo_stroke_opacity=None,
        ),
    )
    assert family_map_has_highlight_halo(sch)
    assert family_map_resolved_highlight_halo_stroke_opacity(sch) == 1.0

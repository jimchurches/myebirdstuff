"""Tests for hierarchical map marker hex resolution (refs #147)."""

from explorer.app.streamlit.defaults import MAP_MARKER_COLOUR_SCHEME_1, active_map_marker_colour_scheme
from explorer.core.map_marker_colour_resolve import (
    MAP_MARKER_CATCHALL_EDGE_HEX,
    MAP_MARKER_CATCHALL_FILL_HEX,
    MAP_MARKER_SCHEME_DEFAULT_EDGE_HEX,
    MAP_MARKER_SCHEME_DEFAULT_FILL_HEX,
    is_valid_hex_colour,
    normalize_marker_hex,
    resolve_location_visit_colours,
    resolve_marker_global_colours,
)


def test_catchall_matches_scheme_defaults() -> None:
    assert MAP_MARKER_CATCHALL_FILL_HEX == MAP_MARKER_SCHEME_DEFAULT_FILL_HEX
    assert MAP_MARKER_CATCHALL_EDGE_HEX == MAP_MARKER_SCHEME_DEFAULT_EDGE_HEX


def test_normalize_marker_hex_channel_fallback() -> None:
    assert normalize_marker_hex("", channel="fill") == MAP_MARKER_CATCHALL_FILL_HEX
    assert normalize_marker_hex("not-a-colour", channel="edge") == MAP_MARKER_CATCHALL_EDGE_HEX


def test_resolve_scheme_1_visit_matches_legacy_globals() -> None:
    sch = MAP_MARKER_COLOUR_SCHEME_1
    vf, ve = resolve_location_visit_colours(sch)
    gf, ge = resolve_marker_global_colours(sch)
    assert vf == gf == "#D3D3D3"
    assert ve == ge == "#008000"


def test_resolve_experimental_visit_distinct_from_global() -> None:
    sch = active_map_marker_colour_scheme(3)
    vf, ve = resolve_location_visit_colours(sch)
    assert vf == "#C7A8C1"
    assert ve == "#4D2D48"
    gf, _ge = resolve_marker_global_colours(sch)
    assert vf != gf


def test_is_valid_hex_colour() -> None:
    assert is_valid_hex_colour("#fff")
    assert is_valid_hex_colour("#FFFFFF")
    assert not is_valid_hex_colour("")
    assert not is_valid_hex_colour("nope")

"""Tests for :mod:`explorer.presentation.design_map_export`."""

from __future__ import annotations

from explorer.app.streamlit.defaults import active_map_marker_colour_scheme
from explorer.presentation.design_map_export import (
    format_full_defaults_export,
    format_map_marker_colour_scheme_dict_py,
)
from explorer.presentation.design_map_preview import (
    MAP_SCOPE_ALL,
    DesignMapPreviewConfig,
    scheme_seed_config,
)


def _sample_cfg() -> DesignMapPreviewConfig:
    return scheme_seed_config(1, preview_scope=MAP_SCOPE_ALL)


def test_format_map_marker_dict_contains_key_fields() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    text = format_map_marker_colour_scheme_dict_py(cfg, "Test name", template=sch)
    assert "display_name='Test name'" in text
    assert "marker_default_fill_hex=" in text
    assert "marker_location_visit_edge_hex=" in text
    assert "marker_species_edge_hex=" in text
    assert "circle_marker_radius_px=" in text
    assert "density_fill_hex=" in text
    assert "visit_circle_marker_radius_px=" in text
    assert "visit_stroke_weight=" in text
    assert "legend_highlight_swatch_fill_index=" in text


def test_format_full_export_is_single_expanded_scheme_block() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    text = format_full_defaults_export(cfg, display_name="Export me", template=sch)
    assert "_MAP_MARKER_COLOUR_SCHEME_EXPORT_VALUES" in text
    assert "MAP_MARKER_COLOUR_SCHEME_EXPORT = MapMarkerColourScheme" in text
    assert "marker_lifer_fill_hex=" in text
    assert "MAP_CIRCLE_MARKER_RADIUS_PX =" not in text
    # Ordered block: marker defaults before family circle_marker_* in output
    assert text.index("marker_default_fill_hex") < text.index("circle_marker_radius_px=")

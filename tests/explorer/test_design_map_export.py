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
    assert "visit_fill_opacity_lifers=" in text
    assert "legend_highlight_swatch_fill_index=" in text
    # Sparse overrides: scheme 1 has no per-collection overrides → all match default
    assert "marker_circle_radius_px_locations=" not in text
    assert "marker_circle_radius_px_species=" not in text
    assert "marker_default_circle_radius_px=" in text
    assert "marker_default_circle_fill_opacity=" in text


def test_sparse_fill_opacity_omitted_when_all_collections_match_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    md = float(cfg.marker_default_circle_fill_opacity)
    from dataclasses import replace

    flat = replace(
        cfg,
        marker_circle_fill_opacity_locations=md,
        marker_circle_fill_opacity_species=md,
        marker_circle_fill_opacity_lifers=md,
        marker_circle_fill_opacity_families=md,
    )
    text = format_map_marker_colour_scheme_dict_py(flat, "Flat", template=sch)
    assert "marker_circle_fill_opacity_locations=" not in text
    assert "marker_circle_fill_opacity_species=" not in text


def test_export_emits_radius_override_only_when_differs_from_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    d = int(cfg.marker_default_circle_radius_px)
    # Replace frozen dataclass with a copy that has one collection override
    from dataclasses import replace

    cfg2 = replace(cfg, marker_circle_radius_species=d + 3)
    text = format_map_marker_colour_scheme_dict_py(cfg2, "O", template=sch)
    assert f"marker_circle_radius_px_species={d + 3}" in text
    assert "marker_circle_radius_px_locations=" not in text
    assert "marker_circle_radius_px_lifers=" not in text
    assert "marker_circle_radius_px_families=" not in text


def test_export_emits_fill_opacity_override_only_when_differs_from_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    from dataclasses import replace

    md = float(cfg.marker_default_circle_fill_opacity)
    cfg2 = replace(
        cfg,
        marker_circle_fill_opacity_locations=md,
        marker_circle_fill_opacity_species=0.42,
        marker_circle_fill_opacity_lifers=md,
        marker_circle_fill_opacity_families=md,
    )
    text = format_map_marker_colour_scheme_dict_py(cfg2, "O", template=sch)
    assert "marker_circle_fill_opacity_species=0.42" in text
    assert "marker_circle_fill_opacity_locations=" not in text
    assert "marker_circle_fill_opacity_lifers=" not in text


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

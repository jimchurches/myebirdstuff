"""Tests for :mod:`explorer.presentation.design_map_export`."""

from __future__ import annotations

from dataclasses import replace

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
    assert "global_defaults=MapMarkerGlobalDefaults(" in text
    assert "fill_hex=" in text
    assert "all_locations=MapMarkerAllLocationsStyle(" in text
    assert "species_locations=MapMarkerSpeciesLocationsStyle(" in text
    assert "map_lifer_fill_hex=" in text
    assert "family_locations=MapMarkerFamilyLocationsStyle(" in text
    assert "pin_radius_px=" in text
    assert "density_fill_hex=" in text
    assert "stroke_weight=" in text
    assert "lifer_fill_opacity=" in text
    assert "subspecies_fill_opacity=" in text
    assert "legend_highlight_band_index=" in text
    assert "radius_override_px=" not in text
    assert "circle_radius_px=" in text
    assert "circle_fill_opacity=" in text
    assert "colours_hex=" not in text


def test_sparse_fill_opacity_omitted_when_all_collections_match_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    md = float(cfg.marker_default_circle_fill_opacity)
    flat = replace(
        cfg,
        marker_circle_fill_opacity_locations=md,
        marker_circle_fill_opacity_species=md,
        marker_circle_fill_opacity_lifer_map_lifer=md,
        marker_circle_fill_opacity_lifer_map_subspecies=md,
        marker_circle_fill_opacity_families=md,
    )
    text = format_map_marker_colour_scheme_dict_py(flat, "Flat", template=sch)
    assert "fill_opacity_override=" not in text


def test_export_emits_radius_override_only_when_differs_from_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    d = int(cfg.marker_default_circle_radius_px)
    cfg2 = replace(cfg, marker_circle_radius_species=d + 3)
    text = format_map_marker_colour_scheme_dict_py(cfg2, "O", template=sch)
    assert f"radius_override_px={d + 3}" in text
    assert text.count("radius_override_px=") == 1


def test_export_emits_fill_opacity_override_only_when_differs_from_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    md = float(cfg.marker_default_circle_fill_opacity)
    cfg2 = replace(
        cfg,
        marker_circle_fill_opacity_locations=md,
        marker_circle_fill_opacity_species=0.42,
        marker_circle_fill_opacity_lifer_map_lifer=md,
        marker_circle_fill_opacity_lifer_map_subspecies=md,
        marker_circle_fill_opacity_families=md,
    )
    text = format_map_marker_colour_scheme_dict_py(cfg2, "O", template=sch)
    assert "fill_opacity_override=0.42" in text


def test_format_full_export_is_single_expanded_scheme_block() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    text = format_full_defaults_export(cfg, display_name="Export me", template=sch)
    assert "MAP_MARKER_COLOUR_SCHEME_EXPORT = MapMarkerColourScheme(" in text
    assert "map_lifer_fill_hex=" in text
    assert "MAP_CIRCLE_MARKER_RADIUS_PX =" not in text
    assert text.index("fill_hex=") < text.index("pin_radius_px=")


def test_export_emits_marker_cluster_colours_hex_when_configured() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    cfg2 = replace(
        cfg,
        marker_cluster_colours_hex=(
            "#b91c1c",
            "#991b1b",
            "#fecaca",
            "#eab308",
            "#a16207",
            "#fef08a",
            "#16a34a",
            "#166534",
            "#bbf7d0",
        ),
    )
    text = format_map_marker_colour_scheme_dict_py(cfg2, "Clusters", template=sch)
    assert "colours_hex=" in text
    assert "'#b91c1c'" in text
    assert "'#991b1b'" in text
    assert "'#eab308'" in text
    assert "'#a16207'" in text
    assert "'#16a34a'" in text
    assert "'#166534'" in text

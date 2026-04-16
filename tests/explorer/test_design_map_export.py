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
    assert "lifer_fill_hex=" in text
    assert "family_locations=MapMarkerFamilyLocationsStyle(" in text
    assert "radius_px=" in text
    assert "density_fill_hex=" in text
    assert "stroke_weight=" in text
    assert "lifer_fill_opacity=" in text
    assert "subspecies_fill_opacity=" in text
    assert "legend_highlight_band_index=" in text
    assert "radius_override_px=" not in text
    assert "colours_hex=" not in text


def test_export_omits_hex_when_collections_match_global_defaults() -> None:
    """Sparse export: per-map fill/stroke hex lines are omitted when they match globals."""
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    g_fill = cfg.marker_default_fill_hex
    g_stroke = cfg.marker_default_stroke_hex
    flat = replace(
        cfg,
        default_fill_hex=g_fill,
        default_stroke_hex=g_stroke,
        species_fill_hex=g_fill,
        species_stroke_hex=g_stroke,
        species_lifer_fill_hex=g_fill,
        species_lifer_stroke_hex=g_stroke,
        last_seen_fill_hex=g_fill,
        last_seen_stroke_hex=g_stroke,
        lifer_map_lifer_fill_hex=g_fill,
        lifer_map_lifer_stroke_hex=g_stroke,
        lifer_map_subspecies_fill_hex=g_fill,
        lifer_map_subspecies_stroke_hex=g_stroke,
        species_map_background_fill_hex=g_fill,
        species_map_background_stroke_hex=g_stroke,
    )
    text = format_map_marker_colour_scheme_dict_py(flat, "G", template=sch)
    al_start = text.index("all_locations=")
    sp_start = text.index("species_locations=")
    al_block = text[al_start:sp_start]
    assert "        fill_hex=" not in al_block
    assert "        stroke_hex=" not in al_block
    sp_end = text.index("species_map_background=")
    species_block = text[sp_start:sp_end]
    for needle in (
        "        fill_hex=",
        "        stroke_hex=",
        "        lifer_fill_hex=",
        "        lifer_stroke_hex=",
        "        last_seen_fill_hex=",
        "        last_seen_stroke_hex=",
    ):
        assert needle not in species_block
    smb_start = sp_end
    smb_end = text.index("lifer_locations=")
    smb_block = text[smb_start:smb_end]
    assert "        fill_hex=" not in smb_block
    assert "        stroke_hex=" not in smb_block
    ll_end = text.index("family_locations=")
    ll_block = text[smb_end:ll_end]
    for needle in (
        "        lifer_fill_hex=",
        "        lifer_stroke_hex=",
        "        subspecies_fill_hex=",
        "        subspecies_stroke_hex=",
    ):
        assert needle not in ll_block


def test_sparse_fill_opacity_omitted_when_all_collections_match_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    md = float(cfg.marker_default_fill_opacity)
    flat = replace(
        cfg,
        marker_fill_opacity_locations=md,
        marker_fill_opacity_species=md,
        marker_fill_opacity_lifer_map_lifer=md,
        marker_fill_opacity_lifer_map_subspecies=md,
        marker_fill_opacity_families=md,
    )
    text = format_map_marker_colour_scheme_dict_py(flat, "Flat", template=sch)
    assert "fill_opacity_override=" not in text


def test_export_emits_radius_px_only_when_differs_from_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    d = int(cfg.marker_default_radius_px)
    cfg2 = replace(cfg, marker_radius_species=d + 3)
    text = format_map_marker_colour_scheme_dict_py(cfg2, "O", template=sch)
    assert f"radius_px={d + 3}" in text
    assert text.count(f"radius_px={d + 3}") >= 1


def test_export_emits_species_fill_opacity_when_differs_from_default() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    md = float(cfg.marker_default_fill_opacity)
    cfg2 = replace(
        cfg,
        marker_fill_opacity_locations=md,
        marker_fill_opacity_species=0.42,
        marker_fill_opacity_lifer_map_lifer=md,
        marker_fill_opacity_lifer_map_subspecies=md,
        marker_fill_opacity_families=md,
    )
    text = format_map_marker_colour_scheme_dict_py(cfg2, "O", template=sch)
    assert "fill_opacity=0.42" in text
    assert "species_locations=MapMarkerSpeciesLocationsStyle(" in text
    assert text.index("species_locations=") < text.index("fill_opacity=0.42")


def test_format_full_export_is_single_expanded_scheme_block() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    text = format_full_defaults_export(cfg, display_name="Export me", template=sch)
    assert "MAP_MARKER_COLOUR_SCHEME_EXPORT = MapMarkerColourScheme(" in text
    assert "lifer_fill_hex=" in text
    assert "MAP_CIRCLE_MARKER_RADIUS_PX =" not in text
    assert text.index("fill_hex=") < text.index("density_fill_hex=")


def test_export_scheme3_omits_redundant_fill_opacity_lines() -> None:
    """Sparse export: species/lifer inherit global opacity; family has no duplicate override."""
    cfg = scheme_seed_config(3, preview_scope=MAP_SCOPE_ALL)
    sch = active_map_marker_colour_scheme(3)
    text = format_map_marker_colour_scheme_dict_py(cfg, "Ash Violet", template=sch)
    sp_start = text.index("species_locations=")
    sm_start = text.index("species_map_background=")
    species_block = text[sp_start:sm_start]
    assert "fill_opacity=" not in species_block
    ll_start = text.index("lifer_locations=")
    fam_start = text.index("family_locations=")
    lifer_block = text[ll_start:fam_start]
    assert "lifer_fill_opacity=" not in lifer_block
    assert "subspecies_fill_opacity=" not in lifer_block
    vp_start = text.index("viewport=")
    fam_block = text[fam_start:vp_start]
    assert "fill_opacity_override=" not in fam_block


def test_export_emits_marker_cluster_tier_icon_hex_when_configured() -> None:
    cfg = _sample_cfg()
    sch = active_map_marker_colour_scheme(1)
    cfg2 = replace(
        cfg,
        marker_cluster_tier_icon_hex=(
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
    assert "tier_icon_hex=" in text
    assert "'#b91c1c'" in text
    assert "'#991b1b'" in text
    assert "'#eab308'" in text
    assert "'#a16207'" in text
    assert "'#16a34a'" in text
    assert "'#166534'" in text

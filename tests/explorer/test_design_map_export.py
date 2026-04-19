"""Tests for :mod:`explorer.presentation.design_map_export`."""

from __future__ import annotations

from dataclasses import replace

from explorer.presentation.design_map_export import (
    format_full_defaults_export,
    format_map_marker_colour_scheme_dict_py,
)
from explorer.core.settings_schema_defaults import MAP_MARKER_COLOUR_SCHEME_DEFAULT

from tests.colour_scheme_test_utils import BUNDLED_COLOUR_SCHEME_INDICES
from explorer.presentation.design_map_preview import (
    MAP_SCOPE_ALL,
    DesignMapPreviewConfig,
    scheme_seed_config,
)


def _sample_cfg() -> DesignMapPreviewConfig:
    return scheme_seed_config(MAP_MARKER_COLOUR_SCHEME_DEFAULT, preview_scope=MAP_SCOPE_ALL)


def _family_locations_block(text: str) -> str:
    """Slice from ``family_locations=`` through the closing ``,`` of that nested constructor."""
    fam_start = text.index("family_locations=")
    scheme_close = text.rindex("\n)")
    return text[fam_start:scheme_close]


def test_format_map_marker_dict_contains_key_fields() -> None:
    cfg = _sample_cfg()
    text = format_map_marker_colour_scheme_dict_py(cfg, "Test name")
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
    assert "legend_highlight_band_index=" in text
    assert "radius_override_px=" not in text
    assert "colours_hex=" not in text
    assert "viewport=" not in text


def test_export_omits_hex_when_collections_match_global_defaults() -> None:
    """Sparse export: per-map fill/stroke hex lines are omitted when they match globals."""
    cfg = _sample_cfg()
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
    text = format_map_marker_colour_scheme_dict_py(flat, "G")
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


def test_export_omits_blank_hex_values_as_inherit_global() -> None:
    """Blank hex values are treated as unset/inherit and not exported as explicit overrides."""
    cfg = _sample_cfg()
    cfg2 = replace(
        cfg,
        lifer_map_lifer_fill_hex="",
        lifer_map_lifer_stroke_hex="",
        species_lifer_fill_hex="",
        species_lifer_stroke_hex="",
    )
    text = format_map_marker_colour_scheme_dict_py(cfg2, "Blank")
    ll_start = text.index("lifer_locations=")
    ll_end = text.index("family_locations=")
    ll_block = text[ll_start:ll_end]
    assert "        lifer_fill_hex=''," not in ll_block
    assert "        lifer_stroke_hex=''," not in ll_block
    sp_start = text.index("species_locations=")
    sp_end = text.index("species_map_background=")
    sp_block = text[sp_start:sp_end]
    assert "        lifer_fill_hex=''," not in sp_block
    assert "        lifer_stroke_hex=''," not in sp_block


def test_sparse_fill_opacity_omitted_when_all_collections_match_default() -> None:
    cfg = _sample_cfg()
    md = float(cfg.marker_default_fill_opacity)
    flat = replace(
        cfg,
        marker_fill_opacity_locations=md,
        marker_fill_opacity_species=md,
        marker_fill_opacity_lifer_map_lifer=md,
        marker_fill_opacity_lifer_map_subspecies=md,
        marker_fill_opacity_families=md,
    )
    text = format_map_marker_colour_scheme_dict_py(flat, "Flat")
    assert "fill_opacity_override=" not in text


def test_export_emits_radius_px_only_when_differs_from_default() -> None:
    cfg = _sample_cfg()
    d = int(cfg.marker_default_radius_px)
    cfg2 = replace(cfg, marker_radius_species=d + 3)
    text = format_map_marker_colour_scheme_dict_py(cfg2, "O")
    assert f"radius_px={d + 3}" in text
    assert text.count(f"radius_px={d + 3}") >= 1


def test_export_emits_species_fill_opacity_when_differs_from_default() -> None:
    cfg = _sample_cfg()
    md = float(cfg.marker_default_fill_opacity)
    cfg2 = replace(
        cfg,
        marker_fill_opacity_locations=md,
        marker_fill_opacity_species=0.42,
        marker_fill_opacity_lifer_map_lifer=md,
        marker_fill_opacity_lifer_map_subspecies=md,
        marker_fill_opacity_families=md,
    )
    text = format_map_marker_colour_scheme_dict_py(cfg2, "O")
    assert "fill_opacity=0.42" in text
    assert "species_locations=MapMarkerSpeciesLocationsStyle(" in text
    assert text.index("species_locations=") < text.index("fill_opacity=0.42")


def test_format_full_export_is_single_expanded_scheme_block() -> None:
    cfg = _sample_cfg()
    text = format_full_defaults_export(cfg, display_name="Export me")
    assert "MAP_MARKER_COLOUR_SCHEME_EXPORT = MapMarkerColourScheme(" in text
    assert "lifer_fill_hex=" in text
    assert "MAP_CIRCLE_MARKER_RADIUS_PX =" not in text
    assert "from explorer.core.map_marker_scheme_model import" not in text
    assert text.index("fill_hex=") < text.index("density_fill_hex=")


def test_export_omits_family_fill_opacity_when_matches_global() -> None:
    """Sparse export: family map omits fill_opacity when it matches global_defaults."""
    cfg = scheme_seed_config(MAP_MARKER_COLOUR_SCHEME_DEFAULT, preview_scope=MAP_SCOPE_ALL)
    text = format_map_marker_colour_scheme_dict_py(cfg, "S1")
    fam_block = _family_locations_block(text)
    assert "        fill_opacity=" not in fam_block


def test_export_omits_family_density_stroke_when_all_bands_match_global() -> None:
    """Sparse export: omit density_stroke_hex when every band equals global stroke."""
    cfg = scheme_seed_config(MAP_MARKER_COLOUR_SCHEME_DEFAULT, preview_scope=MAP_SCOPE_ALL)
    g_stroke = cfg.marker_default_stroke_hex
    flat = replace(
        cfg,
        family_stroke_hex=(g_stroke, g_stroke, g_stroke, g_stroke),
    )
    text = format_map_marker_colour_scheme_dict_py(flat, "AllStrokeGlobal")
    fam_block = _family_locations_block(text)
    assert "        density_stroke_hex=" not in fam_block


def test_export_scheme3_omits_redundant_fill_opacity_lines() -> None:
    """Sparse export: species/lifer inherit global opacity; family has no duplicate override."""
    from explorer.app.streamlit.defaults import active_map_marker_colour_scheme

    idx = BUNDLED_COLOUR_SCHEME_INDICES[-1]
    sch = active_map_marker_colour_scheme(idx)
    cfg = scheme_seed_config(idx, preview_scope=MAP_SCOPE_ALL)
    text = format_map_marker_colour_scheme_dict_py(cfg, sch.display_name)
    sp_start = text.index("species_locations=")
    sm_start = text.index("species_map_background=")
    species_block = text[sp_start:sm_start]
    assert "fill_opacity=" not in species_block
    ll_start = text.index("lifer_locations=")
    fam_start = text.index("family_locations=")
    lifer_block = text[ll_start:fam_start]
    assert "lifer_fill_opacity=" not in lifer_block
    assert "subspecies_fill_opacity=" not in lifer_block
    fam_block = _family_locations_block(text)
    assert "fill_opacity_override=" not in fam_block


def test_export_emits_marker_cluster_tier_icon_hex_when_configured() -> None:
    cfg = _sample_cfg()
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
    text = format_map_marker_colour_scheme_dict_py(cfg2, "Clusters")
    assert "tier_icon_hex=" in text
    assert "'#b91c1c'" in text
    assert "'#991b1b'" in text
    assert "'#eab308'" in text
    assert "'#a16207'" in text
    assert "'#16a34a'" in text
    assert "'#166534'" in text

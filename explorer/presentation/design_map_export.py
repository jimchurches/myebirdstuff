"""
Generate paste-ready Python for :mod:`explorer.app.streamlit.defaults` from a
:class:`~explorer.presentation.design_map_preview.DesignMapPreviewConfig`.

Output is a nested :class:`~explorer.core.map_marker_scheme_model.MapMarkerColourScheme` constructor
matching the structure in ``defaults.py``. Optional per-collection radius, fill opacity, and
fill/stroke hex fields are emitted only when they differ from :class:`MapMarkerGlobalDefaults` (or the
appropriate inherit-global rule); cluster tier colours and geometry follow the same rules as before.
"""

from __future__ import annotations

from explorer.app.streamlit.defaults import (
    MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT,
    MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT,
    MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT,
    MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT,
    MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT,
)
from explorer.core.map_marker_scheme_model import MapMarkerColourScheme
from explorer.presentation.design_map_preview import DesignMapPreviewConfig


def _fmt_float(x: float) -> str:
    s = f"{float(x):.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _fmt_hex_tuple(values: tuple[str, ...]) -> str:
    lines = ",\n            ".join(f"{v!r}" for v in values)
    return f"(\n            {lines},\n        )"


def _opacity_overrides_default(resolved: float, default: float) -> bool:
    return round(float(resolved), 4) != round(float(default), 4)


def _norm_hex7(h: str) -> str:
    s = (h or "").strip()
    if not s:
        return ""
    if not s.startswith("#"):
        s = f"#{s}"
    return s[:7].lower()


def _hex_differs(resolved: str, base: str) -> bool:
    """True when *resolved* is a different colour from *base* (``#RRGGBB``, case-insensitive)."""
    nr = _norm_hex7(resolved)
    if not nr:
        return False
    return nr != _norm_hex7(base)


def format_map_marker_colour_scheme_dict_py(
    cfg: DesignMapPreviewConfig,
    display_name: str,
    *,
    template: MapMarkerColourScheme,
    dict_name: str = "MAP_MARKER_COLOUR_SCHEME_EXPORT",
) -> str:
    """Return a ``MapMarkerColourScheme(...)`` assignment for pasting into ``defaults.py``."""
    vp = template.viewport
    md = int(cfg.marker_default_radius_px)
    md_fo = float(cfg.marker_default_fill_opacity)
    md_sw = int(cfg.marker_default_stroke_weight)
    g_fill = cfg.marker_default_fill_hex
    g_stroke = cfg.marker_default_stroke_hex
    t_al = template.all_locations
    t_smb = template.species_map_background
    t_sp = template.species_locations
    t_ll = template.lifer_locations
    t_fam = template.family_locations

    lines: list[str] = [
        f"{dict_name} = MapMarkerColourScheme(",
        f"    display_name={display_name!r},",
        "    global_defaults=MapMarkerGlobalDefaults(",
        f"        fill_hex={g_fill!r},",
        f"        stroke_hex={g_stroke!r},",
        f"        radius_px={md},",
        f"        fill_opacity={_fmt_float(cfg.marker_default_fill_opacity)},",
        f"        stroke_weight={int(cfg.marker_default_stroke_weight)},",
        "    ),",
    ]

    crl = int(cfg.marker_radius_locations)
    sw_v = int(cfg.stroke_weight_visit)
    fo_loc = float(cfg.marker_fill_opacity_locations)

    al_parts: list[str] = [
        "    all_locations=MapMarkerAllLocationsStyle(",
    ]
    if _hex_differs(cfg.default_fill_hex, g_fill):
        al_parts.append(f"        fill_hex={cfg.default_fill_hex!r},")
    if _hex_differs(cfg.default_stroke_hex, g_stroke):
        al_parts.append(f"        stroke_hex={cfg.default_stroke_hex!r},")
    if sw_v != md_sw:
        al_parts.append(f"        stroke_weight={sw_v},")
    if crl != md:
        al_parts.append(f"        radius_px={crl},")
    if _opacity_overrides_default(fo_loc, md_fo):
        if t_al.fill_opacity_override is not None:
            al_parts.append(f"        fill_opacity_override={_fmt_float(fo_loc)},")
        else:
            al_parts.append(f"        fill_opacity={_fmt_float(fo_loc)},")

    cl_parts: list[str] = []
    if cfg.marker_cluster_tier_icon_hex is not None:
        cl_parts.append(f"            tier_icon_hex={_fmt_hex_tuple(cfg.marker_cluster_tier_icon_hex)},")
        pairs: tuple[tuple[str, float, float], ...] = (
            ("inner_fill_opacity", cfg.marker_cluster_inner_fill_opacity, MAP_MARKER_CLUSTER_INNER_FILL_OPACITY_DEFAULT),
            ("halo_opacity", cfg.marker_cluster_halo_opacity, MAP_MARKER_CLUSTER_HALO_OPACITY_DEFAULT),
            ("border_opacity", cfg.marker_cluster_border_opacity, MAP_MARKER_CLUSTER_BORDER_OPACITY_DEFAULT),
        )
        for name, val, dflt in pairs:
            if round(float(val), 4) != round(float(dflt), 4):
                cl_parts.append(f"            {name}={_fmt_float(val)},")
        if int(cfg.marker_cluster_halo_spread_px) != int(MAP_MARKER_CLUSTER_HALO_SPREAD_PX_DEFAULT):
            cl_parts.append(f"            halo_spread_px={int(cfg.marker_cluster_halo_spread_px)},")
        if int(cfg.marker_cluster_border_width_px) != int(MAP_MARKER_CLUSTER_BORDER_WIDTH_PX_DEFAULT):
            cl_parts.append(f"            border_width_px={int(cfg.marker_cluster_border_width_px)},")
        cluster_block = ["        cluster=MapMarkerClusterStyle("] + cl_parts + ["        ),"]
    else:
        cluster_block = ["        cluster=MapMarkerClusterStyle(),"]

    al_parts.extend(cluster_block)
    al_parts.append("    ),")
    lines.extend(al_parts)

    fo_spec = float(cfg.marker_fill_opacity_species)
    sp_lines: list[str] = [
        "    species_locations=MapMarkerSpeciesLocationsStyle(",
    ]
    if _hex_differs(cfg.species_fill_hex, g_fill):
        sp_lines.append(f"        fill_hex={cfg.species_fill_hex!r},")
    if _hex_differs(cfg.species_stroke_hex, g_stroke):
        sp_lines.append(f"        stroke_hex={cfg.species_stroke_hex!r},")
    if _hex_differs(cfg.species_lifer_fill_hex, g_fill):
        sp_lines.append(f"        lifer_fill_hex={cfg.species_lifer_fill_hex!r},")
    if _hex_differs(cfg.species_lifer_stroke_hex, g_stroke):
        sp_lines.append(f"        lifer_stroke_hex={cfg.species_lifer_stroke_hex!r},")
    if _hex_differs(cfg.last_seen_fill_hex, g_fill):
        sp_lines.append(f"        last_seen_fill_hex={cfg.last_seen_fill_hex!r},")
    if _hex_differs(cfg.last_seen_stroke_hex, g_stroke):
        sp_lines.append(f"        last_seen_stroke_hex={cfg.last_seen_stroke_hex!r},")
    if _opacity_overrides_default(fo_spec, md_fo):
        if t_sp.fill_opacity_override is not None:
            sp_lines.append(f"        fill_opacity_override={_fmt_float(fo_spec)},")
        else:
            sp_lines.append(f"        fill_opacity={_fmt_float(fo_spec)},")
    if int(cfg.marker_radius_species) != md:
        sp_lines.append(f"        radius_px={int(cfg.marker_radius_species)},")
    if int(cfg.stroke_weight_species) != int(cfg.stroke_weight_visit):
        sp_lines.append(f"        stroke_weight_override={int(cfg.stroke_weight_species)},")
    sp_lines.append("    ),")
    lines.extend(sp_lines)

    rsmb = int(cfg.marker_radius_species_map_background)
    sw_smb = int(cfg.stroke_weight_species_map_background)
    fo_smb = float(cfg.marker_fill_opacity_species_map_background)
    smb_lines: list[str] = [
        "    species_map_background=MapMarkerSpeciesMapBackgroundStyle(",
    ]
    if _hex_differs(cfg.species_map_background_fill_hex, g_fill):
        smb_lines.append(f"        fill_hex={cfg.species_map_background_fill_hex!r},")
    if _hex_differs(cfg.species_map_background_stroke_hex, g_stroke):
        smb_lines.append(f"        stroke_hex={cfg.species_map_background_stroke_hex!r},")
    if sw_smb != md_sw:
        smb_lines.append(f"        stroke_weight={sw_smb},")
    if rsmb != md:
        smb_lines.append(f"        radius_px={rsmb},")
    if _opacity_overrides_default(fo_smb, md_fo):
        if t_smb.fill_opacity_override is not None:
            smb_lines.append(f"        fill_opacity_override={_fmt_float(fo_smb)},")
        else:
            smb_lines.append(f"        fill_opacity={_fmt_float(fo_smb)},")
    smb_lines.append("    ),")
    lines.extend(smb_lines)

    fo_lml = float(cfg.marker_fill_opacity_lifer_map_lifer)
    fo_lms = float(cfg.marker_fill_opacity_lifer_map_subspecies)
    ll_lines: list[str] = [
        "    lifer_locations=MapMarkerLiferLocationsStyle(",
    ]
    if _hex_differs(cfg.lifer_map_lifer_fill_hex, g_fill):
        ll_lines.append(f"        lifer_fill_hex={cfg.lifer_map_lifer_fill_hex!r},")
    if _hex_differs(cfg.lifer_map_lifer_stroke_hex, g_stroke):
        ll_lines.append(f"        lifer_stroke_hex={cfg.lifer_map_lifer_stroke_hex!r},")
    if _hex_differs(cfg.lifer_map_subspecies_fill_hex, g_fill):
        ll_lines.append(f"        subspecies_fill_hex={cfg.lifer_map_subspecies_fill_hex!r},")
    if _hex_differs(cfg.lifer_map_subspecies_stroke_hex, g_stroke):
        ll_lines.append(f"        subspecies_stroke_hex={cfg.lifer_map_subspecies_stroke_hex!r},")
    if _opacity_overrides_default(fo_lml, md_fo):
        if t_ll.lifer_fill_opacity_override is not None:
            ll_lines.append(f"        lifer_fill_opacity_override={_fmt_float(fo_lml)},")
        else:
            ll_lines.append(f"        lifer_fill_opacity={_fmt_float(fo_lml)},")
    if _opacity_overrides_default(fo_lms, md_fo):
        if t_ll.subspecies_fill_opacity_override is not None:
            ll_lines.append(f"        subspecies_fill_opacity_override={_fmt_float(fo_lms)},")
        else:
            ll_lines.append(f"        subspecies_fill_opacity={_fmt_float(fo_lms)},")
    if int(cfg.marker_radius_lifer_map_lifer) != md:
        ll_lines.append(
            f"        lifer_radius_px={int(cfg.marker_radius_lifer_map_lifer)},"
        )
    if int(cfg.marker_radius_lifer_map_subspecies) != md:
        ll_lines.append(
            f"        subspecies_radius_px={int(cfg.marker_radius_lifer_map_subspecies)},"
        )
    if int(cfg.stroke_weight_lifer) != int(cfg.stroke_weight_visit):
        ll_lines.append(f"        stroke_weight_override={int(cfg.stroke_weight_lifer)},")
    ll_lines.append("    ),")
    lines.extend(ll_lines)

    rf = int(cfg.marker_radius_families)
    lines.extend(
        [
            "    family_locations=MapMarkerFamilyLocationsStyle(",
            f"        radius_px={rf},",
            f"        fill_opacity={_fmt_float(cfg.marker_fill_opacity_families)},",
            f"        stroke_weight={int(cfg.stroke_weight_family)},",
            f"        highlight_stroke_hex={cfg.family_highlight_stroke_hex!r},",
            f"        highlight_stroke_weight={int(cfg.stroke_weight_family_highlight)},",
            f"        density_fill_hex={_fmt_hex_tuple(cfg.family_fill_hex)},",
            f"        density_stroke_hex={_fmt_hex_tuple(cfg.family_stroke_hex)},",
            f"        legend_highlight_band_index={int(cfg.legend_highlight_band_index)},",
        ]
    )
    if rf != md:
        lines.append(f"        radius_px_override={rf},")
    fo_fam = float(cfg.marker_fill_opacity_families)
    if t_fam.fill_opacity_override is not None:
        base_fam = float(t_fam.fill_opacity)
        ovr_fam = float(t_fam.fill_opacity_override)
        if _opacity_overrides_default(ovr_fam, base_fam) and _opacity_overrides_default(fo_fam, md_fo):
            lines.append(f"        fill_opacity_override={_fmt_float(fo_fam)},")
    lines.append("    ),")

    lines.extend(
        [
            "    viewport=MapMarkerViewportStyle(",
            f"        popup_max_width_px={int(vp.popup_max_width_px)},",
            f"        fit_bounds_padding_px={int(vp.fit_bounds_padding_px)},",
            f"        fit_bounds_max_zoom={int(vp.fit_bounds_max_zoom)},",
            f"        fit_bounds_max_zoom_highlight={int(vp.fit_bounds_max_zoom_highlight)},",
            "    ),",
            ")",
        ]
    )
    return "\n".join(lines)


def format_full_defaults_export(
    cfg: DesignMapPreviewConfig,
    *,
    display_name: str,
    template: MapMarkerColourScheme,
) -> str:
    """Single expanded scheme constructor plus import hint for pasting into ``defaults.py``."""
    header = (
        "# --- Copy into explorer/app/streamlit/defaults.py (merge by hand) ---\n"
        "# Rename MAP_MARKER_COLOUR_SCHEME_EXPORT, then register the index in\n"
        "# active_map_marker_colour_scheme() if you add a new slot.\n"
        "# Requires: MapMarkerColourScheme and nested types from\n"
        "# explorer.core.map_marker_scheme_model (see existing MAP_MARKER_COLOUR_SCHEME_* blocks).\n"
    )
    imports = (
        "from explorer.core.map_marker_scheme_model import (\n"
        "    MapMarkerAllLocationsStyle,\n"
        "    MapMarkerClusterStyle,\n"
        "    MapMarkerColourScheme,\n"
        "    MapMarkerFamilyLocationsStyle,\n"
        "    MapMarkerGlobalDefaults,\n"
        "    MapMarkerLiferLocationsStyle,\n"
        "    MapMarkerSpeciesLocationsStyle,\n"
        "    MapMarkerSpeciesMapBackgroundStyle,\n"
        "    MapMarkerViewportStyle,\n"
        ")\n"
    )
    body = format_map_marker_colour_scheme_dict_py(
        cfg, display_name, template=template, dict_name="MAP_MARKER_COLOUR_SCHEME_EXPORT"
    )
    return "\n".join([header, "", imports, "", body, ""])

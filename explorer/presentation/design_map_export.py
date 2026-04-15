"""
Generate paste-ready Python for :mod:`explorer.app.streamlit.defaults` from a
:class:`~explorer.presentation.design_map_preview.DesignMapPreviewConfig`.

Output is a nested :class:`~explorer.core.map_marker_scheme_model.MapMarkerColourScheme` constructor
matching the structure in ``defaults.py``. Optional per-collection radius / fill-opacity fields are
emitted only when they differ from the global defaults; cluster tier colours and geometry follow the
same rules as the previous flat dict exporter.
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


def format_map_marker_colour_scheme_dict_py(
    cfg: DesignMapPreviewConfig,
    display_name: str,
    *,
    template: MapMarkerColourScheme,
    dict_name: str = "MAP_MARKER_COLOUR_SCHEME_EXPORT",
) -> str:
    """Return a ``MapMarkerColourScheme(...)`` assignment for pasting into ``defaults.py``."""
    vp = template.viewport
    md = int(cfg.marker_default_circle_radius_px)
    md_fo = float(cfg.marker_default_circle_fill_opacity)
    md_sw = int(cfg.marker_default_base_stroke_weight)
    t_al = template.all_locations

    lines: list[str] = [
        f"{dict_name} = MapMarkerColourScheme(",
        f"    display_name={display_name!r},",
        "    global_defaults=MapMarkerGlobalDefaults(",
        f"        fill_hex={cfg.marker_default_fill_hex!r},",
        f"        edge_hex={cfg.marker_default_edge_hex!r},",
        f"        circle_radius_px={md},",
        f"        circle_fill_opacity={_fmt_float(cfg.marker_default_circle_fill_opacity)},",
        f"        base_stroke_weight={int(cfg.marker_default_base_stroke_weight)},",
        "    ),",
    ]

    crl = int(cfg.marker_circle_radius_locations)
    sw_v = int(cfg.stroke_weight_visit)
    fo_loc = float(cfg.marker_circle_fill_opacity_locations)

    al_parts: list[str] = [
        "    all_locations=MapMarkerAllLocationsStyle(",
        f"        fill_hex={cfg.default_fill!r},",
        f"        edge_hex={cfg.default_edge!r},",
    ]
    if sw_v != md_sw:
        al_parts.append(f"        stroke_weight={sw_v},")
    if crl != md:
        al_parts.append(f"        radius_override_px={crl},")
    if _opacity_overrides_default(fo_loc, md_fo):
        if t_al.fill_opacity_override is not None:
            al_parts.append(f"        fill_opacity_override={_fmt_float(fo_loc)},")
        else:
            al_parts.append(f"        fill_opacity={_fmt_float(fo_loc)},")

    cl_parts: list[str] = []
    if cfg.marker_cluster_colours_hex is not None:
        cl_parts.append(f"            colours_hex={_fmt_hex_tuple(cfg.marker_cluster_colours_hex)},")
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

    lines.extend(
        [
            "    species_locations=MapMarkerSpeciesLocationsStyle(",
            f"        fill_hex={cfg.species_fill!r},",
            f"        edge_hex={cfg.species_edge!r},",
            f"        map_lifer_fill_hex={cfg.species_map_lifer_fill!r},",
            f"        map_lifer_edge_hex={cfg.species_map_lifer_edge!r},",
            f"        last_seen_fill_hex={cfg.last_seen_fill!r},",
            f"        last_seen_edge_hex={cfg.last_seen_edge!r},",
            f"        emphasis_fill_opacity={_fmt_float(cfg.marker_circle_fill_opacity_species)},",
        ]
    )
    if int(cfg.marker_circle_radius_species) != md:
        lines.append(f"        radius_override_px={int(cfg.marker_circle_radius_species)},")
    if int(cfg.stroke_weight_species) != int(cfg.stroke_weight_visit):
        lines.append(f"        stroke_weight_override={int(cfg.stroke_weight_species)},")
    if _opacity_overrides_default(cfg.marker_circle_fill_opacity_species, md_fo):
        lines.append(f"        fill_opacity_override={_fmt_float(cfg.marker_circle_fill_opacity_species)},")
    lines.append("    ),")

    lines.extend(
        [
            "    lifer_locations=MapMarkerLiferLocationsStyle(",
            f"        lifer_fill_hex={cfg.lifer_map_lifer_fill!r},",
            f"        lifer_edge_hex={cfg.lifer_map_lifer_edge!r},",
            f"        subspecies_fill_hex={cfg.lifer_map_subspecies_fill!r},",
            f"        subspecies_edge_hex={cfg.lifer_map_subspecies_edge!r},",
            f"        lifer_fill_opacity={_fmt_float(cfg.marker_circle_fill_opacity_lifer_map_lifer)},",
            f"        subspecies_fill_opacity={_fmt_float(cfg.marker_circle_fill_opacity_lifer_map_subspecies)},",
        ]
    )
    if int(cfg.marker_circle_radius_lifer_map_lifer) != md:
        lines.append(
            f"        lifer_radius_override_px={int(cfg.marker_circle_radius_lifer_map_lifer)},"
        )
    if int(cfg.marker_circle_radius_lifer_map_subspecies) != md:
        lines.append(
            f"        subspecies_radius_override_px={int(cfg.marker_circle_radius_lifer_map_subspecies)},"
        )
    if int(cfg.stroke_weight_lifer) != int(cfg.stroke_weight_visit):
        lines.append(f"        stroke_weight_override={int(cfg.stroke_weight_lifer)},")
    if _opacity_overrides_default(cfg.marker_circle_fill_opacity_lifer_map_lifer, md_fo):
        lines.append(
            f"        lifer_fill_opacity_override={_fmt_float(cfg.marker_circle_fill_opacity_lifer_map_lifer)},"
        )
    if _opacity_overrides_default(cfg.marker_circle_fill_opacity_lifer_map_subspecies, md_fo):
        lines.append(
            f"        subspecies_fill_opacity_override={_fmt_float(cfg.marker_circle_fill_opacity_lifer_map_subspecies)},"
        )
    lines.append("    ),")

    lines.extend(
        [
            "    family_locations=MapMarkerFamilyLocationsStyle(",
            f"        pin_radius_px={int(cfg.marker_circle_radius_families)},",
            f"        pin_fill_opacity={_fmt_float(cfg.marker_circle_fill_opacity_families)},",
            f"        base_stroke_weight={int(cfg.stroke_weight_family)},",
            f"        highlight_stroke_hex={cfg.family_highlight_stroke_hex!r},",
            f"        highlight_stroke_weight={int(cfg.stroke_weight_family_highlight)},",
            f"        density_fill_hex={_fmt_hex_tuple(cfg.family_fill_hex)},",
            f"        density_stroke_hex={_fmt_hex_tuple(cfg.family_stroke_hex)},",
            f"        legend_highlight_band_index={int(cfg.legend_highlight_band_index)},",
        ]
    )
    if int(cfg.marker_circle_radius_families) != md:
        lines.append(f"        radius_override_px={int(cfg.marker_circle_radius_families)},")
    if _opacity_overrides_default(cfg.marker_circle_fill_opacity_families, md_fo):
        lines.append(f"        fill_opacity_override={_fmt_float(cfg.marker_circle_fill_opacity_families)},")
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
        "    MapMarkerViewportStyle,\n"
        ")\n"
    )
    body = format_map_marker_colour_scheme_dict_py(
        cfg, display_name, template=template, dict_name="MAP_MARKER_COLOUR_SCHEME_EXPORT"
    )
    return "\n".join([header, "", imports, "", body, ""])

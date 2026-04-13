"""
Generate paste-ready Python snippets for :mod:`explorer.app.streamlit.defaults` from a
:class:`~explorer.presentation.design_map_preview.DesignMapPreviewConfig`.

Output is a single ``dict`` aligned with field order on
:class:`~explorer.app.streamlit.defaults.MapMarkerColourScheme` (refs #147).
"""

from __future__ import annotations

from explorer.app.streamlit.defaults import MapMarkerColourScheme
from explorer.presentation.design_map_preview import DesignMapPreviewConfig


def _fmt_float(x: float) -> str:
    s = f"{float(x):.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _fmt_hex_tuple(values: tuple[str, ...]) -> str:
    lines = ",\n        ".join(f"{v!r}" for v in values)
    return f"(\n        {lines},\n    )"


def format_map_marker_colour_scheme_dict_py(
    cfg: DesignMapPreviewConfig,
    display_name: str,
    *,
    template: MapMarkerColourScheme,
    dict_name: str = "_MAP_MARKER_COLOUR_SCHEME_EXPORT_VALUES",
) -> str:
    """Return one ``dict(...)`` matching ``MapMarkerColourScheme`` (ordered keys for paste readability)."""
    lines = [
        f"{dict_name} = dict(",
        f"    display_name={display_name!r},",
        f"    marker_default_fill_hex={cfg.marker_default_fill_hex!r},",
        f"    marker_default_edge_hex={cfg.marker_default_edge_hex!r},",
        f"    marker_default_circle_radius_px={int(cfg.marker_default_circle_radius_px)},",
        f"    marker_default_circle_fill_opacity={_fmt_float(cfg.marker_default_circle_fill_opacity)},",
        f"    marker_default_base_stroke_weight={int(cfg.marker_default_base_stroke_weight)},",
        f"    marker_location_visit_fill_hex={cfg.default_fill!r},",
        f"    marker_location_visit_edge_hex={cfg.default_edge!r},",
        f"    marker_species_fill_hex={cfg.species_fill!r},",
        f"    marker_species_edge_hex={cfg.species_edge!r},",
        f"    marker_lifer_fill_hex={cfg.lifer_fill!r},",
        f"    marker_lifer_edge_hex={cfg.lifer_edge!r},",
        f"    marker_last_seen_fill_hex={cfg.last_seen_fill!r},",
        f"    marker_last_seen_edge_hex={cfg.last_seen_edge!r},",
        f"    circle_marker_radius_px={int(cfg.circle_radius_px)},",
        f"    circle_marker_fill_opacity={_fmt_float(cfg.family_fill_opacity)},",
        f"    base_stroke_weight={int(cfg.stroke_weight_family)},",
        f"    highlight_stroke_hex={cfg.family_highlight_stroke_hex!r},",
        f"    highlight_stroke_weight={int(cfg.stroke_weight_family_highlight)},",
        f"    density_fill_hex={_fmt_hex_tuple(cfg.family_fill_hex)},",
        f"    density_stroke_hex={_fmt_hex_tuple(cfg.family_stroke_hex)},",
        f"    visit_circle_marker_radius_px={int(template.visit_circle_marker_radius_px)},",
        f"    visit_stroke_weight={int(cfg.stroke_weight_visit)},",
        f"    visit_fill_opacity_all_locations={_fmt_float(cfg.fill_opacity_all_locations)},",
        f"    visit_fill_opacity_emphasis={_fmt_float(cfg.fill_opacity_emphasis)},",
        f"    popup_max_width_px={int(template.popup_max_width_px)},",
        f"    fit_bounds_padding_px={int(template.fit_bounds_padding_px)},",
        f"    fit_bounds_max_zoom={int(template.fit_bounds_max_zoom)},",
        f"    fit_bounds_max_zoom_highlight={int(template.fit_bounds_max_zoom_highlight)},",
        f"    legend_highlight_swatch_fill_index={int(cfg.legend_highlight_swatch_fill_index)},",
        ")",
    ]
    return "\n".join(lines)


def format_full_defaults_export(
    cfg: DesignMapPreviewConfig,
    *,
    display_name: str,
    template: MapMarkerColourScheme,
) -> str:
    """Single expanded scheme dict plus ``MapMarkerColourScheme(...)`` constructor line."""
    header = (
        "# --- Copy into explorer/app/streamlit/defaults.py (merge by hand) ---\n"
        "# Rename _MAP_MARKER_COLOUR_SCHEME_EXPORT_VALUES / MAP_MARKER_COLOUR_SCHEME_EXPORT, then\n"
        "# register the index in active_map_marker_colour_scheme() if you add a new slot.\n"
        "# ``circle_marker_*`` / ``density_*`` / ``highlight_*`` / ``base_stroke_weight`` are consumed\n"
        "# by family-map folium today; keep those names until #147 migrates callers.\n"
    )
    mm = format_map_marker_colour_scheme_dict_py(cfg, display_name, template=template)
    inst = (
        "\nMAP_MARKER_COLOUR_SCHEME_EXPORT = MapMarkerColourScheme(**_MAP_MARKER_COLOUR_SCHEME_EXPORT_VALUES)\n"
    )
    return "\n".join([header, "", mm, inst, ""])

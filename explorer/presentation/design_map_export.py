"""
Generate paste-ready Python snippets for :mod:`explorer.app.streamlit.defaults` from a
:class:`~explorer.presentation.design_map_preview.DesignMapPreviewConfig`.

Output is a single ``dict`` aligned with field order on
:class:`~explorer.app.streamlit.defaults.MapMarkerColourScheme` (refs #147).

Optional per-collection circle radius and fill-opacity keys are emitted only when they differ from the
global defaults (``marker_default_circle_radius_px`` / ``marker_default_circle_fill_opacity``).
``marker_cluster_tier_fill_hex`` is emitted only when all three tier colours are set (otherwise Folium defaults).
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


def _opacity_overrides_default(resolved: float, default: float) -> bool:
    return round(float(resolved), 4) != round(float(default), 4)


def _append_sparse_radius_overrides(lines: list[str], cfg: DesignMapPreviewConfig) -> None:
    """Emit ``marker_circle_radius_px_*`` only when different from ``marker_default_circle_radius_px``."""
    d = int(cfg.marker_default_circle_radius_px)
    pairs: tuple[tuple[str, int], ...] = (
        ("marker_circle_radius_px_locations", cfg.marker_circle_radius_locations),
        ("marker_circle_radius_px_species", cfg.marker_circle_radius_species),
        ("marker_circle_radius_px_lifers", cfg.marker_circle_radius_lifers),
        ("marker_circle_radius_px_families", cfg.marker_circle_radius_families),
    )
    for name, val in pairs:
        if int(val) != d:
            lines.append(f"    {name}={int(val)},")


def _append_sparse_cluster_tier_fill_hex(lines: list[str], cfg: DesignMapPreviewConfig) -> None:
    """Emit ``marker_cluster_tier_fill_hex`` only when set (overrides Folium / plugin defaults)."""
    t = cfg.marker_cluster_tier_fill_hex
    if t is None:
        return
    lines.append(f"    marker_cluster_tier_fill_hex={_fmt_hex_tuple(t)},")


def _append_sparse_fill_opacity_overrides(lines: list[str], cfg: DesignMapPreviewConfig) -> None:
    """Emit ``marker_circle_fill_opacity_*`` only when different from ``marker_default_circle_fill_opacity``."""
    d = float(cfg.marker_default_circle_fill_opacity)
    pairs: tuple[tuple[str, float], ...] = (
        ("marker_circle_fill_opacity_locations", cfg.marker_circle_fill_opacity_locations),
        ("marker_circle_fill_opacity_species", cfg.marker_circle_fill_opacity_species),
        ("marker_circle_fill_opacity_lifers", cfg.marker_circle_fill_opacity_lifers),
        ("marker_circle_fill_opacity_families", cfg.marker_circle_fill_opacity_families),
    )
    for name, val in pairs:
        if _opacity_overrides_default(val, d):
            lines.append(f"    {name}={_fmt_float(val)},")


def format_map_marker_colour_scheme_dict_py(
    cfg: DesignMapPreviewConfig,
    display_name: str,
    *,
    template: MapMarkerColourScheme,
    dict_name: str = "_MAP_MARKER_COLOUR_SCHEME_EXPORT_VALUES",
) -> str:
    """Return one ``dict(...)`` matching ``MapMarkerColourScheme`` (ordered keys for paste readability)."""
    lines: list[str] = [
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
        f"    circle_marker_radius_px={int(cfg.marker_circle_radius_families)},",
        f"    circle_marker_fill_opacity={_fmt_float(cfg.marker_circle_fill_opacity_families)},",
        f"    base_stroke_weight={int(cfg.stroke_weight_family)},",
        f"    highlight_stroke_hex={cfg.family_highlight_stroke_hex!r},",
        f"    highlight_stroke_weight={int(cfg.stroke_weight_family_highlight)},",
        f"    density_fill_hex={_fmt_hex_tuple(cfg.family_fill_hex)},",
        f"    density_stroke_hex={_fmt_hex_tuple(cfg.family_stroke_hex)},",
        f"    visit_circle_marker_radius_px={int(cfg.marker_circle_radius_locations)},",
        f"    visit_stroke_weight={int(cfg.stroke_weight_visit)},",
        f"    visit_fill_opacity_all_locations={_fmt_float(cfg.marker_circle_fill_opacity_locations)},",
        f"    visit_fill_opacity_emphasis={_fmt_float(cfg.marker_circle_fill_opacity_species)},",
        f"    visit_fill_opacity_lifers={_fmt_float(cfg.marker_circle_fill_opacity_lifers)},",
        f"    popup_max_width_px={int(template.popup_max_width_px)},",
        f"    fit_bounds_padding_px={int(template.fit_bounds_padding_px)},",
        f"    fit_bounds_max_zoom={int(template.fit_bounds_max_zoom)},",
        f"    fit_bounds_max_zoom_highlight={int(template.fit_bounds_max_zoom_highlight)},",
        f"    legend_highlight_swatch_fill_index={int(cfg.legend_highlight_swatch_fill_index)},",
    ]
    _append_sparse_radius_overrides(lines, cfg)
    _append_sparse_fill_opacity_overrides(lines, cfg)
    _append_sparse_cluster_tier_fill_hex(lines, cfg)
    lines.append(")")
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
        "# Optional ``marker_circle_radius_px_*`` / ``marker_circle_fill_opacity_*`` keys appear only\n"
        "# when they differ from ``marker_default_circle_radius_px`` / ``marker_default_circle_fill_opacity``.\n"
        "# Optional ``marker_cluster_tier_fill_hex`` appears only when all three tier colours are set.\n"
    )
    mm = format_map_marker_colour_scheme_dict_py(cfg, display_name, template=template)
    inst = (
        "\nMAP_MARKER_COLOUR_SCHEME_EXPORT = MapMarkerColourScheme(**_MAP_MARKER_COLOUR_SCHEME_EXPORT_VALUES)\n"
    )
    return "\n".join([header, "", mm, inst, ""])

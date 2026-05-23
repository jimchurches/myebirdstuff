"""Family map banner, legend, and pin styling for the Leaflet component."""

from __future__ import annotations

import html as html_module

from explorer.app.streamlit.defaults import (
    MAP_CIRCLE_MARKER_STROKE_WEIGHT,
    MapMarkerColourScheme,
    active_map_marker_colour_scheme,
)
from explorer.core.family_map_compute import (
    DENSITY_BAND_LABELS,
    FamilyLocationPin,
    FamilyMapBannerMetrics,
)
from explorer.core.map_marker_colour_resolve import (
    _global_defaults,
    family_map_resolved_highlight_pin_stroke_hex,
    resolve_family_band_colours,
    resolve_family_highlight_stroke_hex,
)
from explorer.presentation.map_renderer import (
    build_legend_html,
    checklist_individual_stats_banner_fragment,
)

# Match species-map banner placement (``map_renderer``).
_FAMILY_MAP_BANNER_POSITION = "position:fixed;top:10px;right:10px;z-index:1000;"


def family_map_marker_style(
    pin: FamilyLocationPin,
    *,
    style: MapMarkerColourScheme | None = None,
) -> tuple[str, str, int]:
    """Return ``(fill_hex, stroke_hex, stroke_weight)`` for a composition pin."""
    s = style or active_map_marker_colour_scheme()
    fam = s.family_locations
    g = _global_defaults(s)
    md_sw = max(1, int(getattr(g, "stroke_weight", MAP_CIRCLE_MARKER_STROKE_WEIGHT)))
    sw_band = md_sw if fam.stroke_weight is None else max(1, int(fam.stroke_weight))
    sw_hl = md_sw if fam.highlight_stroke_weight is None else max(1, int(fam.highlight_stroke_weight))
    fills = fam.density_fill_hex
    n = len(fills)
    idx = max(0, min(pin.density_band_index, n - 1)) if n else 0
    fill_res, edge_res = resolve_family_band_colours(s, idx)
    if pin.highlight_match:
        return (
            fill_res,
            family_map_resolved_highlight_pin_stroke_hex(s, idx),
            sw_hl,
        )
    return fill_res, edge_res, sw_band


def _family_map_banner_recorded_clause(metrics: FamilyMapBannerMetrics) -> str:
    u = int(metrics.species_recorded_user)
    t = int(metrics.total_species_taxonomy)
    if t > 0:
        pct = round(100.0 * u / t)
        return f"{u} recorded ({pct}%)"
    return f"{u} recorded"


def build_family_map_banner_overlay_html(
    metrics: FamilyMapBannerMetrics,
    *,
    selected_species_n_checklists: int | None = None,
    selected_species_n_individuals: int | None = None,
    selected_species_display_name: str | None = None,
    selected_species_url: str | None = None,
) -> str:
    """Return HTML for the fixed top-right family map banner."""
    title = html_module.escape(metrics.family_name, quote=False)
    stats = html_module.escape(
        f"{metrics.total_species_taxonomy} in taxonomy · "
        f"{_family_map_banner_recorded_clause(metrics)} · "
        f"{metrics.locations_with_records} locations",
        quote=False,
    )
    extra = ""
    if selected_species_n_checklists is not None and selected_species_n_individuals is not None:
        frag = checklist_individual_stats_banner_fragment(
            selected_species_n_checklists,
            selected_species_n_individuals,
        )
        dn = (selected_species_display_name or "").strip()
        if dn:
            dn_esc = html_module.escape(dn, quote=False)
            url = (selected_species_url or "").strip()
            if url:
                href = html_module.escape(url, quote=True)
                name_html = (
                    f'<a href="{href}" target="_blank" rel="noopener noreferrer">{dn_esc}</a>'
                )
            else:
                name_html = dn_esc
            inner = f"{name_html}: {frag}"
        else:
            inner = frag
        extra = f'<span class="pebird-map-banner__family-selected-summary">{inner}</span>'
    return (
        f'<div class="pebird-map-banner" style="{_FAMILY_MAP_BANNER_POSITION}">'
        f'<span class="pebird-map-banner__title">{title}</span>'
        f'<div class="pebird-map-banner__stats">{stats}</div>'
        f"{extra}"
        f"</div>"
    )


def build_family_map_legend_overlay_html(*, include_highlight: bool) -> str:
    """Backward-compatible wrapper (prefer the pins-based helper)."""
    if include_highlight:
        return build_family_map_legend_overlay_html_for_pins((), highlight_label="selected species")
    return build_family_map_legend_overlay_html_for_pins((), highlight_label=None)


def build_family_map_legend_overlay_html_for_pins(
    pins: tuple[FamilyLocationPin, ...] | list[FamilyLocationPin],
    *,
    highlight_label: str | None,
    highlight_species_url: str | None = None,
    style: MapMarkerColourScheme | None = None,
) -> str:
    """Build the bottom-left legend for the family map."""
    s = style or active_map_marker_colour_scheme()
    fam = s.family_locations
    pin_list = list(pins)
    bands_present = sorted({int(p.density_band_index) for p in pin_list}) if pin_list else []
    items: list[tuple[str, str, str]] = []
    for i in bands_present:
        if 0 <= i < len(DENSITY_BAND_LABELS):
            lab = DENSITY_BAND_LABELS[i]
            fill_r, edge_r = resolve_family_band_colours(s, i)
            items.append((edge_r, fill_r, f"{lab} species at location"))
    hl = (highlight_label or "").strip()
    if hl:
        sw_i = max(
            0,
            min(fam.legend_highlight_band_index, len(fam.density_fill_hex) - 1),
        )
        url = (highlight_species_url or "").strip()
        if url:
            href = html_module.escape(url, quote=True)
            esc_name = html_module.escape(hl, quote=False)
            hl_legend = (
                f'Highlight: <a href="{href}" target="_blank" rel="noopener noreferrer">{esc_name}</a>'
            )
        else:
            hl_legend = f"Highlight: {html_module.escape(hl, quote=False)}"
        fill_hl, _ = resolve_family_band_colours(s, sw_i)
        items.append((resolve_family_highlight_stroke_hex(s), fill_hl, hl_legend))
    return build_legend_html(items) if items else ""

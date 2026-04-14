"""Folium rendering for the taxonomy-family (“Family locations”) map.

Kept separate from :mod:`explorer.core.map_controller` so family colours, banners, and
legends can change without touching the all-species overlay pipeline.

Band and legend hex values are resolved via :mod:`explorer.core.map_marker_colour_resolve`
(the same module used when previewing schemes in ``explorer/app/streamlit/design_map_app.py``).
"""

from __future__ import annotations

import html as html_module
from typing import Callable

import folium
from branca.element import Element

from explorer.app.streamlit.defaults import (
    MAP_HEIGHT_PX_DEFAULT,
    MapMarkerColourScheme,
    active_map_marker_colour_scheme,
    family_map_resolved_circle_radius_px,
    family_map_resolved_fill_opacity,
)
from explorer.core.family_map_compute import (
    DENSITY_BAND_LABELS,
    FamilyLocationPin,
    FamilyMapBannerMetrics,
    format_family_location_popup_html,
)
from explorer.core.map_marker_colour_resolve import (
    normalize_marker_hex,
    resolve_family_band_colours,
)
from explorer.presentation.map_renderer import (
    build_legend_html,
    create_map,
    map_overlay_theme_stylesheet,
    map_popup_width_fix_script,
)

# Match species-map banner placement (``map_renderer``).
_FAMILY_MAP_BANNER_POSITION = "position:fixed;top:10px;right:10px;z-index:1000;"

def family_map_marker_style(
    pin: FamilyLocationPin,
    *,
    style: MapMarkerColourScheme | None = None,
) -> tuple[str, str, int]:
    """Return ``(fill_hex, stroke_hex, stroke_weight)`` for a composition pin.

    Band and highlight colours use :func:`~explorer.core.map_marker_colour_resolve.resolve_family_band_colours`
    and :func:`~explorer.core.map_marker_colour_resolve.normalize_marker_hex`, i.e. the same per-channel
    chain as other scheme-driven maps (band-specific hex, then ``marker_default_*``, then module defaults,
    then catch-all — see :mod:`explorer.core.map_marker_colour_resolve`).
    """
    s = style or active_map_marker_colour_scheme()
    fills = s.density_fill_hex
    n = len(fills)
    idx = max(0, min(pin.density_band_index, n - 1)) if n else 0
    fill_res, edge_res = resolve_family_band_colours(s, idx)
    if pin.highlight_match:
        return (
            fill_res,
            normalize_marker_hex(s.highlight_stroke_hex, channel="edge"),
            s.highlight_stroke_weight,
        )
    return fill_res, edge_res, s.base_stroke_weight


def _default_au_center() -> tuple[float, float]:
    return -25.0, 134.0


def _family_map_banner_recorded_clause(metrics: FamilyMapBannerMetrics) -> str:
    u = int(metrics.species_recorded_user)
    t = int(metrics.total_species_taxonomy)
    if t > 0:
        pct = round(100.0 * u / t)
        return f"{u} recorded ({pct}%)"
    return f"{u} recorded"


def build_family_map_banner_overlay_html(metrics: FamilyMapBannerMetrics) -> str:
    """Return HTML for the fixed top-right banner: family title plus taxonomy / recording summary.

    Reuses the shared ``pebird-map-banner`` layout used on other maps.
    """
    title = html_module.escape(metrics.family_name, quote=False)
    stats = html_module.escape(
        f"{metrics.total_species_taxonomy} in taxonomy · "
        f"{_family_map_banner_recorded_clause(metrics)} · "
        f"{metrics.locations_with_records} locations",
        quote=False,
    )
    return (
        f'<div class="pebird-map-banner" style="{_FAMILY_MAP_BANNER_POSITION}">'
        f'<span class="pebird-map-banner__title">{title}</span>'
        f'<div class="pebird-map-banner__stats">{stats}</div>'
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
    """Build the bottom-left legend: one row per richness band that appears on the map, plus highlight.

    Empty bands are omitted so sparse regions get a compact legend. When *highlight_species_url*
    is set together with *highlight_label*, the species name is linked to its eBird species page.
    Swatch colours use the same resolution as :func:`family_map_marker_style`.
    """
    s = style or active_map_marker_colour_scheme()
    pin_list = list(pins)
    bands_present = sorted({int(p.density_band_index) for p in pin_list}) if pin_list else []
    items: list[tuple[str, str, str]] = []
    for i in bands_present:
        if 0 <= i < len(DENSITY_BAND_LABELS):
            lab = DENSITY_BAND_LABELS[i]
            fill_r, edge_r = resolve_family_band_colours(s, i)
            items.append(
                (
                    edge_r,
                    fill_r,
                    f"{lab} species at location",
                )
            )
    hl = (highlight_label or "").strip()
    if hl:
        sw_i = max(
            0,
            min(
                s.legend_highlight_swatch_fill_index,
                len(s.density_fill_hex) - 1,
            ),
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
        items.append(
            (
                normalize_marker_hex(s.highlight_stroke_hex, channel="edge"),
                fill_hl,
                hl_legend,
            )
        )
    return build_legend_html(items) if items else ""


def build_family_composition_folium_map(
    pins: tuple[FamilyLocationPin, ...] | list[FamilyLocationPin],
    *,
    banner_html: str = "",
    legend_html: str = "",
    map_style: str = "default",
    height_px: int = MAP_HEIGHT_PX_DEFAULT,
    location_page_url_fn: Callable[[str], str | None] | None = None,
    species_url_fn: Callable[[str], str | None] | None = None,
    fit_bounds_highlight_only: bool = False,
    colour_scheme_index: int | None = None,
    default_center: tuple[float, float] | None = None,
) -> folium.Map:
    """Draw the family-composition map: markers, injected banner/legend HTML, and initial ``fit_bounds``.

    *default_center* — when there are no pins, centre the blank map here (e.g. mean of the user’s
    locations). If omitted, a broad regional default is used.

    *location_page_url_fn* maps ``Location ID`` → hotspot URL; *species_url_fn* maps common name
    (as shown in the export) to species page URL.

    When *fit_bounds_highlight_only* is true (highlight species selected), the initial ``fit_bounds``
    uses only pins where ``highlight_match`` is true, with the same padding as the full-family case
    and ``fit_bounds_max_zoom_highlight`` (closer zoom allowed than ``fit_bounds_max_zoom``).
    If none match, falls back to all pins.

    *colour_scheme_index* ``1``, ``2``, or ``3`` selects the sidebar palette; ``None`` uses
    :func:`~explorer.app.streamlit.defaults.active_map_marker_colour_scheme` defaults.
    """
    pin_list = list(pins)
    if pin_list:
        if fit_bounds_highlight_only:
            hl_only = [p for p in pin_list if p.highlight_match]
            _cent_src = hl_only if hl_only else pin_list
        else:
            _cent_src = pin_list
        center = (
            sum(p.latitude for p in _cent_src) / len(_cent_src),
            sum(p.longitude for p in _cent_src) / len(_cent_src),
        )
    else:
        center = default_center if default_center is not None else _default_au_center()

    m = create_map(center, map_style, height_px=height_px)
    m.get_root().html.add_child(Element(map_overlay_theme_stylesheet()))
    m.get_root().html.add_child(Element(map_popup_width_fix_script()))

    if banner_html and str(banner_html).strip():
        m.get_root().html.add_child(Element(str(banner_html).strip()))

    if legend_html and str(legend_html).strip():
        m.get_root().html.add_child(Element(str(legend_html).strip()))

    loc_fn = location_page_url_fn or (lambda _lid: None)
    sp_fn = species_url_fn or (lambda _c: None)
    style = active_map_marker_colour_scheme(colour_scheme_index)

    # Draw non-highlighted first, then highlighted so highlights sit on top.
    normal = [p for p in pin_list if not p.highlight_match]
    highlighted = [p for p in pin_list if p.highlight_match]
    for pin in normal + highlighted:
        fill, stroke, sw = family_map_marker_style(pin, style=style)
        url_map: dict[str, str] = {}
        for line in pin.common_name_lines:
            u = sp_fn(line)
            if u:
                url_map[line] = u
        inner = format_family_location_popup_html(
            pin,
            location_page_url=loc_fn(pin.location_id),
            species_url_by_common=url_map or None,
        )
        popup_body = f'<div class="pebird-map-popup">{inner}</div>'
        folium.CircleMarker(
            location=(pin.latitude, pin.longitude),
            radius=family_map_resolved_circle_radius_px(style),
            color=stroke,
            weight=sw,
            fill=True,
            fill_color=fill,
            fill_opacity=family_map_resolved_fill_opacity(style),
            popup=folium.Popup(popup_body, max_width=style.popup_max_width_px),
        ).add_to(m)

    # Family-map-only initial viewport:
    # - fit relevant pins with edge padding (all family pins, or highlight-only when requested)
    # - cap how far fitBounds may zoom in (family-wide vs species-highlight use different caps)
    if pin_list:
        if fit_bounds_highlight_only:
            hl_pins = [p for p in pin_list if p.highlight_match]
            _bounds_src = hl_pins or pin_list
            _species_framed = bool(hl_pins)
        else:
            _bounds_src = pin_list
            _species_framed = False
        bounds = [[p.latitude, p.longitude] for p in _bounds_src]
        pad = int(style.fit_bounds_padding_px)
        _mz = int(
            style.fit_bounds_max_zoom_highlight
            if _species_framed
            else style.fit_bounds_max_zoom
        )
        m.fit_bounds(
            bounds,
            padding=(pad, pad),
            max_zoom=_mz,
        )

    return m


def build_family_map_banner_element_html(
    metrics_line: str,
    *,
    extra_safe_html: str = "",
) -> str:
    """Wrap a single metrics line for insertion above the map (callers escape *metrics_line*)."""
    esc = html_module.escape(metrics_line, quote=False)
    extra = extra_safe_html if extra_safe_html else ""
    return (
        f'<div style="padding:0.35rem 0.75rem;font-size:0.95rem;line-height:1.35;">'
        f"{esc}{extra}</div>"
    )

"""Folium rendering for Family Map (refs #138) — distinct from species overlay styling."""

from __future__ import annotations

import html as html_module
from typing import Callable

import folium
from branca.element import Element

from explorer.app.streamlit.defaults import (
    FamilyMapColourScheme,
    MAP_HEIGHT_PX_DEFAULT,
    active_family_map_colour_scheme,
)
from explorer.core.family_map_compute import (
    DENSITY_BAND_LABELS,
    FamilyLocationPin,
    FamilyMapBannerMetrics,
    format_family_location_popup_html,
)
from explorer.presentation.map_renderer import build_legend_html, create_map, map_overlay_theme_stylesheet

# Match species-map banner placement (``map_renderer``).
_FAMILY_MAP_BANNER_POSITION = "position:fixed;top:10px;right:10px;z-index:1000;"

def family_map_marker_style(
    pin: FamilyLocationPin,
    *,
    style: FamilyMapColourScheme | None = None,
) -> tuple[str, str, int]:
    """Return ``(fill_hex, stroke_hex, stroke_weight)`` for a composition pin."""
    s = style or active_family_map_colour_scheme()
    fills = s.density_fill_hex
    strokes = s.density_stroke_hex
    idx = max(0, min(pin.density_band_index, len(fills) - 1))
    fill = fills[idx]
    stroke = strokes[idx]
    if pin.highlight_match:
        return fill, s.highlight_stroke_hex, s.highlight_stroke_weight
    return fill, stroke, s.base_stroke_weight


def _default_au_center() -> tuple[float, float]:
    return -25.0, 134.0


def build_family_map_banner_overlay_html(metrics: FamilyMapBannerMetrics) -> str:
    """Full fixed banner div (``pebird-map-banner``) for family composition (refs #138)."""
    title = html_module.escape(metrics.family_name, quote=False)
    stats = html_module.escape(
        f"{metrics.total_species_taxonomy} in taxonomy · "
        f"{metrics.species_recorded_user} recorded · "
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
    style: FamilyMapColourScheme | None = None,
) -> str:
    """Dynamic legend: only include density bands present on the map (refs #138)."""
    s = style or active_family_map_colour_scheme()
    pin_list = list(pins)
    bands_present = sorted({int(p.density_band_index) for p in pin_list}) if pin_list else []
    items: list[tuple[str, str, str]] = []
    for i in bands_present:
        if 0 <= i < len(DENSITY_BAND_LABELS):
            lab = DENSITY_BAND_LABELS[i]
            items.append(
                (
                    s.density_stroke_hex[i],
                    s.density_fill_hex[i],
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
        items.append(
            (
                s.highlight_stroke_hex,
                s.density_fill_hex[sw_i],
                f"Highlight: {hl}",
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
) -> folium.Map:
    """Render CircleMarkers for family composition; optional eBird links in popups.

    *location_page_url_fn* maps ``Location ID`` → hotspot URL; *species_url_fn* maps common name
    (as shown in the export) to species page URL.

    When *fit_bounds_highlight_only* is true (highlight species selected), the initial ``fit_bounds``
    uses only pins where ``highlight_match`` is true, with the same padding / ``max_zoom`` as the
    full-family case. If none match, falls back to all pins.
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
        center = _default_au_center()

    m = create_map(center, map_style, height_px=height_px)
    m.get_root().html.add_child(Element(map_overlay_theme_stylesheet()))

    if banner_html and str(banner_html).strip():
        m.get_root().html.add_child(Element(str(banner_html).strip()))

    if legend_html and str(legend_html).strip():
        m.get_root().html.add_child(Element(str(legend_html).strip()))

    loc_fn = location_page_url_fn or (lambda _lid: None)
    sp_fn = species_url_fn or (lambda _c: None)
    style = active_family_map_colour_scheme()

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
            radius=style.circle_marker_radius_px,
            color=stroke,
            weight=sw,
            fill=True,
            fill_color=fill,
            fill_opacity=style.circle_marker_fill_opacity,
            popup=folium.Popup(popup_body, max_width=style.popup_max_width_px),
        ).add_to(m)

    # Family-map-only initial viewport:
    # - fit relevant pins with edge padding (all family pins, or highlight-only when requested)
    # - never start closer than configured max zoom (allow wider zoom-out when needed)
    if pin_list:
        if fit_bounds_highlight_only:
            _bounds_src = [p for p in pin_list if p.highlight_match] or pin_list
        else:
            _bounds_src = pin_list
        bounds = [[p.latitude, p.longitude] for p in _bounds_src]
        pad = int(style.fit_bounds_padding_px)
        m.fit_bounds(
            bounds,
            padding=(pad, pad),
            max_zoom=int(style.fit_bounds_max_zoom),
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

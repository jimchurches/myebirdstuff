"""Folium rendering for Family Map (refs #138) — distinct from species overlay styling."""

from __future__ import annotations

import html as html_module
from typing import Callable

import folium
from branca.element import Element

from explorer.app.streamlit.defaults import (
    FAMILY_MAP_BASE_STROKE_WEIGHT,
    FAMILY_MAP_CIRCLE_MARKER_FILL_OPACITY,
    FAMILY_MAP_CIRCLE_MARKER_RADIUS_PX,
    FAMILY_MAP_DENSITY_FILL_HEX,
    FAMILY_MAP_DENSITY_STROKE_HEX,
    FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM,
    FAMILY_MAP_FIT_BOUNDS_PADDING_PX,
    FAMILY_MAP_HIGHLIGHT_STROKE_HEX,
    FAMILY_MAP_HIGHLIGHT_STROKE_WEIGHT,
    FAMILY_MAP_LEGEND_HIGHLIGHT_SWATCH_FILL_INDEX,
    FAMILY_MAP_POPUP_MAX_WIDTH_PX,
    MAP_HEIGHT_PX_DEFAULT,
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

def family_map_marker_style(pin: FamilyLocationPin) -> tuple[str, str, int]:
    """Return ``(fill_hex, stroke_hex, stroke_weight)`` for a composition pin."""
    fills = FAMILY_MAP_DENSITY_FILL_HEX
    strokes = FAMILY_MAP_DENSITY_STROKE_HEX
    idx = max(0, min(pin.density_band_index, len(fills) - 1))
    fill = fills[idx]
    stroke = strokes[idx]
    if pin.highlight_match:
        return fill, FAMILY_MAP_HIGHLIGHT_STROKE_HEX, FAMILY_MAP_HIGHLIGHT_STROKE_WEIGHT
    return fill, stroke, FAMILY_MAP_BASE_STROKE_WEIGHT


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
) -> str:
    """Dynamic legend: only include density bands present on the map (refs #138)."""
    pin_list = list(pins)
    bands_present = sorted({int(p.density_band_index) for p in pin_list}) if pin_list else []
    items: list[tuple[str, str, str]] = []
    for i in bands_present:
        if 0 <= i < len(DENSITY_BAND_LABELS):
            lab = DENSITY_BAND_LABELS[i]
            items.append(
                (
                    FAMILY_MAP_DENSITY_STROKE_HEX[i],
                    FAMILY_MAP_DENSITY_FILL_HEX[i],
                    f"{lab} species at location",
                )
            )
    hl = (highlight_label or "").strip()
    if hl:
        sw_i = max(
            0,
            min(
                FAMILY_MAP_LEGEND_HIGHLIGHT_SWATCH_FILL_INDEX,
                len(FAMILY_MAP_DENSITY_FILL_HEX) - 1,
            ),
        )
        items.append(
            (
                FAMILY_MAP_HIGHLIGHT_STROKE_HEX,
                FAMILY_MAP_DENSITY_FILL_HEX[sw_i],
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
) -> folium.Map:
    """Render CircleMarkers for family composition; optional eBird links in popups.

    *location_page_url_fn* maps ``Location ID`` → hotspot URL; *species_url_fn* maps common name
    (as shown in the export) to species page URL.
    """
    pin_list = list(pins)
    if pin_list:
        center = (
            sum(p.latitude for p in pin_list) / len(pin_list),
            sum(p.longitude for p in pin_list) / len(pin_list),
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

    # Draw non-highlighted first, then highlighted so highlights sit on top.
    normal = [p for p in pin_list if not p.highlight_match]
    highlighted = [p for p in pin_list if p.highlight_match]
    for pin in normal + highlighted:
        fill, stroke, sw = family_map_marker_style(pin)
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
            radius=FAMILY_MAP_CIRCLE_MARKER_RADIUS_PX,
            color=stroke,
            weight=sw,
            fill=True,
            fill_color=fill,
            fill_opacity=FAMILY_MAP_CIRCLE_MARKER_FILL_OPACITY,
            popup=folium.Popup(popup_body, max_width=FAMILY_MAP_POPUP_MAX_WIDTH_PX),
        ).add_to(m)

    # Family-map-only initial viewport:
    # - fit all pins with some edge padding
    # - never start closer than zoom 6 (allow wider zoom-out when needed)
    if pin_list:
        bounds = [[p.latitude, p.longitude] for p in pin_list]
        pad = int(FAMILY_MAP_FIT_BOUNDS_PADDING_PX)
        m.fit_bounds(
            bounds,
            padding=(pad, pad),
            max_zoom=int(FAMILY_MAP_FIT_BOUNDS_MAX_ZOOM),
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

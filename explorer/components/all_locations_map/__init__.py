"""Streamlit embed for the All locations Leaflet map component."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from explorer.app.streamlit.defaults import MAP_DEBUG_SHOW_ZOOM_LEVEL

_PARENT = Path(__file__).resolve().parent
_BUILD_DIR = _PARENT / "frontend" / "build"

_declared = None


def _component_callable():
    global _declared
    if _declared is not None:
        return _declared
    index_html = _BUILD_DIR / "index.html"
    if not index_html.is_file():
        return None
    _declared = components.declare_component(
        "all_locations_map",
        path=str(_BUILD_DIR),
    )
    return _declared


def render_all_locations_map_component(
    *,
    revision: str,
    geojson: dict,
    height: int,
    key: str,
    map_style: str = "default",
    cluster_options: dict | None = None,
    circle_marker_style: dict | None = None,
    cluster_icon_style: dict | None = None,
    viewport: dict | None = None,
    map_theme_css: str = "",
    map_popup_width_script: str = "",
    banner_html: str = "",
    legend_html: str = "",
) -> None:
    """Render the iframe component or show build instructions when ``frontend/build`` is absent.

    *circle_marker_style* — resolved pin fill/stroke/radius for GeoJSON circle markers.

    *cluster_icon_style* — optional tier rgba dict from :func:`~explorer.core.all_locations_experimental_marker_style.cluster_icon_style_for_all_locations_map` for MarkerCluster ``iconCreateFunction`` (Folium parity). Empty dict uses plugin default cluster colours.

    *viewport* — camera recipe from :func:`~explorer.core.map_overlay_visit_map.all_locations_leaflet_viewport_recipe` (Folium initial view / fit bounds parity). Omit or empty dict to fall back to GeoJSON-bounds padding in the iframe.

    *map_style* — basemap key matching :func:`~explorer.presentation.map_renderer.create_map` (``default``,
    ``google``, ``carto``). Passed from the Prep map tab sidebar; unknown values behave as ``default``.

    *map_theme_css* — same string Folium injects (``map_overlay_theme_stylesheet``) for banner/legend/popup chrome.

    *map_popup_width_script* — normally **omit** / pass empty: popup width is finalized in the component only; passing Folium&apos;s ``map_popup_width_fix_script`` would double-run shrink timers in the iframe.

    *banner_html* / *legend_html* — overlay HTML fragments with ``position:fixed`` (viewport = iframe),
    matching Folium all-locations overlays (top-right banner, bottom-left legend).

    Zoom debug readout follows ``MAP_DEBUG_SHOW_ZOOM_LEVEL`` in ``defaults.py`` (Folium ``add_zoom_level_debug_overlay`` parity).
    """
    fn = _component_callable()
    if fn is None:
        st.warning(
            "Map component assets are missing. Build them once with:\n\n"
            "`cd explorer/components/all_locations_map/frontend && npm install && npm run build`"
        )
        return
    fn(
        revision=revision,
        geojson=geojson,
        height=int(height),
        map_style=str(map_style or "default"),
        cluster_options=cluster_options if cluster_options is not None else {},
        circle_marker_style=circle_marker_style if circle_marker_style is not None else {},
        cluster_icon_style=cluster_icon_style if cluster_icon_style is not None else {},
        viewport=viewport if viewport is not None else {},
        map_theme_css=map_theme_css,
        map_popup_width_script=map_popup_width_script,
        banner_html=banner_html,
        legend_html=legend_html,
        show_zoom_debug=MAP_DEBUG_SHOW_ZOOM_LEVEL,
        key=key,
    )

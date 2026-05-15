"""Resolved Folium-equivalent All locations pin styling for the Leaflet map (#221 / #222)."""

from __future__ import annotations

from typing import Any

from explorer.app.streamlit.defaults import active_map_marker_colour_scheme
from explorer.core.map_overlay_visit_map import (
    _all_locations_marker_params_from_scheme,
    all_locations_cluster_icon_style_payload,
)


def circle_marker_style_for_all_locations_map(colour_scheme_index: int) -> dict[str, Any]:
    """Circle marker props for the Leaflet component from the sidebar marker scheme index."""
    sch = active_map_marker_colour_scheme(int(colour_scheme_index))
    fill_c, edge, radius_px, stroke_w, fill_op = _all_locations_marker_params_from_scheme(sch)
    return {
        "fill_hex": str(fill_c),
        "stroke_hex": str(edge),
        "radius_px": int(radius_px),
        "stroke_weight": int(stroke_w),
        "fill_opacity": float(fill_op),
    }


def cluster_icon_style_for_all_locations_map(colour_scheme_index: int) -> dict[str, Any] | None:
    """MarkerCluster ``iconCreateFunction`` inputs for the Leaflet component (Folium parity)."""
    sch = active_map_marker_colour_scheme(int(colour_scheme_index))
    return all_locations_cluster_icon_style_payload(sch)


def experimental_default_scheme_circle_marker_props() -> dict[str, Any]:
    """Preset **1** (Eucalypt) — kept for spike-era callers; production uses :func:`circle_marker_style_for_all_locations_map`."""
    return circle_marker_style_for_all_locations_map(1)

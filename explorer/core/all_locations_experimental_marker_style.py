"""Resolved Folium-equivalent All locations pin styling for the Leaflet spike (#221).

Experimental tab intentionally pins visuals to bundled preset **1** (``MAP_MARKER_COLOUR_SCHEME_1`` /
Eucalypt) so marker geometry matches the classic map without honoring the sidebar scheme radio during
the spike; production can wire session scheme later.
"""

from __future__ import annotations

from typing import Any

from explorer.app.streamlit.defaults import MAP_MARKER_COLOUR_SCHEME_1
from explorer.core.map_overlay_visit_map import _all_locations_marker_params_from_scheme


def experimental_default_scheme_circle_marker_props() -> dict[str, Any]:
    """Match ``folium.CircleMarker`` kwargs from :func:`_all_locations_marker_params_from_scheme`."""
    fill_c, edge, radius_px, stroke_w, fill_op = _all_locations_marker_params_from_scheme(
        MAP_MARKER_COLOUR_SCHEME_1
    )
    return {
        "fill_hex": str(fill_c),
        "stroke_hex": str(edge),
        "radius_px": int(radius_px),
        "stroke_weight": int(stroke_w),
        "fill_opacity": float(fill_op),
    }

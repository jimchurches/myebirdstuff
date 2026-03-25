"""
Folium / map chrome geometry used by ``map_controller`` and ``map_renderer``.

Framework-neutral: no Streamlit imports. Aligned with the Streamlit app theme in practice
but owned here so ``personal_ebird_explorer`` does not depend on ``streamlit_app`` (refs #89).
"""

from __future__ import annotations

# Folium ``CircleMarker`` geometry (``map_controller``). ``weight`` matches Leaflet/Folium default when
# previously omitted (explicit for discovery).
MAP_CIRCLE_MARKER_RADIUS_PX = 4
MAP_CIRCLE_MARKER_STROKE_WEIGHT = 3
MAP_PIN_FILL_OPACITY_ALL_LOCATIONS = 0.6
MAP_PIN_FILL_OPACITY_EMPHASIS = 0.9
MAP_POPUP_MAX_WIDTH_PX = 800

# Legend sample dots (``map_renderer.pin_legend_item`` HTML).
MAP_LEGEND_PIN_DOT_PX = 8
MAP_LEGEND_PIN_BORDER_PX = 2

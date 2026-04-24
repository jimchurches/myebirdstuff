"""Inject shared Leaflet popup + banner/legend CSS for overlay maps."""

from __future__ import annotations

import folium
from branca.element import Element

from explorer.presentation.map_renderer import map_overlay_theme_stylesheet, map_popup_width_fix_script


def inject_map_overlay_theme(map_obj: folium.Map) -> None:
    """Add theme stylesheet + popup width script to *map_obj* (popups, fixed banner/legend chrome)."""
    html = map_obj.get_root().html
    html.add_child(Element(map_overlay_theme_stylesheet()))
    html.add_child(Element(map_popup_width_fix_script()))

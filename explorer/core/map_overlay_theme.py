"""Inject shared Leaflet popup + banner/legend CSS for overlay maps."""

from __future__ import annotations

import folium
from branca.element import Element

from explorer.presentation.map_renderer import map_overlay_theme_stylesheet


def inject_map_overlay_theme(map_obj: folium.Map) -> None:
    """Add theme stylesheet to *map_obj* (popups, fixed banner/legend chrome)."""
    map_obj.get_root().html.add_child(Element(map_overlay_theme_stylesheet()))

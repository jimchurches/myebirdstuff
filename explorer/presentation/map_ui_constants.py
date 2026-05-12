"""
Folium / map chrome used by ``map_controller`` and ``map_renderer``.

**Popup chrome** (width, Macaulay link symbol) is defined in :mod:`explorer.app.streamlit.defaults`;
re-exported here so call sites can keep importing from this module.
"""

from __future__ import annotations

from explorer.app.streamlit.defaults import MAP_POPUP_MACAULAY_LINK_SYMBOL, MAP_POPUP_MAX_WIDTH_PX

# Species-map popups: when to leave <details> open (refs #145, map_renderer).
SPECIES_MAP_POPUP_OPEN_SPECIES_SECTION_MAX_OBSERVATIONS = 3
SPECIES_MAP_POPUP_OPEN_VISIT_LIST_MAX_CHECKLISTS = 1

__all__ = [
    "MAP_POPUP_MACAULAY_LINK_SYMBOL",
    "MAP_POPUP_MAX_WIDTH_PX",
    "SPECIES_MAP_POPUP_OPEN_SPECIES_SECTION_MAX_OBSERVATIONS",
    "SPECIES_MAP_POPUP_OPEN_VISIT_LIST_MAX_CHECKLISTS",
]

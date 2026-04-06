"""
Folium / map chrome used by ``map_controller`` and ``map_renderer``.

**Popup width** is defined in :mod:`explorer.app.streamlit.defaults` (``MAP_POPUP_MAX_WIDTH_PX``);
re-exported here so call sites can keep importing from this module.
"""

from __future__ import annotations

from explorer.app.streamlit.defaults import MAP_POPUP_MAX_WIDTH_PX

__all__ = ["MAP_POPUP_MAX_WIDTH_PX"]

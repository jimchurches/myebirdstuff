"""Streamlit embed for the All locations experimental Leaflet component (#221)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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
    cluster_options: dict | None = None,
    circle_marker_style: dict | None = None,
) -> None:
    """Render the iframe component or show build instructions when ``frontend/build`` is absent."""
    fn = _component_callable()
    if fn is None:
        st.warning(
            "Experimental map assets are missing. Build them once with:\n\n"
            "`cd explorer/components/all_locations_map/frontend && npm install && npm run build`"
        )
        return
    fn(
        revision=revision,
        geojson=geojson,
        height=int(height),
        cluster_options=cluster_options if cluster_options is not None else {},
        circle_marker_style=circle_marker_style if circle_marker_style is not None else {},
        key=key,
    )

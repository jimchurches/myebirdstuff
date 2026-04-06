"""
Single source for checklist-style Streamlit HTML tab surface theme (green vs eBird blue) (refs #95).

Tab modules use :func:`inject_streamlit_checklist_css` (refs #96) for table + tab-surface injection, or
compose ``CHECKLIST_STATS_TABLE_CSS`` + :data:`CHECKLIST_STATS_HTML_TAB_SURFACE_CSS` plus any tab-specific
rules. Changing only the surface CSS here rethemes every tab; local extra CSS blocks remain additive overlays.
"""

from __future__ import annotations

import streamlit as st

from explorer.presentation.checklist_stats_display import (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS,
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE,
    CHECKLIST_STATS_TABLE_CSS,
)

# Flip this one flag to theme all checklist-style HTML tabs at once.
USE_EBIRD_BLUE_HTML_TAB_THEME = False

CHECKLIST_STATS_HTML_TAB_SURFACE_CSS = (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    if USE_EBIRD_BLUE_HTML_TAB_THEME
    else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
)


def inject_streamlit_checklist_css(extra_css: str = "") -> None:
    """Inject scoped checklist table + Streamlit tab-surface CSS via ``st.markdown`` (refs #96).

    Uses :data:`CHECKLIST_STATS_HTML_TAB_SURFACE_CSS` (see ``USE_EBIRD_BLUE_HTML_TAB_THEME``). Append
    *extra_css* for tab-specific rules (e.g. Country link row, Rankings max-width).
    """
    st.markdown(
        "<style>"
        f"{CHECKLIST_STATS_TABLE_CSS}"
        f"{CHECKLIST_STATS_HTML_TAB_SURFACE_CSS}"
        f"{extra_css}"
        "</style>",
        unsafe_allow_html=True,
    )

"""
**Yearly Summary** (Streamlit): nested **All** / **Travelling** / **Stationary** tabs (refs #85).

HTML from :func:`build_yearly_summary_streamlit_tab_html_dict`; styles match Checklist Statistics
(``CHECKLIST_STATS_TABLE_CSS`` + tab surface CSS under ``.streamlit-checklist-html-ab``).
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from personal_ebird_explorer.checklist_stats_compute import ChecklistStatsPayload
from personal_ebird_explorer.checklist_stats_display import (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS,
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE,
    CHECKLIST_STATS_TABLE_CSS,
    build_yearly_summary_streamlit_tab_html_dict,
)

_USE_EBIRD_BLUE_HTML_TAB_THEME = False
_YEARLY_HTML_TAB_SURFACE_CSS = (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    if _USE_EBIRD_BLUE_HTML_TAB_THEME
    else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
)


def render_yearly_summary_streamlit_tab(payload: Optional[ChecklistStatsPayload]) -> None:
    """Render global yearly summary as nested Streamlit tabs (default **All**)."""
    st.markdown(
        "<style>"
        f"{CHECKLIST_STATS_TABLE_CSS}"
        f"{_YEARLY_HTML_TAB_SURFACE_CSS}"
        "</style>",
        unsafe_allow_html=True,
    )
    if payload is None:
        st.warning("No checklist data to show.")
        return
    bodies = build_yearly_summary_streamlit_tab_html_dict(payload)
    if bodies is None:
        st.info("No yearly data.")
        return
    tab_all, tab_travelling, tab_stationary = st.tabs(["All", "Travelling", "Stationary"])
    def _yearly_wrap(inner: str) -> str:
        return (
            '<div class="streamlit-checklist-html-ab streamlit-yearly-summary-ab">'
            f"{inner}</div>"
        )

    with tab_all:
        st.markdown(_yearly_wrap(bodies["all"]), unsafe_allow_html=True)
    with tab_travelling:
        st.markdown(_yearly_wrap(bodies["travelling"]), unsafe_allow_html=True)
    with tab_stationary:
        st.markdown(_yearly_wrap(bodies["stationary"]), unsafe_allow_html=True)

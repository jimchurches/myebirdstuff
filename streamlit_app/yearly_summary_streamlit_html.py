"""
**Yearly Summary** (Streamlit): nested **All** / **Travelling** / **Stationary** tabs (refs #85).

HTML from :func:`build_yearly_summary_streamlit_tab_html_dict`; styles match Checklist Statistics
(``CHECKLIST_STATS_TABLE_CSS`` + tab surface CSS under ``.streamlit-checklist-html-ab``).

When the dataset has more years than **Settings → Tables & lists → Yearly tables: recent year columns**
(3–25, default 10), **both** the recent window and full history are rendered once; a **native HTML checkbox**
swaps visibility **without a Streamlit rerun** (avoids full-app “busy” state on toggle).

The tab body runs inside :func:`run_yearly_summary_streamlit_fragment` so interacting with nested
``st.tabs`` only triggers a **partial** fragment rerun (see Streamlit fragments docs).

Call :func:`sync_yearly_summary_session_inputs` from the main script on every full run so the fragment
can read the current :class:`~personal_ebird_explorer.checklist_stats_compute.ChecklistStatsPayload`.
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
    format_yearly_streamlit_dual_view_html,
)

_USE_EBIRD_BLUE_HTML_TAB_THEME = False
_YEARLY_HTML_TAB_SURFACE_CSS = (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    if _USE_EBIRD_BLUE_HTML_TAB_THEME
    else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
)

_SESSION_YEARLY_PAYLOAD_KEY = "_streamlit_yearly_summary_checklist_payload"


def get_yearly_recent_column_count() -> int:
    """Recent-year column window for Yearly Summary + Country (``streamlit_yearly_recent_column_count``; 3–25)."""
    n = int(st.session_state.get("streamlit_yearly_recent_column_count", 10))
    return max(3, min(25, n))


def sync_yearly_summary_session_inputs(payload: Optional[ChecklistStatsPayload]) -> None:
    """Store payload for :func:`run_yearly_summary_streamlit_fragment` (full script runs only)."""
    st.session_state[_SESSION_YEARLY_PAYLOAD_KEY] = payload


def _yearly_wrap_markdown(inner: str) -> str:
    return (
        '<div class="streamlit-checklist-html-ab streamlit-yearly-summary-ab">'
        f"{inner}</div>"
    )


def _yearly_wrap_html(inner: str) -> str:
    return (
        '<div class="streamlit-checklist-html-ab streamlit-yearly-summary-ab">'
        f"{inner}</div>"
    )


@st.fragment
def run_yearly_summary_streamlit_fragment() -> None:
    """Yearly Summary UI; widget interactions here avoid rerunning the whole app where possible."""
    st.markdown(
        "<style>"
        f"{CHECKLIST_STATS_TABLE_CSS}"
        f"{_YEARLY_HTML_TAB_SURFACE_CSS}"
        "</style>",
        unsafe_allow_html=True,
    )

    payload: Optional[ChecklistStatsPayload] = st.session_state.get(_SESSION_YEARLY_PAYLOAD_KEY)
    if payload is None:
        st.warning("No checklist data to show.")
        return
    if not payload.years_list or not payload.yearly_rows:
        st.info("No yearly data.")
        return

    n_years = len(payload.years_list)
    recent_n = get_yearly_recent_column_count()
    if n_years > recent_n:
        bodies_recent = build_yearly_summary_streamlit_tab_html_dict(
            payload,
            show_full_history=False,
            recent_year_count=recent_n,
        )
        bodies_full = build_yearly_summary_streamlit_tab_html_dict(
            payload,
            show_full_history=True,
            recent_year_count=recent_n,
        )
        if bodies_recent is None or bodies_full is None:
            st.info("No yearly data.")
            return

        def _pane(key: str, dom_suffix: str) -> None:
            dual = format_yearly_streamlit_dual_view_html(
                bodies_recent[key],
                bodies_full[key],
                dom_suffix=dom_suffix,
                recent_year_count=recent_n,
            )
            st.html(_yearly_wrap_html(dual))

        tab_all, tab_travelling, tab_stationary = st.tabs(["All", "Travelling", "Stationary"])
        with tab_all:
            _pane("all", "yearly-sum-all")
        with tab_travelling:
            _pane("travelling", "yearly-sum-travelling")
        with tab_stationary:
            _pane("stationary", "yearly-sum-stationary")
        return

    bodies = build_yearly_summary_streamlit_tab_html_dict(payload, show_full_history=True)
    if bodies is None:
        st.info("No yearly data.")
        return

    tab_all, tab_travelling, tab_stationary = st.tabs(["All", "Travelling", "Stationary"])
    with tab_all:
        st.markdown(_yearly_wrap_markdown(bodies["all"]), unsafe_allow_html=True)
    with tab_travelling:
        st.markdown(_yearly_wrap_markdown(bodies["travelling"]), unsafe_allow_html=True)
    with tab_stationary:
        st.markdown(_yearly_wrap_markdown(bodies["stationary"]), unsafe_allow_html=True)

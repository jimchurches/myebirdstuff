"""
**Yearly Summary** (Streamlit): nested **All** / **Travelling** / **Stationary** tabs (refs #85).

HTML from :func:`build_yearly_summary_streamlit_tab_html_dict`; styles match Checklist Statistics
(``CHECKLIST_STATS_TABLE_CSS`` + tab surface CSS under ``.streamlit-checklist-html-ab``).

When the dataset has more years than **Settings → Tables & lists → Yearly tables: recent year columns**
(3–25, default 10), a **Show full history** ``st.toggle`` below the nested tabs switches between the
recent window and all columns. One protocol note (All + Travelling/Stationary completeness) sits below
that control with spacing—redundant per-tab footnotes were removed. Reruns are limited to this ``@st.fragment``
(same pattern as **Country**).

**Placement:** A single toggle after all ``with tab:`` blocks stays below the active table while avoiding
duplicate keys (the same widget cannot be declared inside each nested tab).

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
    format_yearly_streamlit_all_tab_protocol_note_html,
)

_USE_EBIRD_BLUE_HTML_TAB_THEME = False
_YEARLY_HTML_TAB_SURFACE_CSS = (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    if _USE_EBIRD_BLUE_HTML_TAB_THEME
    else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
)

_SESSION_YEARLY_PAYLOAD_KEY = "_streamlit_yearly_summary_checklist_payload"
_STREAMLIT_YEARLY_SHOW_FULL_KEY = "streamlit_yearly_summary_show_full"


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
        show_full = bool(st.session_state.get(_STREAMLIT_YEARLY_SHOW_FULL_KEY, False))
    else:
        show_full = True

    bodies = build_yearly_summary_streamlit_tab_html_dict(
        payload,
        show_full_history=show_full,
        recent_year_count=recent_n,
    )
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

    if n_years > recent_n:
        st.toggle(
            "Show full history",
            key=_STREAMLIT_YEARLY_SHOW_FULL_KEY,
            width="content",
        )
        if not st.session_state.get(_STREAMLIT_YEARLY_SHOW_FULL_KEY, False):
            st.caption(f"Showing results for the most recent {recent_n} years.")

    st.markdown('<div style="height:1rem;" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(format_yearly_streamlit_all_tab_protocol_note_html(), unsafe_allow_html=True)

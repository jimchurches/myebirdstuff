"""
**Checklist Statistics** (Streamlit): six sections as nested ``st.tabs``, one pane per table.

Uses ``checklist_stats_streamlit_tab_sections_html`` (shared with ``format_checklist_stats_bundle`` column blocks).
Styles: :func:`~streamlit_app.streamlit_theme.inject_streamlit_checklist_css` — injected **once** per page; all rules scoped under ``.streamlit-checklist-html-ab``.

**Style:** green striping/accents (default); eBird-blue via ``streamlit_app.streamlit_theme`` (refs #95).
Refs #70.
"""

from __future__ import annotations

import streamlit as st

from personal_ebird_explorer.checklist_stats_compute import ChecklistStatsPayload
from personal_ebird_explorer.checklist_stats_display import checklist_stats_streamlit_tab_sections_html
from explorer.app.streamlit.app_constants import CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY
from explorer.app.streamlit.streamlit_theme import inject_streamlit_checklist_css


def sync_checklist_stats_tab_session_inputs(payload: ChecklistStatsPayload | None) -> None:
    """Store working-set payload for :func:`run_checklist_stats_streamlit_fragment` (full script runs)."""
    st.session_state[CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY] = payload


@st.fragment
def run_checklist_stats_streamlit_fragment() -> None:
    """Checklist Statistics UI; widget interactions here avoid full-app reruns where possible."""
    payload = st.session_state.get(CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY)
    if payload is None:
        st.warning("No checklist data to show.")
        return
    render_checklist_stats_streamlit_html(payload)


def render_checklist_stats_streamlit_html(
    payload: ChecklistStatsPayload,
) -> None:
    """Render checklist stats as nested Streamlit tabs (section order fixed in ``checklist_stats_display``)."""

    sections = checklist_stats_streamlit_tab_sections_html(payload)
    labels = [label for label, _ in sections]

    # Tooltips + rankings helpers once; panel chrome once (scoped under .streamlit-checklist-html-ab).
    inject_streamlit_checklist_css()

    tab_objs = st.tabs(labels)
    for tab, (_, inner_html) in zip(tab_objs, sections):
        with tab:
            st.markdown(
                f'<div class="streamlit-checklist-html-ab">{inner_html}</div>',
                unsafe_allow_html=True,
            )

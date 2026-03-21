"""
**Checklist Statistics** (Streamlit): six sections as nested ``st.tabs``, one pane per table.

Uses ``checklist_stats_streamlit_tab_sections_html`` (shared with ``format_checklist_stats_bundle`` column blocks).
Styles: ``CHECKLIST_STATS_TABLE_CSS`` + tab-surface CSS from ``checklist_stats_display`` — injected **once** per page; all rules scoped under ``.streamlit-checklist-html-ab``.

**Style:** green striping/accents (default). Set ``_USE_EBIRD_BLUE_HTML_TAB_THEME = True`` to try eBird-blue.
Refs #70.
"""

from __future__ import annotations

from typing import Callable, Optional

import streamlit as st

from personal_ebird_explorer.checklist_stats_compute import ChecklistStatsPayload
from personal_ebird_explorer.checklist_stats_display import (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS,
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE,
    CHECKLIST_STATS_TABLE_CSS,
    checklist_stats_streamlit_tab_sections_html,
)

_USE_EBIRD_BLUE_HTML_TAB_THEME = False

_CHECKLIST_HTML_TAB_SURFACE_CSS = (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    if _USE_EBIRD_BLUE_HTML_TAB_THEME
    else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
)


def render_checklist_stats_streamlit_html(
    payload: ChecklistStatsPayload,
    *,
    species_url_fn: Callable[[str], Optional[str]],
) -> None:
    """Render checklist stats as nested Streamlit tabs (section order fixed in ``checklist_stats_display``)."""

    _ = species_url_fn  # Reserved for future species links in this tab; rankings HTML not shown here.

    sections = checklist_stats_streamlit_tab_sections_html(payload)
    labels = [label for label, _ in sections]

    # Tooltips + rankings helpers once; panel chrome once (scoped under .streamlit-checklist-html-ab).
    st.markdown(
        "<style>"
        f"{CHECKLIST_STATS_TABLE_CSS}"
        f"{_CHECKLIST_HTML_TAB_SURFACE_CSS}"
        "</style>",
        unsafe_allow_html=True,
    )

    tab_objs = st.tabs(labels)
    for tab, (_, inner_html) in zip(tab_objs, sections):
        with tab:
            st.markdown(
                f'<div class="streamlit-checklist-html-ab">{inner_html}</div>',
                unsafe_allow_html=True,
            )

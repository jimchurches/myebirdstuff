"""
**Yearly Summary** (Streamlit): one country at a time, custom HTML aligned with Checklist Statistics (refs #75).

Country order follows **Settings → Tables & lists → Country ordering** (``streamlit_country_tab_sort``).
"""

from __future__ import annotations

import streamlit as st

from personal_ebird_explorer.checklist_stats_compute import ChecklistStatsPayload
from personal_ebird_explorer.checklist_stats_display import (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS,
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE,
    CHECKLIST_STATS_TABLE_CSS,
    _sort_country_sections,
    country_display_name_plain,
    country_yearly_links_bar_html,
    format_country_yearly_table_html,
)

# Match ``checklist_stats_streamlit_html`` default (green); flip there if you theme the whole app blue.
_USE_EBIRD_BLUE_HTML_TAB_THEME = False

_YEARLY_EXTRA_CSS = """
.streamlit-checklist-html-ab .stats-links-row { margin: 0 0 0.65rem; line-height: 1.45; }
.streamlit-checklist-html-ab .stats-links-row a { font-weight: 500; }
.streamlit-checklist-html-ab .stats-link-sep { opacity: 0.55; padding: 0 0.15em; }
.streamlit-checklist-html-ab .stats-link-icon { opacity: 0.85; }
"""


def render_yearly_summary_streamlit_html(
    payload: ChecklistStatsPayload | None,
    *,
    country_sort: str,
) -> None:
    """Yearly-by-country table for the selected country; ordering from *country_sort*."""
    tab_css = (
        CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
        if _USE_EBIRD_BLUE_HTML_TAB_THEME
        else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
    )

    st.markdown(
        "<style>"
        f"{CHECKLIST_STATS_TABLE_CSS}"
        f"{tab_css}"
        f"{_YEARLY_EXTRA_CSS}"
        "</style>",
        unsafe_allow_html=True,
    )

    if payload is None or not payload.country_sections:
        st.info("No country data to show. Add **Country** or **State/Province** to your eBird export.")
        return

    sorted_sections = _sort_country_sections(payload.country_sections, country_sort)
    valid = [(ck, ys, rs) for ck, ys, rs in sorted_sections if ys and rs]
    keys = [ck for ck, _, _ in valid]
    if not keys:
        st.info("No per-country yearly statistics for this dataset.")
        return

    cur = st.session_state.get("streamlit_yearly_country")
    if cur not in keys:
        st.session_state.streamlit_yearly_country = keys[0]

    st.markdown("#### By country")
    selected = st.selectbox(
        "Country",
        options=keys,
        format_func=country_display_name_plain,
        key="streamlit_yearly_country",
        help="Order of countries is controlled under **Settings → Tables & lists**.",
    )

    section_by_key = {ck: (ys, rs) for ck, ys, rs in valid}
    years_list, rows = section_by_key[selected]

    st.subheader(country_display_name_plain(selected))
    links_html = country_yearly_links_bar_html(selected)
    table_html = format_country_yearly_table_html(
        selected,
        years_list,
        rows,
        inline_statistic_links=False,
    )

    inner = f"{links_html}{table_html}" if links_html else table_html
    st.markdown(
        f'<div class="streamlit-checklist-html-ab">{inner}</div>',
        unsafe_allow_html=True,
    )

"""
**Country** (Streamlit): one country at a time — same HTML/CSS patterns as Checklist Statistics (refs #75).

Country order follows **Settings → Tables & lists → Country ordering** (``streamlit_country_tab_sort``).

Per-country yearly tables use the same **recent 10 years / full history** HTML checkbox pattern as
**Yearly Summary** when the country has more than 10 year columns (refs #85).
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
    format_yearly_streamlit_dual_view_html,
    slice_yearly_table_rows,
    yearly_streamlit_year_window_slice,
)
from yearly_summary_streamlit_html import get_yearly_recent_column_count

# Match ``checklist_stats_streamlit_html`` default (green); flip there if you theme the whole app blue.
_USE_EBIRD_BLUE_HTML_TAB_THEME = False

_COUNTRY_TAB_EXTRA_CSS = """
.streamlit-checklist-html-ab .stats-links-row { margin: 0 0 0.65rem; line-height: 1.45; }
.streamlit-checklist-html-ab .stats-links-row a { font-weight: 500; }
.streamlit-checklist-html-ab .stats-link-sep { opacity: 0.55; padding: 0 0.15em; }
.streamlit-checklist-html-ab .stats-link-icon { opacity: 0.85; }
"""

# Set by ``app.py`` on every full script run so ``@st.fragment`` partial reruns still see the payload.
_SESSION_PAYLOAD_KEY = "_streamlit_country_tab_checklist_payload"


def render_country_stats_streamlit_html(
    payload: ChecklistStatsPayload | None,
    *,
    country_sort: str,
) -> None:
    """Per-country yearly statistics table; ordering from *country_sort*."""
    tab_css = (
        CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
        if _USE_EBIRD_BLUE_HTML_TAB_THEME
        else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
    )

    st.markdown(
        "<style>"
        f"{CHECKLIST_STATS_TABLE_CSS}"
        f"{tab_css}"
        f"{_COUNTRY_TAB_EXTRA_CSS}"
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
        st.info("No per-country statistics for this dataset.")
        return

    # Prefer new key; fall back if user had a session from the old Yearly tab widget.
    if (
        st.session_state.get("streamlit_country_tab_country") is None
        and st.session_state.get("streamlit_yearly_country") is not None
    ):
        st.session_state.streamlit_country_tab_country = st.session_state.streamlit_yearly_country
    cur = st.session_state.get("streamlit_country_tab_country")
    if cur not in keys:
        st.session_state.streamlit_country_tab_country = keys[0]

    selected = st.selectbox(
        "Country for statistics",
        options=keys,
        format_func=country_display_name_plain,
        key="streamlit_country_tab_country",
        label_visibility="hidden",
    )

    section_by_key = {ck: (ys, rs) for ck, ys, rs in valid}
    years_list, rows = section_by_key[selected]

    st.subheader(country_display_name_plain(selected))
    links_html = country_yearly_links_bar_html(selected)

    recent_n = get_yearly_recent_column_count()
    if len(years_list) > recent_n:
        y_slice = yearly_streamlit_year_window_slice(
            years_list,
            show_full_history=False,
            recent_count=recent_n,
        )
        years_recent = years_list[y_slice]
        rows_recent = slice_yearly_table_rows(rows, years_list, y_slice)
        table_recent = format_country_yearly_table_html(
            selected,
            years_recent,
            rows_recent,
            inline_statistic_links=False,
        )
        table_full = format_country_yearly_table_html(
            selected,
            years_list,
            rows,
            inline_statistic_links=False,
        )
        dual = format_yearly_streamlit_dual_view_html(
            table_recent,
            table_full,
            dom_suffix=f"country-{selected}",
            recent_year_count=recent_n,
        )
        inner = f"{links_html}{dual}" if links_html else dual
        st.html(f'<div class="streamlit-checklist-html-ab">{inner}</div>')
    else:
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


def sync_country_tab_session_inputs(payload: ChecklistStatsPayload | None) -> None:
    """Call from the main script each full run so ``@st.fragment`` partial reruns read the payload."""
    st.session_state[_SESSION_PAYLOAD_KEY] = payload


@st.fragment
def run_country_tab_streamlit_fragment() -> None:
    """Partial reruns: only this fragment when Country selectbox changes (refs #75).

    Full app reruns still call :func:`sync_country_tab_session_inputs`.
    """
    payload = st.session_state.get(_SESSION_PAYLOAD_KEY)
    country_sort = st.session_state.streamlit_country_tab_sort
    render_country_stats_streamlit_html(
        payload,
        country_sort=country_sort,
    )

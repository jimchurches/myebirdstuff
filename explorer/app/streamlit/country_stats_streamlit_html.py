"""
**Country** (Streamlit): one country at a time — same HTML/CSS patterns as Checklist Statistics (refs #75).

Country order follows **Settings → Tables & lists → Country ordering** (``streamlit_country_tab_sort``).

Per-country yearly tables match **Yearly Summary**: when year columns exceed **Settings → Yearly tables:
recent year columns**, a **Show full history** ``st.toggle`` switches recent vs full (refs #85).
"""

from __future__ import annotations

import streamlit as st

from explorer.core.checklist_stats_compute import ChecklistStatsPayload
from explorer.presentation.checklist_stats_display import (
    sort_country_sections_for_display,
    country_display_name_plain,
    country_yearly_links_bar_html,
    format_country_yearly_table_html,
    slice_yearly_table_rows,
    yearly_streamlit_year_window_slice,
)
from explorer.app.streamlit.streamlit_theme import inject_streamlit_checklist_css
from explorer.app.streamlit.yearly_summary_streamlit_html import get_yearly_recent_column_count
from explorer.app.streamlit.app_constants import (
    COUNTRY_TAB_CHECKLIST_PAYLOAD_KEY,
    STREAMLIT_COUNTRY_TAB_COUNTRY_KEY,
    STREAMLIT_COUNTRY_YEARLY_SHOW_FULL_KEY,
)

_COUNTRY_TAB_EXTRA_CSS = """
.streamlit-checklist-html-ab .stats-links-row { margin: 0 0 0.65rem; line-height: 1.45; }
.streamlit-checklist-html-ab .stats-links-row a { font-weight: 500; }
.streamlit-checklist-html-ab .stats-link-sep { opacity: 0.55; padding: 0 0.15em; }
.streamlit-checklist-html-ab .stats-link-icon { opacity: 0.85; }
"""

# Set by ``app.py`` on every full script run so ``@st.fragment`` partial reruns still see the payload.


def render_country_stats_streamlit_html(
    payload: ChecklistStatsPayload | None,
    *,
    country_sort: str,
) -> None:
    """Per-country yearly statistics table; ordering from *country_sort*."""
    inject_streamlit_checklist_css(_COUNTRY_TAB_EXTRA_CSS)

    if payload is None or not payload.country_sections:
        st.info("No country data to show. Add **Country** or **State/Province** to your eBird export.")
        return

    sorted_sections = sort_country_sections_for_display(payload.country_sections, country_sort)
    valid = [(ck, ys, rs) for ck, ys, rs in sorted_sections if ys and rs]
    keys = [ck for ck, _, _ in valid]
    if not keys:
        st.info("No per-country statistics for this dataset.")
        return

    cur = st.session_state.get(STREAMLIT_COUNTRY_TAB_COUNTRY_KEY)
    if cur not in keys:
        st.session_state[STREAMLIT_COUNTRY_TAB_COUNTRY_KEY] = keys[0]

    selected = st.selectbox(
        "Country for statistics",
        options=keys,
        format_func=country_display_name_plain,
        key=STREAMLIT_COUNTRY_TAB_COUNTRY_KEY,
        label_visibility="hidden",
    )

    section_by_key = {ck: (ys, rs) for ck, ys, rs in valid}
    years_list, rows = section_by_key[selected]

    st.subheader(country_display_name_plain(selected))
    links_html = country_yearly_links_bar_html(selected)

    recent_n = get_yearly_recent_column_count()
    n_years = len(years_list)
    if n_years > recent_n:
        show_full = bool(
            st.session_state.get(STREAMLIT_COUNTRY_YEARLY_SHOW_FULL_KEY, False)
        )
        if show_full:
            table_html = format_country_yearly_table_html(
                selected,
                years_list,
                rows,
                inline_statistic_links=False,
            )
        else:
            y_slice = yearly_streamlit_year_window_slice(
                years_list,
                show_full_history=False,
                recent_count=recent_n,
            )
            years_recent = years_list[y_slice]
            rows_recent = slice_yearly_table_rows(rows, years_list, y_slice)
            table_html = format_country_yearly_table_html(
                selected,
                years_recent,
                rows_recent,
                inline_statistic_links=False,
            )
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

    if n_years > recent_n:
        st.toggle(
            "Show full history",
            key=STREAMLIT_COUNTRY_YEARLY_SHOW_FULL_KEY,
            width="content",
        )
        if not st.session_state.get(STREAMLIT_COUNTRY_YEARLY_SHOW_FULL_KEY, False):
            st.caption(f"Showing results for the most recent {recent_n} years.")


def sync_country_tab_session_inputs(payload: ChecklistStatsPayload | None) -> None:
    """Call from the main script each full run so ``@st.fragment`` partial reruns read the payload."""
    st.session_state[COUNTRY_TAB_CHECKLIST_PAYLOAD_KEY] = payload


@st.fragment
def run_country_tab_streamlit_fragment() -> None:
    """Partial reruns: only this fragment when Country selectbox changes (refs #75).

    Full app reruns still call :func:`sync_country_tab_session_inputs`.
    """
    payload = st.session_state.get(COUNTRY_TAB_CHECKLIST_PAYLOAD_KEY)
    country_sort = st.session_state.streamlit_country_tab_sort
    render_country_stats_streamlit_html(
        payload,
        country_sort=country_sort,
    )

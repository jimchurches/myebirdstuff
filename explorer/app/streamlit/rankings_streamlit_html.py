"""
**Rankings & lists** (Streamlit): nested tabs **Top Lists** / **Interesting Lists**, expanders per list.

Uses HTML from :func:`personal_ebird_explorer.checklist_stats_display.format_checklist_stats_bundle`
(``rankings_sections_top_n`` / ``rankings_sections_other``) — same tables as the explorer’s richly-linked HTML tables,
rendered with ``st.markdown(..., unsafe_allow_html=True)``. Table styling matches **Checklist Statistics**:
:func:`~streamlit_app.streamlit_theme.inject_streamlit_checklist_css` plus Rankings width scoped under
``streamlit-checklist-html-ab`` (plus ``streamlit-rankings-html`` for width). Do not use ``st.dataframe``.

**Top N** and **visible rows** are controlled from **Settings → Tables & lists** (session keys
``streamlit_rankings_top_n``, ``streamlit_rankings_visible_rows``; refs `#81`). **Top Lists** tables
include a narrow leading **Rank** column with soft accent styling (refs `#83`). **Species: Not seen in
the past year** is the last expander under Interesting Lists; it lists countable species with no
observation in the trailing twelve months and is not Top-N–capped (refs `#106`; geographic filters are `#108`).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from personal_ebird_explorer.checklist_stats_display import format_checklist_stats_bundle
from personal_ebird_explorer.taxonomy import get_species_and_lifelist_urls, load_taxonomy

from explorer.app.streamlit.app_caches import cached_full_export_checklist_stats_payload
from explorer.app.streamlit.app_constants import RANKINGS_TAB_BUNDLE_KEY
from explorer.app.streamlit.defaults import RANKINGS_BUNDLE_SCROLL_HINT_DEFAULT, RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX
from explorer.app.streamlit.streamlit_theme import inject_streamlit_checklist_css

# Must include ``streamlit-checklist-html-ab`` — ``CHECKLIST_STATS_*`` rules are scoped to it (same as Checklist Statistics).
_STREAMLIT_TABLE_SCOPE = "streamlit-checklist-html-ab"
_RANKINGS_SCOPE_EXTRA = "streamlit-rankings-html"


@st.cache_data(show_spinner=False)
def _cached_rankings_stats_bundle(
    df: pd.DataFrame,
    top_n: int,
    visible_rows: int,
    country_sort: str,
    taxonomy_locale: str,
    high_count_sort: str,
    high_count_tie_break: str,
) -> dict[str, Any]:
    """Notebook-parity rankings bundle (full export + Top N + scroll + taxonomy links). refs #81."""
    loc = taxonomy_locale.strip() if taxonomy_locale else None
    link_urls_fn = get_species_and_lifelist_urls if load_taxonomy(locale=loc) else (lambda _: (None, None))
    payload = cached_full_export_checklist_stats_payload(
        df,
        top_n,
        high_count_sort,
        high_count_tie_break,
    )
    return format_checklist_stats_bundle(
        payload,
        link_urls_fn=link_urls_fn,
        scroll_hint=RANKINGS_BUNDLE_SCROLL_HINT_DEFAULT,
        visible_rows=visible_rows,
        country_sort=country_sort,
        high_count_sort=high_count_sort,
        high_count_tie_break=high_count_tie_break,
    )


def sync_rankings_tab_session_inputs(bundle: dict[str, Any]) -> None:
    """Store formatted Rankings bundle for :func:`run_rankings_streamlit_tab_fragment` (full script runs)."""
    st.session_state[RANKINGS_TAB_BUNDLE_KEY] = bundle


def render_rankings_streamlit_tab_from_bundle(bundle: dict[str, Any]) -> None:
    """Render Rankings HTML from a precomputed bundle (fragment-safe)."""
    inject_streamlit_checklist_css(
        f".{_STREAMLIT_TABLE_SCOPE}.{_RANKINGS_SCOPE_EXTRA} {{ max-width:{RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX}px;width:100%; }}"
    )

    tab_top, tab_int = st.tabs(["Top Lists", "Interesting Lists"])

    with tab_top:
        for title, inner_html in bundle.get("rankings_sections_top_n") or []:
            with st.expander(title, expanded=False):
                st.markdown(
                    f'<div class="{_STREAMLIT_TABLE_SCOPE} {_RANKINGS_SCOPE_EXTRA}">{inner_html}</div>',
                    unsafe_allow_html=True,
                )

    with tab_int:
        for title, inner_html in bundle.get("rankings_sections_other") or []:
            with st.expander(title, expanded=False):
                st.markdown(
                    f'<div class="{_STREAMLIT_TABLE_SCOPE} {_RANKINGS_SCOPE_EXTRA}">{inner_html}</div>',
                    unsafe_allow_html=True,
                )


@st.fragment
def run_rankings_streamlit_tab_fragment() -> None:
    """Partial reruns when Rankings expanders/widgets change (same pattern as Country / Yearly)."""
    bundle = st.session_state.get(RANKINGS_TAB_BUNDLE_KEY) or {}
    if not bundle.get("rankings_sections_top_n") and not bundle.get("rankings_sections_other"):
        st.info("Load checklist data to use Rankings & lists.")
        return
    render_rankings_streamlit_tab_from_bundle(bundle)


def build_rankings_tab_bundle(
    df_full: pd.DataFrame,
    *,
    country_sort: str,
    taxonomy_locale: str,
    high_count_sort: str,
    high_count_tie_break: str,
) -> dict[str, Any]:
    """Compute cached Rankings bundle (call from main script alongside other full-export prep)."""
    return _cached_rankings_stats_bundle(
        df_full,
        int(st.session_state.streamlit_rankings_top_n),
        int(st.session_state.streamlit_rankings_visible_rows),
        country_sort,
        taxonomy_locale,
        high_count_sort,
        high_count_tie_break,
    )

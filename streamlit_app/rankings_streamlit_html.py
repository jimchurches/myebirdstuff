"""
**Rankings & lists** (Streamlit): nested tabs **Top Lists** / **Interesting Lists**, expanders per list.

Uses HTML from :func:`personal_ebird_explorer.checklist_stats_display.format_checklist_stats_bundle`
(``rankings_sections_top_n`` / ``rankings_sections_other``) — same tables as the Jupyter notebook,
rendered with ``st.markdown(..., unsafe_allow_html=True)``. Do not use ``st.dataframe`` for these tables.

**Top N** / **visible rows** sliders live in **Top Lists**; duplicate controls may exist under **Settings**
for UI evaluation (refs `#81`).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from personal_ebird_explorer.checklist_stats_compute import compute_checklist_stats_payload
from personal_ebird_explorer.checklist_stats_display import (
    CHECKLIST_STATS_TABLE_CSS,
    format_checklist_stats_bundle,
)
from personal_ebird_explorer.taxonomy import get_species_and_lifelist_urls, load_taxonomy

_RANKINGS_WRAPPER_CLASS = "streamlit-rankings-html"


@st.cache_data(show_spinner=False)
def _cached_rankings_stats_bundle(
    df: pd.DataFrame,
    top_n: int,
    visible_rows: int,
    country_sort: str,
    taxonomy_locale: str,
) -> dict[str, Any]:
    """Notebook-parity rankings bundle (full export + Top N + scroll + taxonomy links). refs #81."""
    loc = taxonomy_locale.strip() if taxonomy_locale else None
    link_urls_fn = get_species_and_lifelist_urls if load_taxonomy(locale=loc) else (lambda _: (None, None))
    payload = compute_checklist_stats_payload(df, top_n)
    return format_checklist_stats_bundle(
        payload,
        link_urls_fn=link_urls_fn,
        scroll_hint="shading",
        visible_rows=visible_rows,
        country_sort=country_sort,
    )


def render_rankings_streamlit_tab(
    df_full: pd.DataFrame,
    *,
    country_sort: str,
    taxonomy_locale: str,
) -> None:
    """Render Rankings & lists from the full export (notebook parity: ``df_full``)."""

    st.markdown(
        "<style>"
        f"{CHECKLIST_STATS_TABLE_CSS}"
        f".{_RANKINGS_WRAPPER_CLASS} {{ font-size:13px;line-height:1.6;max-width:1400px;width:100%; }}"
        "</style>",
        unsafe_allow_html=True,
    )

    tab_top, tab_int = st.tabs(["Top Lists", "Interesting Lists"])

    with tab_top:
        st.slider(
            "Top N table limit",
            min_value=5,
            max_value=500,
            value=200,
            step=1,
            key="streamlit_rankings_top_n",
            help="Maximum rows that feed each “Top …” ranking (same role as notebook Top N).",
        )
        st.slider(
            "Visible rows (scroll)",
            min_value=4,
            max_value=80,
            value=16,
            step=1,
            key="streamlit_rankings_visible_rows",
            help="Scroll area height for rankings tables (row shading).",
        )
        bundle = _cached_rankings_stats_bundle(
            df_full,
            int(st.session_state.streamlit_rankings_top_n),
            int(st.session_state.streamlit_rankings_visible_rows),
            country_sort,
            taxonomy_locale,
        )
        for title, inner_html in bundle.get("rankings_sections_top_n") or []:
            with st.expander(title, expanded=False):
                st.markdown(
                    f'<div class="{_RANKINGS_WRAPPER_CLASS}">{inner_html}</div>',
                    unsafe_allow_html=True,
                )

    with tab_int:
        for title, inner_html in bundle.get("rankings_sections_other") or []:
            with st.expander(title, expanded=False):
                st.markdown(
                    f'<div class="{_RANKINGS_WRAPPER_CLASS}">{inner_html}</div>',
                    unsafe_allow_html=True,
                )

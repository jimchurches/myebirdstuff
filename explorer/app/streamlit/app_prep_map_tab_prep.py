"""Non-map tab prep spinner: checklist, rankings, maintenance, and session sync.

Extracted from ``app_prep_map_ui.render_prep_spinner_and_map_tab`` so map-mode payload
logic can be split incrementally without mixing tab-cache work.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from explorer.app.streamlit.app_caches import (
    cached_checklist_stats_payload,
    cached_full_export_checklist_stats_payload,
    cached_sex_notation_by_year,
    full_location_data_for_maintenance,
)
from explorer.app.streamlit.app_constants import (
    STREAMLIT_CLOSE_LOCATION_METERS_KEY,
    STREAMLIT_COUNTRY_TAB_SORT_KEY,
    STREAMLIT_HIGH_COUNT_SORT_KEY,
    STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY,
    STREAMLIT_RANKINGS_TOP_N_KEY,
)
from explorer.app.streamlit.checklist_stats_streamlit_html import (
    sync_checklist_stats_tab_session_inputs,
)
from explorer.app.streamlit.country_stats_streamlit_html import (
    sync_country_tab_session_inputs,
)
from explorer.app.streamlit.maintenance_streamlit_html import (
    sync_maintenance_tab_session_inputs,
)
from explorer.app.streamlit.perf_instrumentation import perf_span
from explorer.app.streamlit.rankings_streamlit_html import (
    build_ranking_lists_families_bundle,
    sync_ranking_lists_families_bundle,
)
from explorer.app.streamlit.streamlit_ui_constants import TAB_PREP_SPINNER_TEXT
from explorer.app.streamlit.yearly_summary_streamlit_html import (
    sync_yearly_summary_session_inputs,
)


def run_tab_prep_spinner_and_sync(
    *,
    work_df: Any,
    df_full: Any,
    tax_locale_effective: str,
    tab_prep_spinner_text: str = TAB_PREP_SPINNER_TEXT,
) -> None:
    """Second sidebar spinner: checklist/rankings caches and tab session sync."""
    with st.spinner(tab_prep_spinner_text):
        with perf_span("prep.cache_checklist_stats.working"):
            checklist_payload = cached_checklist_stats_payload(work_df, tax_locale_effective)
        top_n = int(st.session_state.get(STREAMLIT_RANKINGS_TOP_N_KEY))
        hc_sort = str(st.session_state.get(STREAMLIT_HIGH_COUNT_SORT_KEY))
        hc_tb = str(st.session_state.get(STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY))
        if df_full is not None and not df_full.empty:
            with perf_span("prep.cache_checklist_stats.full_export"):
                maint_full_payload = cached_full_export_checklist_stats_payload(
                    df_full, top_n, hc_sort, hc_tb, tax_locale_effective
                )
            with perf_span("prep.cache_rankings_bundle"):
                ranking_lists_families_bundle = build_ranking_lists_families_bundle(
                    df_full,
                    country_sort=st.session_state.get(STREAMLIT_COUNTRY_TAB_SORT_KEY),
                    taxonomy_locale=tax_locale_effective,
                    high_count_sort=hc_sort,
                    high_count_tie_break=hc_tb,
                )
            with perf_span("prep.cache_sex_notation_by_year"):
                sex_notation_by_year: dict = cached_sex_notation_by_year(df_full)
        else:
            maint_full_payload = None
            ranking_lists_families_bundle = {}
            sex_notation_by_year = {}

        with perf_span("prep.tab_session_sync"):
            sync_checklist_stats_tab_session_inputs(checklist_payload)
            sync_ranking_lists_families_bundle(ranking_lists_families_bundle)
            loc_maint = full_location_data_for_maintenance(df_full)
            incomplete_maint: dict = {}
            if maint_full_payload is not None:
                incomplete_maint = maint_full_payload.incomplete_by_year or {}
            sync_maintenance_tab_session_inputs(
                loc_maint,
                close_location_meters=int(st.session_state.get(STREAMLIT_CLOSE_LOCATION_METERS_KEY)),
                incomplete_by_year=incomplete_maint,
                sex_notation_by_year=sex_notation_by_year,
            )
            sync_yearly_summary_session_inputs(checklist_payload)
            sync_country_tab_session_inputs(checklist_payload)

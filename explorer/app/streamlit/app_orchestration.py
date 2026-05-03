"""Orchestration phases for the Streamlit dashboard entrypoint (GitHub #200).

These functions split :func:`explorer.app.streamlit.app.main` into named phases.
**Execution order matters** for Streamlit (sidebar widgets, ``st.tabs``, spinner nesting).

Ordered flow:

1. :func:`bootstrap_streamlit_page` — ``set_page_config`` + Streamlit chrome theme CSS.
2. :func:`init_session_defaults_before_data_load` — taxonomy locale + country tab sort defaults.
3. :func:`coerce_session_upload_cache` — normalize cached upload tuple for the loader.
4. :func:`explorer.app.streamlit.app_landing_ui.load_dataframe_after_landing` — disk / upload /
   landing; may return ``None`` (caller exits).
5. :func:`bootstrap_session_after_csv_load` — run id, perf dataset context, settings YAML,
   table clamps, popup / filter caches.
6. :func:`explorer.app.streamlit.app_map_working_ui.render_map_sidebar_and_working_set` —
   sidebar + working dataframe (refs #131).
7. :func:`build_taxonomy_popup_assets` — cached taxonomy URL fn + popup preferences.
8. :func:`render_dashboard_shell` — title row, primary ``st.tabs``, compact tab CSS, prep spinner
   + Map tab (refs #130), then non-map tab fragments, then Settings.

Prep + Folium run **after** ``st.tabs`` are created so loading indicators stay aligned with the
tab row (refs #70, #130).
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import streamlit as st

from explorer.presentation.checklist_stats_display import COUNTRY_TAB_SORT_ALPHABETICAL
from explorer.core.explorer_paths import settings_yaml_path_for_source
from explorer.app.streamlit.app_caches import cached_species_url_fn
from explorer.app.streamlit.app_constants import (
    DEFAULT_TAXONOMY_LOCALE,
    EXPLORER_MAIN_SCRIPT_RUN_ID_KEY,
    FILTERED_BY_LOC_CACHE_KEY,
    POPUP_HTML_CACHE_KEY,
    REPO_ROOT,
    SETTINGS_BASELINE_KEY,
    SETTINGS_CONFIG_PATH_KEY,
    SETTINGS_CONFIG_SOURCE_KEY,
    SETTINGS_LOADED_FROM_KEY,
    SETTINGS_WARNED_KEY,
    SESSION_UPLOAD_CACHE_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
)
from explorer.app.streamlit.app_landing_ui import title_with_logo
from explorer.app.streamlit.app_prep_map_ui import render_prep_spinner_and_map_tab
from explorer.app.streamlit.app_settings_ui import render_settings_tab
from explorer.app.streamlit.app_settings_state import (
    apply_settings_payload_to_state,
    env_taxonomy_locale,
    init_and_clamp_streamlit_table_settings,
    load_settings_yaml_via_module,
    settings_state_payload,
)
from explorer.app.streamlit.checklist_stats_streamlit_html import run_checklist_stats_streamlit_fragment
from explorer.app.streamlit.country_stats_streamlit_html import run_country_tab_streamlit_fragment
from explorer.app.streamlit.maintenance_streamlit_html import run_maintenance_streamlit_tab_fragment
from explorer.app.streamlit.perf_instrumentation import perf_set_dataset_context, perf_span
from explorer.app.streamlit.rankings_streamlit_html import run_rankings_streamlit_tab_fragment
from explorer.app.streamlit.streamlit_theme import (
    inject_main_tab_panel_top_compact_css,
    inject_streamlit_chrome_theme_tokens_css,
)
from explorer.app.streamlit.streamlit_ui_constants import NOTEBOOK_MAIN_TAB_LABELS
from explorer.app.streamlit.yearly_summary_streamlit_html import run_yearly_summary_streamlit_fragment

if TYPE_CHECKING:
    from explorer.app.streamlit.app_map_working_ui import MapWorkingContext


@dataclass(frozen=True)
class TaxonomyPopupAssets:
    """Cached taxonomy lookup + popup display preferences for the map tab."""

    tax_locale_effective: str
    species_url_fn: Any
    popup_sort_order: Any
    popup_scroll_hint: Any
    mark_lifer: bool
    mark_last_seen: bool


def bootstrap_streamlit_page() -> None:
    st.set_page_config(page_title="Personal eBird Explorer (Streamlit)", layout="wide")
    inject_streamlit_chrome_theme_tokens_css()


def init_session_defaults_before_data_load() -> None:
    if STREAMLIT_TAXONOMY_LOCALE_KEY not in st.session_state:
        st.session_state[STREAMLIT_TAXONOMY_LOCALE_KEY] = (
            env_taxonomy_locale() or DEFAULT_TAXONOMY_LOCALE
        )
    if "streamlit_country_tab_sort" not in st.session_state:
        st.session_state.streamlit_country_tab_sort = COUNTRY_TAB_SORT_ALPHABETICAL


def coerce_session_upload_cache() -> Any:
    upload_cache = st.session_state.get(SESSION_UPLOAD_CACHE_KEY)
    if upload_cache is not None and not (
        isinstance(upload_cache, tuple) and len(upload_cache) == 2 and isinstance(upload_cache[0], bytes)
    ):
        return None
    return upload_cache


def bootstrap_session_after_csv_load(df_full: Any, *, source_label: str | None) -> None:
    st.session_state[EXPLORER_MAIN_SCRIPT_RUN_ID_KEY] = int(
        st.session_state.get(EXPLORER_MAIN_SCRIPT_RUN_ID_KEY, 0)
    ) + 1
    perf_set_dataset_context(df_full)

    st.session_state[SETTINGS_CONFIG_SOURCE_KEY] = source_label or ""
    settings_yaml_path = settings_yaml_path_for_source(REPO_ROOT, source_label or "")
    st.session_state[SETTINGS_CONFIG_PATH_KEY] = settings_yaml_path or ""
    if settings_yaml_path and st.session_state.get(SETTINGS_LOADED_FROM_KEY) != settings_yaml_path:
        cfg_data, cfg_warn = load_settings_yaml_via_module(settings_yaml_path)
        if cfg_warn and not st.session_state.get(SETTINGS_WARNED_KEY):
            st.warning(cfg_warn)
            st.session_state[SETTINGS_WARNED_KEY] = True
        apply_settings_payload_to_state(cfg_data)
        st.session_state[SETTINGS_LOADED_FROM_KEY] = settings_yaml_path
        st.session_state[SETTINGS_BASELINE_KEY] = settings_state_payload()

    init_and_clamp_streamlit_table_settings()
    if SETTINGS_BASELINE_KEY not in st.session_state:
        st.session_state[SETTINGS_BASELINE_KEY] = settings_state_payload()

    if POPUP_HTML_CACHE_KEY not in st.session_state:
        st.session_state[POPUP_HTML_CACHE_KEY] = {}
    if FILTERED_BY_LOC_CACHE_KEY not in st.session_state:
        st.session_state[FILTERED_BY_LOC_CACHE_KEY] = OrderedDict()


def build_taxonomy_popup_assets() -> TaxonomyPopupAssets:
    tax_locale_effective = (
        str(st.session_state.get(STREAMLIT_TAXONOMY_LOCALE_KEY, "")).strip()
        or DEFAULT_TAXONOMY_LOCALE
    )
    with perf_span("taxonomy.cached_species_url_fn"):
        species_url_fn = cached_species_url_fn(tax_locale_effective)
    return TaxonomyPopupAssets(
        tax_locale_effective=tax_locale_effective,
        species_url_fn=species_url_fn,
        popup_sort_order=st.session_state.streamlit_popup_sort_order,
        popup_scroll_hint=st.session_state.streamlit_popup_scroll_hint,
        mark_lifer=bool(st.session_state.streamlit_mark_lifer),
        mark_last_seen=bool(st.session_state.streamlit_mark_last_seen),
    )


def run_non_map_data_tab_fragments(
    tab_checklist: Any,
    tab_rankings: Any,
    tab_yearly: Any,
    tab_country: Any,
    tab_maint: Any,
) -> None:
    """Checklist, Rankings, Yearly, Country, Maintenance tabs (refs #118)."""
    with tab_checklist:
        run_checklist_stats_streamlit_fragment()

    with tab_rankings:
        run_rankings_streamlit_tab_fragment()

    with tab_yearly:
        run_yearly_summary_streamlit_fragment()

    with tab_country:
        run_country_tab_streamlit_fragment()

    with tab_maint:
        run_maintenance_streamlit_tab_fragment()


def render_dashboard_shell(
    *,
    df_full: Any,
    provenance: Any,
    source_label: str | None,
    data_abs_path: str | None,
    data_basename: str | None,
    mw: MapWorkingContext,
    tax: TaxonomyPopupAssets,
) -> None:
    title_with_logo()

    (
        tab_map,
        tab_checklist,
        tab_rankings,
        tab_yearly,
        tab_country,
        tab_maint,
        tab_settings,
    ) = st.tabs(NOTEBOOK_MAIN_TAB_LABELS)

    inject_main_tab_panel_top_compact_css()

    render_prep_spinner_and_map_tab(
        tab_map=tab_map,
        work_df=mw.work_df,
        df_full=df_full,
        provenance=provenance,
        tax_locale_effective=tax.tax_locale_effective,
        map_height=mw.map_height,
        map_style=mw.map_style,
        map_view_mode=mw.map_view_mode,
        is_lifer_view=mw.is_lifer_view,
        date_filter_banner=mw.date_filter_banner,
        species_pick_common=mw.species_pick_common,
        species_pick_sci=mw.species_pick_sci,
        family_name=mw.family_name,
        family_highlight_base=mw.family_highlight_base,
        family_colour_scheme=mw.family_colour_scheme,
        hide_non_matching_locations=mw.hide_non_matching_locations,
        popup_sort_order=tax.popup_sort_order,
        popup_scroll_hint=tax.popup_scroll_hint,
        mark_lifer=tax.mark_lifer,
        mark_last_seen=tax.mark_last_seen,
        species_url_fn=tax.species_url_fn,
    )

    run_non_map_data_tab_fragments(
        tab_checklist,
        tab_rankings,
        tab_yearly,
        tab_country,
        tab_maint,
    )

    with tab_settings:
        render_settings_tab(
            data_basename=data_basename,
            data_abs_path=data_abs_path,
            source_label=source_label,
        )

"""Streamlit session bootstrap before and after CSV load (GitHub #200, R13 split)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from explorer.app.streamlit.app_caches import cached_species_url_fn
from explorer.app.streamlit.app_constants import (
    DEFAULT_TAXONOMY_LOCALE,
    EXPLORER_MAIN_SCRIPT_RUN_ID_KEY,
    REPO_ROOT,
    SESSION_UPLOAD_CACHE_KEY,
    SETTINGS_BASELINE_KEY,
    SETTINGS_CONFIG_PATH_KEY,
    SETTINGS_CONFIG_SOURCE_KEY,
    SETTINGS_LOADED_FROM_KEY,
    SETTINGS_WARNED_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
)
from explorer.app.streamlit.app_settings_state import (
    apply_settings_payload_to_state,
    env_taxonomy_locale,
    init_and_clamp_streamlit_table_settings,
    load_settings_yaml_via_module,
    settings_state_payload,
)
from explorer.app.streamlit.perf_instrumentation import (
    perf_set_dataset_context,
    perf_span,
)
from explorer.app.streamlit.streamlit_theme import (
    inject_streamlit_chrome_theme_tokens_css,
)
from explorer.core.explorer_paths import settings_yaml_path_for_source
from explorer.presentation.checklist_stats_display import COUNTRY_TAB_SORT_ALPHABETICAL


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

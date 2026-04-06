"""Sidebar prep spinner (checklist / rankings / tab sync + map build) and Map tab Folium embed (refs #130).

The ``with tab_map`` / ``st_folium`` block stays nested inside the sidebar ``st.spinner`` so loading
indicators stay aligned with Streamlit’s spinner (refs #124). Partial ``@st.fragment`` reruns do not
use this path.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable

import streamlit as st

from explorer.app.streamlit.app_caches import (
    cached_checklist_stats_payload,
    cached_full_export_checklist_stats_payload,
    cached_sex_notation_by_year,
    full_location_data_for_maintenance,
    static_map_cache_key,
)
from explorer.app.streamlit.app_constants import (
    EBIRD_DATA_SIG_KEY,
    EXPLORER_MAP_HTML_BYTES_KEY,
    EXPORT_MAP_HTML_BTN_KEY,
    FOLIUM_MAP_MOUNT_NONCE_KEY,
    FOLIUM_STATIC_MAP_CACHE_KEY,
    STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
)
from explorer.app.streamlit.app_map_ui import (
    inject_map_folium_iframe_min_height_css,
    place_spinner_emoji_strip,
    sidebar_bottom_slot_end,
    sidebar_bottom_slot_start,
    sidebar_footer_links,
)
from explorer.app.streamlit.checklist_stats_streamlit_html import (
    sync_checklist_stats_tab_session_inputs,
)
from explorer.app.streamlit.country_stats_streamlit_html import sync_country_tab_session_inputs
from explorer.app.streamlit.maintenance_streamlit_html import sync_maintenance_tab_session_inputs
from explorer.app.streamlit.map_working import folium_map_to_html_bytes
from explorer.app.streamlit.rankings_streamlit_html import (
    build_rankings_tab_bundle,
    sync_rankings_tab_session_inputs,
)
from explorer.app.streamlit.streamlit_ui_constants import (
    CHECKLIST_STATS_SPINNER_TEXT,
    MAP_EXPORT_HTML_FILENAME,
)
from explorer.app.streamlit.yearly_summary_streamlit_html import sync_yearly_summary_session_inputs
from explorer.core.map_controller import build_species_overlay_map
from explorer.core.map_prep import data_signature_for_caches, prepare_all_locations_map_context
from explorer.core.settings_schema_defaults import MAP_CLUSTER_ALL_LOCATIONS_DEFAULT
from explorer.core.species_logic import base_species_for_lifer


def render_prep_spinner_and_map_tab(
    *,
    tab_map: Any,
    work_df: Any,
    df_full: Any,
    provenance: str | None,
    tax_locale_effective: str,
    map_height: int,
    map_style: str,
    map_view_mode: str,
    is_lifer_view: bool,
    date_filter_banner: str,
    species_pick_common: str | None,
    species_pick_sci: str,
    hide_non_matching_locations: bool,
    popup_sort_order: Any,
    popup_scroll_hint: Any,
    mark_lifer: bool,
    mark_last_seen: bool,
    species_url_fn: Callable[..., str],
) -> None:
    """Run checklist prep inside the sidebar spinner, then render Folium in the Map tab."""
    with st.sidebar:
        sidebar_bottom_slot_start()
        with st.spinner(CHECKLIST_STATS_SPINNER_TEXT):
            _spinner_emoji_placeholder = place_spinner_emoji_strip()
            checklist_payload = cached_checklist_stats_payload(work_df, tax_locale_effective)
            top_n = int(st.session_state.streamlit_rankings_top_n)
            hc_sort = str(st.session_state.streamlit_high_count_sort)
            hc_tb = str(st.session_state.streamlit_high_count_tie_break)
            if df_full is not None and not df_full.empty:
                maint_full_payload = cached_full_export_checklist_stats_payload(
                    df_full, top_n, hc_sort, hc_tb, tax_locale_effective
                )
                rankings_bundle = build_rankings_tab_bundle(
                    df_full,
                    country_sort=st.session_state.streamlit_country_tab_sort,
                    taxonomy_locale=tax_locale_effective,
                    high_count_sort=hc_sort,
                    high_count_tie_break=hc_tb,
                )
            else:
                maint_full_payload = None
                rankings_bundle = {}
            sex_notation_by_year: dict = (
                {} if df_full.empty else cached_sex_notation_by_year(df_full)
            )

            sync_checklist_stats_tab_session_inputs(checklist_payload)
            sync_rankings_tab_session_inputs(rankings_bundle)
            loc_maint = full_location_data_for_maintenance(df_full)
            incomplete_maint: dict = {}
            if maint_full_payload is not None:
                incomplete_maint = maint_full_payload.incomplete_by_year or {}
            sync_maintenance_tab_session_inputs(
                loc_maint,
                close_location_meters=int(st.session_state.streamlit_close_location_meters),
                incomplete_by_year=incomplete_maint,
                sex_notation_by_year=sex_notation_by_year,
            )
            sync_yearly_summary_session_inputs(checklist_payload)
            sync_country_tab_session_inputs(checklist_payload)

            prov_plain = provenance or ""
            sig = data_signature_for_caches(df_full, prov_plain)
            if st.session_state.get(EBIRD_DATA_SIG_KEY) != sig:
                st.session_state.ebird_data_sig = sig
                st.session_state.popup_html_cache = {}
                st.session_state.filtered_by_loc_cache = OrderedDict()
                st.session_state.pop(FOLIUM_STATIC_MAP_CACHE_KEY, None)

            map_warning_text: str | None = None
            map_for_folium = None
            folium_st_key: str | None = None
            try:
                ctx = prepare_all_locations_map_context(work_df, full_df=df_full)
            except ValueError as e:
                map_warning_text = str(e)
                st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
            else:
                overlay_common = (
                    (species_pick_common or "").strip() if map_view_mode == "species" else ""
                )
                overlay_sci = (species_pick_sci or "").strip() if map_view_mode == "species" else ""
                hide_nm = (
                    map_view_mode == "species"
                    and bool(overlay_sci)
                    and hide_non_matching_locations
                )
                _map_kw = {
                    **ctx,
                    "selected_species": overlay_sci,
                    "selected_common_name": overlay_common,
                    "map_style": map_style,
                    "popup_sort_order": popup_sort_order,
                    "popup_scroll_hint": popup_scroll_hint,
                    "lifer_color": st.session_state.streamlit_lifer_color,
                    "lifer_fill": st.session_state.streamlit_lifer_fill,
                    "last_seen_color": st.session_state.streamlit_last_seen_color,
                    "last_seen_fill": st.session_state.streamlit_last_seen_fill,
                    "species_color": st.session_state.streamlit_species_color,
                    "species_fill": st.session_state.streamlit_species_fill,
                    "default_color": st.session_state.streamlit_default_color,
                    "default_fill": st.session_state.streamlit_default_fill,
                    "mark_lifer": mark_lifer,
                    "mark_last_seen": mark_last_seen,
                    "cluster_all_locations": bool(
                        st.session_state.get(
                            STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                            MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
                        )
                    ),
                    "date_filter_status": "" if is_lifer_view else date_filter_banner,
                    "species_url_fn": species_url_fn,
                    "base_species_fn": base_species_for_lifer,
                    "taxonomy_locale": tax_locale_effective,
                    "popup_html_cache": st.session_state.popup_html_cache,
                    "filtered_by_loc_cache": st.session_state.filtered_by_loc_cache,
                    "map_view_mode": map_view_mode,
                    "hide_non_matching_locations": hide_nm,
                    "show_subspecies_lifers": bool(
                        st.session_state.get(STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY, False)
                    ),
                    "map_height_px": int(map_height),
                }
                _render_opts_sig = (
                    popup_sort_order,
                    popup_scroll_hint,
                    st.session_state.streamlit_lifer_color,
                    st.session_state.streamlit_lifer_fill,
                    st.session_state.streamlit_last_seen_color,
                    st.session_state.streamlit_last_seen_fill,
                    st.session_state.streamlit_species_color,
                    st.session_state.streamlit_species_fill,
                    st.session_state.streamlit_default_color,
                    st.session_state.streamlit_default_fill,
                    mark_lifer,
                    mark_last_seen,
                    bool(
                        st.session_state.get(
                            STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                            MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
                        )
                    ),
                    bool(st.session_state.get(STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY, False)),
                    int(map_height),
                )
                _species_selected = bool(overlay_sci)
                _cache_map_view_mode = map_view_mode
                if map_view_mode == "species" and not _species_selected:
                    _cache_map_view_mode = "all"
                _ck = static_map_cache_key(
                    work_df,
                    _cache_map_view_mode,
                    date_filter_banner,
                    map_style,
                    _render_opts_sig,
                    taxonomy_locale=tax_locale_effective,
                    species_selected_sci=overlay_sci if _species_selected else "",
                    species_selected_common=overlay_common if _species_selected else "",
                    hide_non_matching_locations=bool(hide_nm),
                )
                _use_static_cache = True
                _cached = st.session_state.get(FOLIUM_STATIC_MAP_CACHE_KEY)
                if (
                    isinstance(_cached, dict)
                    and _cached.get("key") == _ck
                    and _cached.get("map") is not None
                ):
                    result_map = _cached["map"]
                    result_warning = _cached.get("warning")
                else:
                    result = build_species_overlay_map(**_map_kw)
                    result_map = result.map
                    result_warning = result.warning
                    if _use_static_cache and result_map is not None:
                        st.session_state[FOLIUM_STATIC_MAP_CACHE_KEY] = {
                            "key": _ck,
                            "map": result_map,
                            "warning": result_warning,
                        }

                if result_warning:
                    map_warning_text = result_warning
                    st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                elif result_map is None:
                    map_warning_text = "Map could not be built."
                    st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                else:
                    st.session_state[EXPLORER_MAP_HTML_BYTES_KEY] = folium_map_to_html_bytes(result_map)
                    map_for_folium = result_map
                    folium_st_key = (
                        f"explorer_folium_{abs(hash(_ck))}_h{map_height}_mv{map_view_mode}_n"
                        f"{int(st.session_state.get(FOLIUM_MAP_MOUNT_NONCE_KEY, 0))}"
                    )

            with tab_map:
                if map_warning_text is not None:
                    st.warning(map_warning_text)
                elif map_for_folium is not None and folium_st_key is not None:
                    inject_map_folium_iframe_min_height_css(map_height)
                    try:
                        from streamlit_folium import st_folium
                    except ImportError:
                        st.error(
                            "Missing **streamlit-folium** (needed to embed the Folium map). "
                            "Locally: `pip install -r requirements.txt`. "
                            "**Streamlit Community Cloud:** set app **Python requirements** to "
                            "`requirements.txt` at the repo root."
                        )
                        st.stop()
                    st_folium(
                        map_for_folium,
                        use_container_width=True,
                        height=map_height,
                        # ``_ck`` coerces **Species** with no pick to ``all`` so we reuse one Folium build
                        # when the cache is valid. *map_view_mode* + *FOLIUM_MAP_MOUNT_NONCE_KEY* force a
                        # distinct streamlit-folium component identity when the sidebar layout changes
                        # (All↔Species); see invalidation block above.
                        key=folium_st_key,
                        returned_objects=[],
                        return_on_hover=False,
                    )

        _spinner_emoji_placeholder.empty()
        _has_map_export = bool(st.session_state.get(EXPLORER_MAP_HTML_BYTES_KEY))
        if _has_map_export:
            st.divider()
            _ex1, _ex2, _ex3 = st.columns([1, 3, 1])
            with _ex2:
                st.download_button(
                    "Export map HTML",
                    data=st.session_state[EXPLORER_MAP_HTML_BYTES_KEY],
                    file_name=MAP_EXPORT_HTML_FILENAME,
                    mime="text/html",
                    key=EXPORT_MAP_HTML_BTN_KEY,
                    help="Standalone HTML for the current map.",
                    use_container_width=True,
                )
        sidebar_footer_links(leading_divider=not _has_map_export)
        sidebar_bottom_slot_end()

"""Settings tab UI for the Streamlit app (refs #118).

Extracted from :mod:`explorer.app.streamlit.app` so ``main()`` stays orchestration-heavy
rather than embedding the full settings forms and captions.
"""

from __future__ import annotations

import streamlit as st

from explorer.presentation.checklist_stats_display import (
    COUNTRY_TAB_SORT_ALPHABETICAL,
    COUNTRY_TAB_SORT_LIFERS_WORLD,
    COUNTRY_TAB_SORT_TOTAL_SPECIES,
)
from explorer.core.settings_schema_defaults import (
    MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
    MAP_PIN_COLOUR_ALLOWLIST,
    MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT,
    MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
    MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
    TABLES_HIGH_COUNT_SORT_DEFAULT,
    TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT,
    TABLES_RANKINGS_TOP_N_DEFAULT,
    TABLES_RANKINGS_TOP_N_MAX,
    TABLES_RANKINGS_TOP_N_MIN,
    TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT,
    TABLES_RANKINGS_VISIBLE_ROWS_MAX,
    TABLES_RANKINGS_VISIBLE_ROWS_MIN,
    YEARLY_RECENT_COLUMN_COUNT_DEFAULT,
    YEARLY_RECENT_COLUMN_COUNT_MAX,
    YEARLY_RECENT_COLUMN_COUNT_MIN,
)
from explorer.app.streamlit.app_constants import (
    COUNTRY_SORT_LABELS,
    REPO_ROOT,
    SETTINGS_BASELINE_KEY,
    SETTINGS_CONFIG_PATH_KEY,
    SETTINGS_FLASH_RESET_KEY,
    SETTINGS_FLASH_SAVE_KEY,
    SETTINGS_PANEL_CSS,
    STREAMLIT_CLOSE_LOCATION_METERS_KEY,
    STREAMLIT_COUNTRY_TAB_SORT_KEY,
    STREAMLIT_DEFAULT_COLOR_KEY,
    STREAMLIT_DEFAULT_FILL_KEY,
    STREAMLIT_LIFER_COLOR_KEY,
    STREAMLIT_LIFER_FILL_KEY,
    STREAMLIT_LAST_SEEN_COLOR_KEY,
    STREAMLIT_LAST_SEEN_FILL_KEY,
    STREAMLIT_MAP_BASEMAP_APPLY_PENDING_KEY,
    STREAMLIT_MAP_BASEMAP_SAVED_KEY,
    STREAMLIT_MAP_BASEMAP_KEY,
    STREAMLIT_MAP_HEIGHT_PX_APPLY_PENDING_KEY,
    STREAMLIT_MAP_HEIGHT_PX_KEY,
    STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_SAVED_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY,
    STREAMLIT_MARK_LAST_SEEN_KEY,
    STREAMLIT_MARK_LIFER_KEY,
    STREAMLIT_POPUP_SCROLL_HINT_KEY,
    STREAMLIT_POPUP_SORT_ORDER_KEY,
    STREAMLIT_RANKINGS_TOP_N_KEY,
    STREAMLIT_RANKINGS_VISIBLE_ROWS_KEY,
    STREAMLIT_HIGH_COUNT_SORT_KEY,
    STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY,
    STREAMLIT_SAVE_SETTINGS_BTN_KEY,
    STREAMLIT_RESET_SETTINGS_BTN_KEY,
    STREAMLIT_SPECIES_COLOR_KEY,
    STREAMLIT_SPECIES_FILL_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
    STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY,
)
from explorer.app.streamlit.app_settings_state import (
    apply_settings_payload_to_state,
    init_and_clamp_streamlit_table_settings,
    settings_config_module_available,
    settings_data_path_html,
    settings_defaults_payload,
    settings_persistence_flash_banners,
    settings_state_payload,
    settings_taxonomy_help_markdown,
    write_settings_yaml_via_module,
)
from explorer.app.streamlit.defaults import (
    MAP_BASEMAP_DEFAULT,
    MAP_BASEMAP_LABELS,
    MAP_BASEMAP_OPTIONS,
    MAP_HEIGHT_PX_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
)


def render_settings_tab(
    *,
    data_basename: str | None,
    data_abs_path: str | None,
    source_label: str | None,
) -> None:
    """Render the **Settings** tab: persistence, map batch form, tables form, taxonomy, data path."""
    st.markdown(SETTINGS_PANEL_CSS, unsafe_allow_html=True)
    with st.container(key="ebird_settings_panel"):
        settings_yaml_path = st.session_state.get(SETTINGS_CONFIG_PATH_KEY, "") or ""
        settings_module_ready = settings_config_module_available()
        can_save_settings = bool(settings_yaml_path) and settings_module_ready

        if can_save_settings:
            b1, b2 = st.columns(2)
            with b1:
                if st.button(
                    "Save settings",
                    key=STREAMLIT_SAVE_SETTINGS_BTN_KEY,
                    width="stretch",
                ):
                    ok, err = write_settings_yaml_via_module(
                        settings_yaml_path, settings_state_payload()
                    )
                    if ok:
                        # Keep sidebar runtime controls in sync only after Save.
                        st.session_state[STREAMLIT_MAP_BASEMAP_APPLY_PENDING_KEY] = "__default__"
                        st.session_state[STREAMLIT_MAP_HEIGHT_PX_APPLY_PENDING_KEY] = int(
                            st.session_state.get(
                                STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY,
                                st.session_state.get(STREAMLIT_MAP_HEIGHT_PX_KEY, MAP_HEIGHT_PX_DEFAULT),
                            )
                        )
                        st.session_state[STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY] = bool(
                            st.session_state.get(
                                STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_SAVED_KEY,
                                st.session_state.get(STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY, True),
                            )
                        )
                        st.session_state[SETTINGS_BASELINE_KEY] = settings_state_payload()
                        st.session_state[SETTINGS_FLASH_SAVE_KEY] = True
                        st.rerun()
                    else:
                        st.error(err or "Failed to save settings.")
            with b2:
                if st.button(
                    "Reset to defaults",
                    key=STREAMLIT_RESET_SETTINGS_BTN_KEY,
                    width="stretch",
                ):
                    apply_settings_payload_to_state(settings_defaults_payload())
                    init_and_clamp_streamlit_table_settings()
                    st.session_state[SETTINGS_FLASH_RESET_KEY] = True

            settings_persistence_flash_banners()
            st.caption(
                "Use **Apply map settings** and **Apply table settings** before **Save settings**. "
                "Taxonomy still applies immediately in-session. Save writes your current applied preferences "
                "to your configuration file."
            )
            st.caption(f"Configuration file: {settings_yaml_path}")

        st.divider()
        st.subheader("Map display")
        st.caption(
            "Popup behaviour, mark toggles, default clustering for the All locations map (saved when you "
            "**Save settings**), and pin colours are batched here; click **Apply map settings** for one rerun. "
            "For a quick on/off without changing your saved default, use the **Map** sidebar toggle."
        )
        _popup_sort_opts = ["ascending", "descending"]
        _popup_scroll_opts = ["shading", "chevron", "both"]
        _popup_sort_cur = str(st.session_state.get(STREAMLIT_POPUP_SORT_ORDER_KEY, "ascending"))
        if _popup_sort_cur not in _popup_sort_opts:
            _popup_sort_cur = "ascending"
        _popup_scroll_cur = str(st.session_state.get(STREAMLIT_POPUP_SCROLL_HINT_KEY, "shading"))
        if _popup_scroll_cur not in _popup_scroll_opts:
            _popup_scroll_cur = "shading"

        def _pin_idx(key: str) -> int:
            cur = st.session_state.get(key, MAP_PIN_COLOUR_ALLOWLIST[0])
            return MAP_PIN_COLOUR_ALLOWLIST.index(cur) if cur in MAP_PIN_COLOUR_ALLOWLIST else 0

        with st.form("ebird_map_settings_batch"):
            basemap_default_w = st.selectbox(
                "Basemap — default",
                options=list(MAP_BASEMAP_OPTIONS),
                format_func=lambda k: MAP_BASEMAP_LABELS.get(k, k),
                index=list(MAP_BASEMAP_OPTIONS).index(
                    st.session_state.get(STREAMLIT_MAP_BASEMAP_SAVED_KEY, MAP_BASEMAP_DEFAULT)
                    if st.session_state.get(STREAMLIT_MAP_BASEMAP_SAVED_KEY, MAP_BASEMAP_DEFAULT)
                    in MAP_BASEMAP_OPTIONS
                    else MAP_BASEMAP_DEFAULT
                ),
                help=(
                    "Your default map background. The Map sidebar can temporarily override this for the current session."
                ),
            )
            mark_lifer_w = st.toggle(
                "Mark lifer",
                value=bool(st.session_state.get(STREAMLIT_MARK_LIFER_KEY, True)),
            )
            mark_last_seen_w = st.toggle(
                "Mark last-seen",
                value=bool(st.session_state.get(STREAMLIT_MARK_LAST_SEEN_KEY, True)),
            )
            cluster_all_locations_w = st.toggle(
                "Group nearby pins — default (All locations map)",
                value=bool(
                    st.session_state.get(
                        STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_SAVED_KEY,
                        MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
                    )
                ),
                help=(
                    "When on, nearby checklist locations are combined into clusters at low zoom; "
                    "zoom in or click a cluster to see individual pins. "
                    "Species and lifer maps always show one pin per location. "
                    "This value is written to your config when you **Save settings** and used on the next load. "
                    "**Apply map settings** also updates the map now. Use the **Map** sidebar for a session-only toggle."
                ),
            )
            map_height_default_w = st.slider(
                "Map height (px)",
                min_value=MAP_HEIGHT_PX_MIN,
                max_value=MAP_HEIGHT_PX_MAX,
                value=int(
                    st.session_state.get(STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY, MAP_HEIGHT_PX_DEFAULT)
                ),
                step=MAP_HEIGHT_PX_STEP,
                help=(
                    "Saved default map height. The Map sidebar slider remains a quick session-only override."
                ),
            )
            popup_sort_w = st.selectbox(
                "Popup sort order",
                options=_popup_sort_opts,
                index=_popup_sort_opts.index(_popup_sort_cur),
            )
            popup_scroll_w = st.selectbox(
                "Popup scroll hint",
                options=_popup_scroll_opts,
                index=_popup_scroll_opts.index(_popup_scroll_cur),
            )
            st.caption("Pin colors")
            c1, c2 = st.columns(2)
            with c1:
                default_edge_w = st.selectbox(
                    "Default edge",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    index=_pin_idx(STREAMLIT_DEFAULT_COLOR_KEY),
                )
                species_edge_w = st.selectbox(
                    "Species edge",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    index=_pin_idx(STREAMLIT_SPECIES_COLOR_KEY),
                )
                lifer_edge_w = st.selectbox(
                    "Lifer edge",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    index=_pin_idx(STREAMLIT_LIFER_COLOR_KEY),
                )
                last_seen_edge_w = st.selectbox(
                    "Last-seen edge",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    index=_pin_idx(STREAMLIT_LAST_SEEN_COLOR_KEY),
                )
            with c2:
                default_fill_w = st.selectbox(
                    "Default fill",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    index=_pin_idx(STREAMLIT_DEFAULT_FILL_KEY),
                )
                species_fill_w = st.selectbox(
                    "Species fill",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    index=_pin_idx(STREAMLIT_SPECIES_FILL_KEY),
                )
                lifer_fill_w = st.selectbox(
                    "Lifer fill",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    index=_pin_idx(STREAMLIT_LIFER_FILL_KEY),
                )
                last_seen_fill_w = st.selectbox(
                    "Last-seen fill",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    index=_pin_idx(STREAMLIT_LAST_SEEN_FILL_KEY),
                )
            apply_map = st.form_submit_button("Apply map settings", width="stretch")

        if apply_map:
            st.session_state[STREAMLIT_MAP_BASEMAP_SAVED_KEY] = str(basemap_default_w)
            st.session_state[STREAMLIT_MAP_BASEMAP_APPLY_PENDING_KEY] = "__default__"
            st.session_state[STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY] = int(map_height_default_w)
            st.session_state[STREAMLIT_MAP_HEIGHT_PX_APPLY_PENDING_KEY] = int(map_height_default_w)
            st.session_state[STREAMLIT_MARK_LIFER_KEY] = bool(mark_lifer_w)
            st.session_state[STREAMLIT_MARK_LAST_SEEN_KEY] = bool(mark_last_seen_w)
            _cl = bool(cluster_all_locations_w)
            st.session_state[STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_SAVED_KEY] = _cl
            st.session_state[STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY] = _cl
            st.session_state[STREAMLIT_POPUP_SORT_ORDER_KEY] = popup_sort_w
            st.session_state[STREAMLIT_POPUP_SCROLL_HINT_KEY] = popup_scroll_w
            st.session_state[STREAMLIT_DEFAULT_COLOR_KEY] = default_edge_w
            st.session_state[STREAMLIT_SPECIES_COLOR_KEY] = species_edge_w
            st.session_state[STREAMLIT_LIFER_COLOR_KEY] = lifer_edge_w
            st.session_state[STREAMLIT_LAST_SEEN_COLOR_KEY] = last_seen_edge_w
            st.session_state[STREAMLIT_DEFAULT_FILL_KEY] = default_fill_w
            st.session_state[STREAMLIT_SPECIES_FILL_KEY] = species_fill_w
            st.session_state[STREAMLIT_LIFER_FILL_KEY] = lifer_fill_w
            st.session_state[STREAMLIT_LAST_SEEN_FILL_KEY] = last_seen_fill_w
            init_and_clamp_streamlit_table_settings()
            st.rerun()

        st.divider()
        st.subheader("Tables & Lists")
        st.caption(
            "Rankings, yearly column window, country ordering, high-count behaviour, and maintenance search radius — "
            "click **Apply table settings** for one rerun."
        )
        _country_sort_opts = [
            COUNTRY_TAB_SORT_ALPHABETICAL,
            COUNTRY_TAB_SORT_LIFERS_WORLD,
            COUNTRY_TAB_SORT_TOTAL_SPECIES,
        ]
        _cur_country = st.session_state.get(
            STREAMLIT_COUNTRY_TAB_SORT_KEY, COUNTRY_TAB_SORT_ALPHABETICAL
        )
        _idx_country = (
            _country_sort_opts.index(_cur_country)
            if _cur_country in _country_sort_opts
            else 0
        )
        _hc_sort_opts = ["total_count", "alphabetical"]
        _cur_hc = st.session_state.get(STREAMLIT_HIGH_COUNT_SORT_KEY, TABLES_HIGH_COUNT_SORT_DEFAULT)
        if _cur_hc not in _hc_sort_opts:
            _cur_hc = TABLES_HIGH_COUNT_SORT_DEFAULT
        _idx_hc = _hc_sort_opts.index(_cur_hc)
        _hc_tb_opts = ["last", "first"]
        _cur_tb = st.session_state.get(
            STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY, TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT
        )
        if _cur_tb not in _hc_tb_opts:
            _cur_tb = TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT
        _idx_tb = _hc_tb_opts.index(_cur_tb)

        with st.form("ebird_table_settings_batch"):
            rn = st.slider(
                "Ranking tables: number of results",
                min_value=TABLES_RANKINGS_TOP_N_MIN,
                max_value=TABLES_RANKINGS_TOP_N_MAX,
                value=int(
                    st.session_state.get(STREAMLIT_RANKINGS_TOP_N_KEY, TABLES_RANKINGS_TOP_N_DEFAULT)
                ),
                step=1,
            )
            vr = st.slider(
                "Ranking tables: visible rows",
                min_value=TABLES_RANKINGS_VISIBLE_ROWS_MIN,
                max_value=TABLES_RANKINGS_VISIBLE_ROWS_MAX,
                value=int(
                    st.session_state.get(
                        STREAMLIT_RANKINGS_VISIBLE_ROWS_KEY, TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT
                    )
                ),
                step=1,
            )
            yc = st.slider(
                "Yearly tables: recent year columns",
                min_value=YEARLY_RECENT_COLUMN_COUNT_MIN,
                max_value=YEARLY_RECENT_COLUMN_COUNT_MAX,
                value=int(
                    st.session_state.get(
                        STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY, YEARLY_RECENT_COLUMN_COUNT_DEFAULT
                    )
                ),
                step=1,
            )
            co = st.selectbox(
                "Country ordering",
                options=_country_sort_opts,
                format_func=lambda k: COUNTRY_SORT_LABELS[k],
                index=_idx_country,
            )
            hc_sort_w = st.selectbox(
                "High count ordering",
                options=_hc_sort_opts,
                format_func=lambda x: (
                    "By total count (high to low)" if x == "total_count" else "Alphabetical (species)"
                ),
                index=_idx_hc,
            )
            hc_tb_w = st.selectbox(
                "High count tie winner",
                options=_hc_tb_opts,
                format_func=lambda x: (
                    "Most recent checklist" if x == "last" else "Earliest checklist"
                ),
                index=_idx_tb,
                help=(
                    "For species with multiple checklists at the same high count, choose which checklist row is shown."
                ),
            )
            cl = st.slider(
                "Close location (m)",
                min_value=MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
                max_value=MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
                value=int(
                    st.session_state.get(
                        STREAMLIT_CLOSE_LOCATION_METERS_KEY, MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT
                    )
                ),
                step=1,
                help=(
                    "Locations within this distance (metres), excluding exact duplicate coordinates, "
                    "are listed under **Maintenance → Location Maintenance → Close locations**."
                ),
            )
            apply_tables = st.form_submit_button("Apply table settings", width="stretch")

        if apply_tables:
            st.session_state[STREAMLIT_RANKINGS_TOP_N_KEY] = rn
            st.session_state[STREAMLIT_RANKINGS_VISIBLE_ROWS_KEY] = vr
            st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = yc
            st.session_state[STREAMLIT_COUNTRY_TAB_SORT_KEY] = co
            st.session_state[STREAMLIT_HIGH_COUNT_SORT_KEY] = hc_sort_w
            st.session_state[STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY] = hc_tb_w
            st.session_state[STREAMLIT_CLOSE_LOCATION_METERS_KEY] = cl
            init_and_clamp_streamlit_table_settings()
            st.rerun()

        st.divider()
        st.subheader("Taxonomy")
        st.text_input(
            "Taxonomy locale",
            key=STREAMLIT_TAXONOMY_LOCALE_KEY,
        )
        st.caption(settings_taxonomy_help_markdown())
        st.divider()
        st.subheader("Data & path")
        st.caption("Read-only details for this session (useful when troubleshooting).")
        st.markdown(
            settings_data_path_html(
                data_basename=data_basename,
                data_abs_path=data_abs_path,
                source_label=source_label,
                repo_root=REPO_ROOT,
            ),
            unsafe_allow_html=True,
        )

"""
Personal eBird Explorer — Streamlit prototype (Folium map + notebook-style popups).

Planning and phased migration notes: https://github.com/jimchurches/myebirdstuff/issues/70 (refs #70).

Run locally from repo root::

    pip install -r requirements-streamlit.txt
    streamlit run streamlit_app/app.py

Disk resolution when no file is uploaded: ``scripts/config_secret.py`` and
``scripts/config.py`` (``DATA_FOLDER``), then the **process working directory**
(where you ran ``streamlit run``). See ``streamlit_app/README.md`` — *Data loading*.

Streamlit Cloud: CSV upload on the **landing** main area when disk resolution finds no file; session
state keeps upload bytes for reruns (no data picker on the dashboard). After a successful pick we
``st.rerun()`` so the next run loads from cache and **does not** emit landing widgets (title/uploader)
in the same pass as the dashboard — otherwise Streamlit’s top-to-bottom execution leaves landing + tabs
on screen together. If Streamlit Cloud still shows a stray upload blurb under tabs, treat as a
separate delta/orphan issue (e.g. container boundaries, Streamlit version); same-run load traded that
for a worse duplicate layout locally.

**No-data landing:** No disk file and no cached upload → title, copy, uploader in the main column.
Disk path takes precedence over a stale session upload when both exist.

**Taxonomy:** After CSV load, the app fetches the eBird taxonomy once per session (cached) so species
names in popups can link to eBird species pages. Default locale is **en_AU**; override with
``STREAMLIT_EBIRD_TAXONOMY_LOCALE`` / ``EBIRD_TAXONOMY_LOCALE`` or **Settings → Taxonomy**.
Streamlit does not expose the browser language to Python.

**Checklist Statistics:** Shared HTML sections (nested ``st.tabs`` + formatted tables from
``checklist_stats_streamlit_tab_sections_html``). ``cached_checklist_stats_payload`` runs **once** immediately
under the main tab bar (inside ``st.spinner("Doing interesting things with your eBird data...")``) so the loading message shows
no matter which tab is selected (refs #70).

**Country:** Per-country yearly table uses the same ``CHECKLIST_STATS_*`` HTML/CSS as Checklist Statistics
(``country_stats_streamlit_html``). The tab runs inside ``@st.fragment`` so changing the country selectbox
triggers a **partial rerun** (not the whole map/checklist pipeline) (refs #75).

**Maintenance:** Location duplicates / close locations, incomplete checklists, and sex-notation scan use
``maintenance_streamlit_html`` (nested tabs + expanders + shared HTML builders). Incomplete lists and sex
notation use the **full** export (``df_full``), not the date-filtered working set. **Close location (m)** is
configurable under **Settings → Maintenance** (refs #79).

**Rankings & lists:** ``rankings_streamlit_html`` — nested **Top Lists** / **Interesting Lists** tabs,
expanders per list, HTML from ``format_checklist_stats_bundle`` on ``df_full``. **Top N** and **visible rows**
are configured under **Settings → Tables & lists** (refs `#81`).

**Yearly Summary:** ``yearly_summary_streamlit_html`` — nested **All** / **Travelling** / **Stationary** tabs inside
``@st.fragment``; ``st.toggle`` switches recent vs full year columns when count exceeds **Settings → Yearly tables:
recent year columns** (default 10). ``sync_yearly_summary_session_inputs`` + ``run_yearly_summary_streamlit_fragment``
match the Country tab fragment pattern (refs #85).

**Main tabs + sidebar:** All tab bodies run each rerun (instant tab switching), with one always-on sidebar that
contains map controls plus footer links (refs #70). Settings sliders use a keyed container with
``max-width: min(100%, 40rem)`` on wide viewports.
"""

from __future__ import annotations

import os
import sys
from collections import OrderedDict

import pandas as pd
import streamlit as st

# Repo root on sys.path so ``import streamlit_app...`` works (refs #90).
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_APP_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from personal_ebird_explorer.checklist_stats_display import (  # noqa: E402
    COUNTRY_TAB_SORT_ALPHABETICAL,
    COUNTRY_TAB_SORT_LIFERS_WORLD,
    COUNTRY_TAB_SORT_TOTAL_SPECIES,
)
from personal_ebird_explorer.explorer_paths import settings_yaml_path_for_source  # noqa: E402
from personal_ebird_explorer.map_controller import build_species_overlay_map  # noqa: E402
from personal_ebird_explorer.species_search import build_ram_species_whoosh_index  # noqa: E402
from personal_ebird_explorer.species_logic import base_species_for_lifer  # noqa: E402
from personal_ebird_explorer.streamlit_map_prep import (  # noqa: E402
    data_signature_for_caches,
    prepare_all_locations_map_context,
)
from streamlit_app.app_caches import (  # noqa: E402
    cached_checklist_stats_payload,
    cached_sex_notation_by_year,
    cached_species_url_fn,
    full_location_data_for_maintenance,
    static_map_cache_key,
)
from streamlit_app.app_constants import (  # noqa: E402
    COUNTRY_SORT_LABELS,
    EBIRD_DATA_SIG_KEY,
    EBIRD_LANDING_CSV_UPLOADER_KEY,
    EBIRD_LANDING_MAIN_CONTAINER_KEY,
    EXPLORER_MAP_HTML_BYTES_KEY,
    DEFAULT_TAXONOMY_LOCALE,
    FOLIUM_STATIC_MAP_CACHE_KEY,
    MAP_VIEW_LABEL_TO_MODE,
    EXPORT_MAP_HTML_BTN_KEY,
    PERSIST_MAP_DATE_FILTER_KEY,
    PERSIST_MAP_DATE_RANGE_KEY,
    PERSIST_SPECIES_COMMON_KEY,
    PERSIST_SPECIES_SCI_KEY,
    SESSION_PREV_MAP_VIEW_KEY,
    SESSION_SPECIES_IX_KEY,
    SESSION_SPECIES_IX_SIG_KEY,
    SESSION_SPECIES_PICK_KEY,
    SESSION_SPECIES_SEARCH_KEY,
    SESSION_SPECIES_WS_KEY,
    SESSION_UPLOAD_CACHE_KEY,
    SETTINGS_BASELINE_KEY,
    SETTINGS_CONFIG_PATH_KEY,
    SETTINGS_CONFIG_SOURCE_KEY,
    SETTINGS_FLASH_RESET_KEY,
    SETTINGS_FLASH_SAVE_KEY,
    SETTINGS_LOADED_FROM_KEY,
    SETTINGS_PANEL_CSS,
    SETTINGS_WARNED_KEY,
    REPO_ROOT,
    STREAMLIT_CLOSE_LOCATION_METERS_KEY,
    STREAMLIT_COUNTRY_TAB_SORT_KEY,
    STREAMLIT_DEFAULT_COLOR_KEY,
    STREAMLIT_DEFAULT_FILL_KEY,
    STREAMLIT_COUNTRY_TAB_COUNTRY_KEY,
    STREAMLIT_LIFER_COLOR_KEY,
    STREAMLIT_LIFER_FILL_KEY,
    STREAMLIT_LAST_SEEN_COLOR_KEY,
    STREAMLIT_LAST_SEEN_FILL_KEY,
    STREAMLIT_MAP_BASEMAP_KEY,
    STREAMLIT_MAP_DATE_FILTER_KEY,
    STREAMLIT_MAP_DATE_RANGE_KEY,
    STREAMLIT_MAP_HEIGHT_PX_KEY,
    STREAMLIT_MAP_VIEW_LABEL_KEY,
    STREAMLIT_MARK_LAST_SEEN_KEY,
    STREAMLIT_MARK_LIFER_KEY,
    STREAMLIT_POPUP_SCROLL_HINT_KEY,
    STREAMLIT_POPUP_SORT_ORDER_KEY,
    STREAMLIT_RANKINGS_TOP_N_KEY,
    STREAMLIT_RANKINGS_VISIBLE_ROWS_KEY,
    STREAMLIT_SAVE_SETTINGS_BTN_KEY,
    STREAMLIT_RESET_SETTINGS_BTN_KEY,
    STREAMLIT_SPECIES_COLOR_KEY,
    STREAMLIT_SPECIES_FILL_KEY,
    STREAMLIT_SPECIES_HIDE_ONLY_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
    STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY,
)
from streamlit_app.app_data_loading import load_dataframe  # noqa: E402
from streamlit_app.app_map_ui import (  # noqa: E402
    ensure_streamlit_map_basemap_height_keys,
    inject_spinner_theme_css,
    sidebar_footer_links,
    species_searchbox_fragment,
)
from streamlit_app.app_settings_state import (  # noqa: E402
    apply_settings_payload_to_state,
    env_taxonomy_locale,
    init_and_clamp_streamlit_table_settings,
    load_settings_yaml_via_module,
    settings_config_module_available,
    settings_data_path_html,
    settings_defaults_payload,
    settings_persistence_flash_banners,
    settings_state_payload,
    settings_taxonomy_help_html,
    write_settings_yaml_via_module,
)
from streamlit_app.checklist_stats_streamlit_html import render_checklist_stats_streamlit_html  # noqa: E402
from streamlit_app.country_stats_streamlit_html import (  # noqa: E402
    run_country_tab_streamlit_fragment,
    sync_country_tab_session_inputs,
)
from streamlit_app.defaults import (  # noqa: E402
    CHECKLIST_STATS_SPINNER_MESSAGE,
    MAP_BASEMAP_OPTIONS,
    MAP_DATE_FILTER_DEFAULT,
    MAP_EXPORT_HTML_FILENAME,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
    MAP_VIEW_LABELS,
    MAP_PIN_COLOUR_ALLOWLIST,
    NOTEBOOK_MAIN_TAB_LABELS,
    SPECIES_SEARCH_CAPTION,
    TABLES_RANKINGS_TOP_N_MAX,
    TABLES_RANKINGS_TOP_N_MIN,
    TABLES_RANKINGS_VISIBLE_ROWS_MAX,
    TABLES_RANKINGS_VISIBLE_ROWS_MIN,
    YEARLY_RECENT_COLUMN_COUNT_MAX,
    YEARLY_RECENT_COLUMN_COUNT_MIN,
    MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
    MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
)
from streamlit_app.maintenance_streamlit_html import render_maintenance_streamlit_tab  # noqa: E402
from streamlit_app.map_working import (  # noqa: E402
    date_inception_to_today_default,
    folium_map_to_html_bytes,
    streamlit_working_set_and_status,
)
from streamlit_app.rankings_streamlit_html import render_rankings_streamlit_tab  # noqa: E402
from streamlit_app.yearly_summary_streamlit_html import (  # noqa: E402
    run_yearly_summary_streamlit_fragment,
    sync_yearly_summary_session_inputs,
)

def main() -> None:
    st.set_page_config(page_title="Personal eBird Explorer (Streamlit)", layout="wide")

    if "streamlit_taxonomy_locale" not in st.session_state:
        st.session_state.streamlit_taxonomy_locale = env_taxonomy_locale() or DEFAULT_TAXONOMY_LOCALE
    if "streamlit_country_tab_sort" not in st.session_state:
        st.session_state.streamlit_country_tab_sort = COUNTRY_TAB_SORT_ALPHABETICAL

    upload_cache = st.session_state.get(SESSION_UPLOAD_CACHE_KEY)
    if upload_cache is not None and not (
        isinstance(upload_cache, tuple) and len(upload_cache) == 2 and isinstance(upload_cache[0], bytes)
    ):
        upload_cache = None

    df_full, provenance, source_label, data_abs_path, data_basename = load_dataframe(
        uploaded=None, upload_cache=upload_cache
    )

    if df_full is not None and provenance and "Disk:" in provenance:
        # Drop stale session upload when disk resolution wins (local path after a prior Cloud upload).
        st.session_state.pop(SESSION_UPLOAD_CACHE_KEY, None)

    if df_full is None:
        # Keyed container: on the post-upload rerun this block is skipped entirely, so Cloud/Streamlit
        # can drop the whole landing subtree instead of leaving orphan markdown under tabs.
        with st.container(key=EBIRD_LANDING_MAIN_CONTAINER_KEY):
            st.title("Personal eBird Explorer")
            st.subheader("Streamlit prototype")
            st.markdown("Upload your **My eBird Data** CSV to open the map and tabs.")
            uploaded = st.file_uploader(
                "eBird export (CSV)",
                type=["csv"],
                key=EBIRD_LANDING_CSV_UPLOADER_KEY,
                help="Official eBird full data export (CSV).",
            )
            if uploaded is not None:
                df_full, provenance, source_label, data_abs_path, data_basename = load_dataframe(
                    uploaded=uploaded, upload_cache=None
                )
                if df_full is not None:
                    st.session_state[SESSION_UPLOAD_CACHE_KEY] = (uploaded.getvalue(), uploaded.name)
                    # Landing widgets already ran above in this run; rerun loads from cache and skips this block.
                    st.rerun()

            if df_full is None:
                st.markdown(
                    """
**From eBird**

1. Sign in: [Download My Data](https://ebird.org/downloadMyData)
2. Under **My eBird Observations**, use **Request My Observations**.
3. A link to your data will be sent to your email address (often a few minutes; sometimes longer).
4. Open the email, download the **.zip** and unzip it.
5. Upload the CSV here (in English the file name should be **MyEBirdData.csv**).
                    """
                )
                st.caption(
                    "Species links default to **en_AU**; change locale under **Settings → Taxonomy** after load. "
                    "Data still loads if names don’t match.\n\n"
                    "This page is skipped when a CSV is already found on disk (local config path). "
                    "Support for local files works when Streamlit is running locally; see the code repo for more information. "
                    "Proper instructions will appear here in future releases."
                )
        sidebar_footer_links()
        if df_full is None:
            return

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

    if "popup_html_cache" not in st.session_state:
        st.session_state.popup_html_cache = {}
    if "filtered_by_loc_cache" not in st.session_state:
        st.session_state.filtered_by_loc_cache = OrderedDict()

    ensure_streamlit_map_basemap_height_keys()

    with st.sidebar:
        st.header("Map")

        map_view_label = st.selectbox(
            "Map view",
            list(MAP_VIEW_LABELS),
            key=STREAMLIT_MAP_VIEW_LABEL_KEY,
        )
        map_view_mode = MAP_VIEW_LABEL_TO_MODE[map_view_label]
        is_lifer_view = map_view_mode == "lifers"

        st.markdown("**Date**")
        if is_lifer_view:
            st.caption("Lifer locations is not date-filtered.")
            if st.session_state.get(PERSIST_MAP_DATE_FILTER_KEY, MAP_DATE_FILTER_DEFAULT):
                st.caption("Your date filter is preserved for other map views.")
            date_filter_on_effective = False
            date_range_sel: tuple | None = None
        else:
            # Restore widget keys after Lifer view (those widgets were not rendered, keys may be missing).
            if STREAMLIT_MAP_DATE_FILTER_KEY not in st.session_state:
                st.session_state.streamlit_map_date_filter = bool(
                    st.session_state.get(PERSIST_MAP_DATE_FILTER_KEY, MAP_DATE_FILTER_DEFAULT)
                )
            if st.session_state.get(STREAMLIT_MAP_DATE_FILTER_KEY, False):
                if STREAMLIT_MAP_DATE_RANGE_KEY not in st.session_state:
                    pr = st.session_state.get(PERSIST_MAP_DATE_RANGE_KEY)
                    if isinstance(pr, tuple) and len(pr) == 2:
                        st.session_state.streamlit_map_date_range = pr
                    else:
                        a, b = date_inception_to_today_default(df_full)
                        st.session_state.streamlit_map_date_range = (a, b)

            date_filter_on_effective = st.toggle(
                "Date filter",
                key=STREAMLIT_MAP_DATE_FILTER_KEY,
                help="Turn on to limit the map and checklist stats to a date range.",
            )
            if not date_filter_on_effective:
                date_range_sel = None
            else:
                d_inception, today = date_inception_to_today_default(df_full)
                if STREAMLIT_MAP_DATE_RANGE_KEY not in st.session_state:
                    st.session_state.streamlit_map_date_range = (d_inception, today)
                rng = st.session_state["streamlit_map_date_range"]
                if not isinstance(rng, tuple) or len(rng) != 2:
                    st.session_state.streamlit_map_date_range = (d_inception, today)
                else:
                    r0 = max(min(rng[0], today), d_inception)
                    r1 = max(min(rng[1], today), d_inception)
                    rng_val = (r0, r1) if r0 <= r1 else (r1, r0)
                    if rng_val != rng:
                        st.session_state.streamlit_map_date_range = rng_val
                dr = st.date_input(
                    "Date range",
                    min_value=d_inception,
                    max_value=today,
                    key=STREAMLIT_MAP_DATE_RANGE_KEY,
                )
                if isinstance(dr, tuple) and len(dr) == 2:
                    date_range_sel = (dr[0], dr[1])
                else:
                    date_range_sel = (d_inception, today)

            st.session_state[PERSIST_MAP_DATE_FILTER_KEY] = date_filter_on_effective
            if date_filter_on_effective and date_range_sel is not None:
                st.session_state[PERSIST_MAP_DATE_RANGE_KEY] = date_range_sel

    ws, date_filter_banner = streamlit_working_set_and_status(
        df_full,
        map_view_mode=map_view_mode,
        date_filter_on=date_filter_on_effective,
        date_range=date_range_sel,
        map_caches=(st.session_state.popup_html_cache, st.session_state.filtered_by_loc_cache),
    )
    if ws is None:
        st.error("Invalid date range. Using all-time data for this run.")
        ws, date_filter_banner = streamlit_working_set_and_status(
            df_full,
            map_view_mode=map_view_mode,
            date_filter_on=False,
            date_range=None,
            map_caches=(st.session_state.popup_html_cache, st.session_state.filtered_by_loc_cache),
        )
    work_df = ws.df

    hide_non_matching_locations = False
    species_pick_common: str | None = None
    species_pick_sci = ""

    _prev_mv = st.session_state.get(SESSION_PREV_MAP_VIEW_KEY)
    if map_view_mode == "species" and _prev_mv is not None and _prev_mv != "species":
        st.session_state.pop(SESSION_SPECIES_SEARCH_KEY, None)

    if map_view_mode == "species":
        _ix_sig = (len(ws.species_list), st.session_state.get(EBIRD_DATA_SIG_KEY))
        if st.session_state.get(SESSION_SPECIES_IX_SIG_KEY) != _ix_sig:
            st.session_state[SESSION_SPECIES_IX_KEY] = build_ram_species_whoosh_index(
                ws.species_list, ws.name_map
            )
            st.session_state[SESSION_SPECIES_IX_SIG_KEY] = _ix_sig
        st.session_state[SESSION_SPECIES_WS_KEY] = ws

        with st.sidebar:
            st.markdown("**Species**")
            st.caption(SPECIES_SEARCH_CAPTION)
            species_searchbox_fragment()
            hide_non_matching_locations = st.toggle(
                "Show only selected species",
                key=STREAMLIT_SPECIES_HIDE_ONLY_KEY,
                help=(
                    "When off, all locations are shown with your species highlighted. "
                    "When on, only locations where you recorded the species."
                ),
            )

        species_pick_common = st.session_state.get(SESSION_SPECIES_PICK_KEY)
        if species_pick_common:
            species_pick_sci = str(ws.name_map.get(species_pick_common, "") or "")
            st.session_state[PERSIST_SPECIES_COMMON_KEY] = species_pick_common
            st.session_state[PERSIST_SPECIES_SCI_KEY] = species_pick_sci
        else:
            st.session_state.pop(PERSIST_SPECIES_COMMON_KEY, None)
            st.session_state.pop(PERSIST_SPECIES_SCI_KEY, None)
    else:
        st.session_state.pop(SESSION_SPECIES_PICK_KEY, None)

    with st.sidebar:
        st.divider()
        map_style = st.selectbox(
            "Basemap",
            options=list(MAP_BASEMAP_OPTIONS),
            key=STREAMLIT_MAP_BASEMAP_KEY,
        )
        st.markdown(
            '<div style="height:0.65rem" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        map_height = st.slider(
            "Map height (px)",
            min_value=MAP_HEIGHT_PX_MIN,
            max_value=MAP_HEIGHT_PX_MAX,
            step=MAP_HEIGHT_PX_STEP,
            key=STREAMLIT_MAP_HEIGHT_PX_KEY,
        )

    st.session_state[SESSION_PREV_MAP_VIEW_KEY] = map_view_mode

    tax_locale_effective = (st.session_state.streamlit_taxonomy_locale.strip() or DEFAULT_TAXONOMY_LOCALE)
    species_url_fn = cached_species_url_fn(tax_locale_effective)
    popup_sort_order = st.session_state.streamlit_popup_sort_order
    popup_scroll_hint = st.session_state.streamlit_popup_scroll_hint
    mark_lifer = bool(st.session_state.streamlit_mark_lifer)
    mark_last_seen = bool(st.session_state.streamlit_mark_last_seen)

    inject_spinner_theme_css()

    st.title("Personal eBird Explorer — Streamlit prototype")

    (
        tab_map,
        tab_checklist,
        tab_rankings,
        tab_yearly,
        tab_country,
        tab_maint,
        tab_settings,
    ) = st.tabs(NOTEBOOK_MAIN_TAB_LABELS)

    with st.spinner(CHECKLIST_STATS_SPINNER_MESSAGE):
        checklist_payload = cached_checklist_stats_payload(work_df)
        maint_full_payload = cached_checklist_stats_payload(df_full)
        sex_notation_by_year = cached_sex_notation_by_year(df_full)

    with tab_map:
        prov_plain = provenance or ""
        sig = data_signature_for_caches(df_full, prov_plain)
        if st.session_state.get(EBIRD_DATA_SIG_KEY) != sig:
            st.session_state.ebird_data_sig = sig
            st.session_state.popup_html_cache = {}
            st.session_state.filtered_by_loc_cache = OrderedDict()
            st.session_state.pop(FOLIUM_STATIC_MAP_CACHE_KEY, None)

        try:
            ctx = prepare_all_locations_map_context(work_df, full_df=df_full)
        except ValueError as e:
            st.warning(str(e))
            st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
        else:
            overlay_common = (
                (species_pick_common or "").strip() if map_view_mode == "species" else ""
            )
            overlay_sci = (
                (species_pick_sci or "").strip() if map_view_mode == "species" else ""
            )
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
                "date_filter_status": date_filter_banner,
                "species_url_fn": species_url_fn,
                "base_species_fn": base_species_for_lifer,
                "taxonomy_locale": tax_locale_effective,
                "popup_html_cache": st.session_state.popup_html_cache,
                "filtered_by_loc_cache": st.session_state.filtered_by_loc_cache,
                "map_view_mode": map_view_mode,
                "hide_non_matching_locations": hide_nm,
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
            )
            _ck = static_map_cache_key(
                work_df,
                map_view_mode,
                date_filter_banner,
                map_style,
                _render_opts_sig,
                taxonomy_locale=tax_locale_effective,
            )
            _use_static_cache = map_view_mode in ("all", "lifers")
            _cached = (
                st.session_state.get(FOLIUM_STATIC_MAP_CACHE_KEY) if _use_static_cache else None
            )
            if (
                _use_static_cache
                and isinstance(_cached, dict)
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
                st.warning(result_warning)
                st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
            elif result_map is None:
                st.warning("Map could not be built.")
                st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
            else:
                st.session_state[EXPLORER_MAP_HTML_BYTES_KEY] = folium_map_to_html_bytes(result_map)
                try:
                    from streamlit_folium import st_folium
                except ImportError:
                    st.error(
                        "Missing **streamlit-folium** (needed to embed the Folium map). "
                        "Locally: `pip install -r requirements-streamlit.txt`. "
                        "**Streamlit Community Cloud:** set app **Python requirements** to "
                        "`requirements-streamlit.txt` or `streamlit_app/requirements.txt` "
                        "(not the repo root `requirements.txt`)."
                    )
                    st.stop()
                st_folium(
                    result_map,
                    use_container_width=True,
                    height=map_height,
                    key=f"explorer_folium_map_h{map_height}",
                    returned_objects=[],
                    return_on_hover=False,
                )

    with tab_checklist:
        if checklist_payload is not None:
            render_checklist_stats_streamlit_html(checklist_payload)
        else:
            st.warning("No checklist data to show.")

    with tab_rankings:
        if df_full is None or df_full.empty:
            st.info("Load checklist data to use Rankings & lists.")
        else:
            render_rankings_streamlit_tab(
                df_full,
                country_sort=st.session_state.streamlit_country_tab_sort,
                taxonomy_locale=tax_locale_effective,
            )

    with tab_yearly:
        sync_yearly_summary_session_inputs(checklist_payload)
        run_yearly_summary_streamlit_fragment()

    with tab_country:
        if checklist_payload is not None:
            sync_country_tab_session_inputs(checklist_payload)
            run_country_tab_streamlit_fragment()
        else:
            st.warning("No checklist data to show.")

    with tab_maint:
        loc_maint = full_location_data_for_maintenance(df_full)
        incomplete_maint: dict = {}
        if maint_full_payload is not None:
            incomplete_maint = maint_full_payload.incomplete_by_year or {}
        render_maintenance_streamlit_tab(
            loc_maint,
            close_location_meters=int(st.session_state.streamlit_close_location_meters),
            incomplete_by_year=incomplete_maint,
            sex_notation_by_year=sex_notation_by_year,
            species_url_fn=species_url_fn,
        )

    with tab_settings:
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
                        use_container_width=True,
                    ):
                        ok, err = write_settings_yaml_via_module(
                            settings_yaml_path, settings_state_payload()
                        )
                        if ok:
                            st.session_state[SETTINGS_BASELINE_KEY] = settings_state_payload()
                            st.session_state[SETTINGS_FLASH_SAVE_KEY] = True
                        else:
                            st.error(err or "Failed to save settings.")
                with b2:
                    if st.button(
                        "Reset to defaults",
                        key=STREAMLIT_RESET_SETTINGS_BTN_KEY,
                        use_container_width=True,
                    ):
                        apply_settings_payload_to_state(settings_defaults_payload())
                        init_and_clamp_streamlit_table_settings()
                        st.session_state[SETTINGS_FLASH_RESET_KEY] = True

                settings_persistence_flash_banners()
                st.caption(
                    "Settings apply immediately in-session. Save writes your preferences to your "
                    "configuration file."
                )
                st.caption(f"Configuration file: {settings_yaml_path}")

            st.divider()
            st.subheader("Map display")
            st.toggle("Mark lifer", key=STREAMLIT_MARK_LIFER_KEY)
            st.toggle("Mark last-seen", key=STREAMLIT_MARK_LAST_SEEN_KEY)
            st.selectbox(
                "Popup sort order",
                options=["ascending", "descending"],
                key=STREAMLIT_POPUP_SORT_ORDER_KEY,
            )
            st.selectbox(
                "Popup scroll hint",
                options=["shading", "chevron", "both"],
                key=STREAMLIT_POPUP_SCROLL_HINT_KEY,
            )
            st.caption("Pin colors")
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox(
                    "Default edge",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    key=STREAMLIT_DEFAULT_COLOR_KEY,
                )
                st.selectbox(
                    "Species edge",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    key=STREAMLIT_SPECIES_COLOR_KEY,
                )
                st.selectbox(
                    "Lifer edge",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    key=STREAMLIT_LIFER_COLOR_KEY,
                )
                st.selectbox(
                    "Last-seen edge",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    key=STREAMLIT_LAST_SEEN_COLOR_KEY,
                )
            with c2:
                st.selectbox(
                    "Default fill",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    key=STREAMLIT_DEFAULT_FILL_KEY,
                )
                st.selectbox(
                    "Species fill",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    key=STREAMLIT_SPECIES_FILL_KEY,
                )
                st.selectbox(
                    "Lifer fill",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    key=STREAMLIT_LIFER_FILL_KEY,
                )
                st.selectbox(
                    "Last-seen fill",
                    MAP_PIN_COLOUR_ALLOWLIST,
                    key=STREAMLIT_LAST_SEEN_FILL_KEY,
                )

            st.divider()
            st.subheader("Tables & lists")
            # Sliders feed Rankings & lists / Yearly Summary / Country sparse-year UI (shared formatters).
            st.slider(
                "Ranking tables: number of results",
                min_value=TABLES_RANKINGS_TOP_N_MIN,
                max_value=TABLES_RANKINGS_TOP_N_MAX,
                step=1,
                key=STREAMLIT_RANKINGS_TOP_N_KEY,
            )
            st.slider(
                "Ranking tables: visible rows",
                min_value=TABLES_RANKINGS_VISIBLE_ROWS_MIN,
                max_value=TABLES_RANKINGS_VISIBLE_ROWS_MAX,
                step=1,
                key=STREAMLIT_RANKINGS_VISIBLE_ROWS_KEY,
            )
            st.slider(
                "Yearly tables: recent year columns",
                min_value=YEARLY_RECENT_COLUMN_COUNT_MIN,
                max_value=YEARLY_RECENT_COLUMN_COUNT_MAX,
                step=1,
                key=STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY,
            )
            st.selectbox(
                "Country ordering",
                options=[
                    COUNTRY_TAB_SORT_ALPHABETICAL,
                    COUNTRY_TAB_SORT_LIFERS_WORLD,
                    COUNTRY_TAB_SORT_TOTAL_SPECIES,
                ],
                format_func=lambda k: COUNTRY_SORT_LABELS[k],
                key=STREAMLIT_COUNTRY_TAB_SORT_KEY,
            )
            st.divider()
            st.subheader("Maintenance")
            st.slider(
                "Close location (m)",
                min_value=MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
                max_value=MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
                step=1,
                key=STREAMLIT_CLOSE_LOCATION_METERS_KEY,
                help=(
                    "Locations within this distance (metres), excluding exact duplicate coordinates, "
                    "are listed under **Maintenance → Location Maintenance → Close locations**."
                ),
            )
            st.divider()
            st.subheader("Taxonomy")
            st.text_input(
                "Taxonomy locale",
                key=STREAMLIT_TAXONOMY_LOCALE_KEY,
            )
            st.markdown(settings_taxonomy_help_html(), unsafe_allow_html=True)
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

    if st.session_state.get(EXPLORER_MAP_HTML_BYTES_KEY):
        with st.sidebar:
            st.divider()
            st.download_button(
                "Export map HTML",
                data=st.session_state[EXPLORER_MAP_HTML_BYTES_KEY],
                file_name=MAP_EXPORT_HTML_FILENAME,
                mime="text/html",
                key=EXPORT_MAP_HTML_BTN_KEY,
                help="Standalone HTML for the current map (notebook-style export).",
            )

    sidebar_footer_links()


if __name__ == "__main__":
    main()

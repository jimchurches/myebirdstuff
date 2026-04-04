"""
Personal eBird Explorer — Streamlit app (Folium map + rich location popups).

Planning and phased migration notes: https://github.com/jimchurches/myebirdstuff/issues/70 (refs #70).

Run locally from repo root::

    pip install -r requirements.txt
    streamlit run explorer/app/streamlit/app.py

Disk resolution when no file is uploaded: ``config/config_secret.yaml`` and
``config/config.yaml`` (``data_folder``), then the **process working directory**
(where you ran ``streamlit run``). See ``explorer/app/streamlit/README.md`` — *Data loading*.

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
``checklist_stats_streamlit_tab_sections_html``). ``cached_checklist_stats_payload(work_df)``, full-export prep,
sync helpers, and **Map** tab Folium build + ``st_folium`` run inside one ``st.spinner(...)`` so the themed
spinner tracks the top “Running…” bar more closely; other main tabs render after the spinner exits.
``sync_checklist_stats_tab_session_inputs`` + ``@st.fragment`` match Country / Yearly (refs #70).

**Country:** Per-country yearly table uses the same ``CHECKLIST_STATS_*`` HTML/CSS as Checklist Statistics
(``country_stats_streamlit_html``). The tab runs inside ``@st.fragment`` so changing the country selectbox
triggers a **partial rerun** (not the whole map/checklist pipeline) (refs #75).

**Maintenance:** Same fragment pattern; incomplete checklists use ``cached_full_export_checklist_stats_payload``
(aligned with Rankings Top N + high-count settings). **Close location (m)** is set under **Settings → Tables & lists**
(refs #79).

**Ranking & Lists:** ``cached_full_export_checklist_stats_payload`` + ``format_checklist_stats_bundle``;
``build_rankings_tab_bundle`` runs in the main spinner pass; **Top N** / **visible rows** / table options are under
**Settings → Tables & lists** (batch **Apply**; refs `#81`).

**Yearly Summary:** ``yearly_summary_streamlit_html`` — nested **All** / **Travelling** / **Stationary** tabs inside
``@st.fragment``; ``st.toggle`` switches recent vs full year columns when count exceeds **Settings → Yearly tables:
recent year columns** (default 10). ``sync_yearly_summary_session_inputs`` + ``run_yearly_summary_streamlit_fragment``
match the Country tab fragment pattern (refs #85).

**Main tabs + sidebar:** Map tab body runs inside the main ``st.spinner`` block each full rerun; data tabs use ``@st.fragment`` where possible. One always-on
sidebar for map controls plus footer links (refs #70). Settings use a keyed container with
``max-width: min(100%, 40rem)`` on wide viewports. **Tables & lists** controls are batched in a form (one rerun on **Apply**).
"""

from __future__ import annotations

import base64
import os
import sys

# ``streamlit run explorer/app/streamlit/app.py`` puts the script directory on ``sys.path``, not the
# repo root. Prepend repo root so ``import explorer.*`` resolves (refs #70).
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from collections import OrderedDict
from pathlib import Path

import pandas as pd
import streamlit as st

from explorer.presentation.checklist_stats_display import (  # noqa: E402
    COUNTRY_TAB_SORT_ALPHABETICAL,
    COUNTRY_TAB_SORT_LIFERS_WORLD,
    COUNTRY_TAB_SORT_TOTAL_SPECIES,
)
from explorer.core.explorer_paths import settings_yaml_path_for_source  # noqa: E402
from explorer.core.map_controller import build_species_overlay_map  # noqa: E402
from explorer.core.species_search import build_ram_species_whoosh_index  # noqa: E402
from explorer.core.species_logic import base_species_for_lifer  # noqa: E402
from explorer.core.map_prep import (  # noqa: E402
    data_signature_for_caches,
    prepare_all_locations_map_context,
)
from explorer.app.streamlit.app_caches import (  # noqa: E402
    cached_checklist_stats_payload,
    cached_full_export_checklist_stats_payload,
    cached_sex_notation_by_year,
    cached_species_url_fn,
    full_location_data_for_maintenance,
    static_map_cache_key,
)
from explorer.app.streamlit.app_constants import (  # noqa: E402
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
    STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
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
    STREAMLIT_SPECIES_HIDE_ONLY_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
    STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY,
)
from explorer.app.streamlit.app_data_loading import load_dataframe  # noqa: E402
from explorer.app.streamlit.app_map_ui import (  # noqa: E402
    ensure_streamlit_map_basemap_height_keys,
    inject_spinner_emoji_animation,
    inject_spinner_theme_css,
    sidebar_footer_links,
    species_searchbox_fragment,
)
from explorer.app.streamlit.app_settings_state import (  # noqa: E402
    apply_settings_payload_to_state,
    env_taxonomy_locale,
    init_and_clamp_streamlit_table_settings,
    load_settings_yaml_via_module,
    settings_config_module_available,
    settings_data_path_html,
    settings_defaults_payload,
    settings_persistence_flash_banners,
    settings_state_payload,
    settings_taxonomy_help_markdown,
    write_settings_yaml_via_module,
)
from explorer.app.streamlit.checklist_stats_streamlit_html import (  # noqa: E402
    run_checklist_stats_streamlit_fragment,
    sync_checklist_stats_tab_session_inputs,
)
from explorer.app.streamlit.country_stats_streamlit_html import (  # noqa: E402
    run_country_tab_streamlit_fragment,
    sync_country_tab_session_inputs,
)
from explorer.core.settings_schema_defaults import (  # noqa: E402
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
from explorer.app.streamlit.defaults import (  # noqa: E402
    MAP_BASEMAP_LABELS,
    MAP_BASEMAP_OPTIONS,
    MAP_DATE_FILTER_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
    MAP_VIEW_LABELS,
)
from explorer.app.streamlit.streamlit_ui_constants import (  # noqa: E402
    CHECKLIST_STATS_SPINNER_TEXT,
    MAP_EXPORT_HTML_FILENAME,
    NOTEBOOK_MAIN_TAB_LABELS,
    SPECIES_SEARCH_CAPTION,
)
from explorer.app.streamlit.maintenance_streamlit_html import (  # noqa: E402
    run_maintenance_streamlit_tab_fragment,
    sync_maintenance_tab_session_inputs,
)
from explorer.app.streamlit.map_working import (  # noqa: E402
    date_inception_to_today_default,
    folium_map_to_html_bytes,
    streamlit_working_set_and_status,
)
from explorer.app.streamlit.rankings_streamlit_html import (  # noqa: E402
    build_rankings_tab_bundle,
    run_rankings_streamlit_tab_fragment,
    sync_rankings_tab_session_inputs,
)
from explorer.app.streamlit.yearly_summary_streamlit_html import (  # noqa: E402
    run_yearly_summary_streamlit_fragment,
    sync_yearly_summary_session_inputs,
)

# Same asset as docs/explorer/README.md (repo-relative).
_APP_LOGO_SVG = Path(REPO_ROOT) / "docs" / "explorer" / "assets" / "personal-ebird-explorer-logo.svg"


def _title_with_logo() -> None:
    """App heading: title + logo in one compact row (flex), logo beside text—not full-width columns."""
    if _APP_LOGO_SVG.is_file():
        b64 = base64.b64encode(_APP_LOGO_SVG.read_bytes()).decode("ascii")
        # ``st.html`` avoids extra block height from ``st.image`` + wide ``st.columns``; flex keeps
        # the mark next to the title on large screens and wraps on narrow viewports.
        st.html(
            "<div style='display:flex;flex-direction:row;align-items:center;flex-wrap:wrap;"
            "gap:0.75rem;margin:0;padding:0 0 0.2rem 0;'>"
            "<h1 style='margin:0;padding:0;font-size:clamp(1.35rem,3.5vw,2.25rem);"
            "line-height:1.15;font-weight:600;'>Personal eBird Explorer</h1>"
            f"<img src='data:image/svg+xml;base64,{b64}' alt='' width='77' "
            "style='width:77px;max-width:min(77px,18vw);height:auto;display:block;"
            "margin:0 0 0 77px;flex-shrink:0;'/>"
            "</div>"
        )
    else:
        st.title("Personal eBird Explorer")


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
            _title_with_logo()
            st.markdown(
                "Your eBird data, made visible, navigable, and ready to explore"
            )
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
            st.caption("Lifer locations are not date-filtered.")
            if st.session_state.get(PERSIST_MAP_DATE_FILTER_KEY, MAP_DATE_FILTER_DEFAULT):
                st.caption("Your date filter is preserved for other map views.")
            st.toggle(
                "Show subspecies lifers",
                key=STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
            )
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
            format_func=lambda k: MAP_BASEMAP_LABELS.get(k, k),
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

    _title_with_logo()
    st.markdown("Your eBird data, made visible, navigable, and ready to explore")

    (
        tab_map,
        tab_checklist,
        tab_rankings,
        tab_yearly,
        tab_country,
        tab_maint,
        tab_settings,
    ) = st.tabs(NOTEBOOK_MAIN_TAB_LABELS)

    # Emoji strip: first nodes inside ``st.spinner`` so it sits under the status row (refs #74).
    with st.spinner(CHECKLIST_STATS_SPINNER_TEXT):
        _spinner_emoji_placeholder = st.empty()
        with _spinner_emoji_placeholder.container():
            inject_spinner_emoji_animation()
        checklist_payload = cached_checklist_stats_payload(work_df)
        top_n = int(st.session_state.streamlit_rankings_top_n)
        hc_sort = str(st.session_state.streamlit_high_count_sort)
        hc_tb = str(st.session_state.streamlit_high_count_tie_break)
        if df_full is not None and not df_full.empty:
            maint_full_payload = cached_full_export_checklist_stats_payload(
                df_full, top_n, hc_sort, hc_tb
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
        sex_notation_by_year = cached_sex_notation_by_year(df_full)

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

        # Keep spinner visible through Folium build + ``st_folium`` so it tracks the top “Running…” bar
        # more closely (spinner ends when this block exits; other tabs render after).
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
                    "cluster_all_locations": bool(
                        st.session_state.get(
                            STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                            MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
                        )
                    ),
                    # For lifer mode we already communicate the “not date-filtered” behaviour in the
                    # side panel. Avoid repeating "all-time data" text in the banner.
                    "date_filter_status": "" if is_lifer_view else date_filter_banner,
                    "species_url_fn": species_url_fn,
                    "base_species_fn": base_species_for_lifer,
                    "taxonomy_locale": tax_locale_effective,
                    "popup_html_cache": st.session_state.popup_html_cache,
                    "filtered_by_loc_cache": st.session_state.filtered_by_loc_cache,
                    "map_view_mode": map_view_mode,
                    "hide_non_matching_locations": hide_nm,
                    "show_subspecies_lifers": bool(st.session_state.get(STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY, False)),
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
                )
                # ``build_species_overlay_map`` treats **Species** with no species picked as the same
                # geometry as **All locations** (``map_controller`` coerces mode to ``all``). Match that here
                # so static Folium reuse applies when switching Map view All ↔ Species before a selection.
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
                # One Folium map in session; key includes species + hide toggle so Selected species
                # maps reuse on identical full reruns (e.g. switching tabs) without a multi-species LRU.
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
                            "Locally: `pip install -r requirements.txt`. "
                            "**Streamlit Community Cloud:** set app **Python requirements** to "
                            "`requirements.txt` at the repo root."
                        )
                        st.stop()
                    st_folium(
                        result_map,
                        use_container_width=True,
                        height=map_height,
                        # Include the full map cache key in the component identity so switching views,
                        # toggles, and even server restarts remount the iframe (prevents stale marker
                        # styling like "white pins" persisting across sessions).
                        key=f"explorer_folium_{abs(hash(_ck))}_h{map_height}",
                        returned_objects=[],
                        return_on_hover=False,
                    )

        _spinner_emoji_placeholder.empty()  # Drop emoji iframe once load finishes (refs #74).

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
                        width="stretch",
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
                "Popup behaviour, mark toggles, clustering for the All locations map, and pin colours "
                "are batched here; click **Apply map settings** for one rerun."
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
                mark_lifer_w = st.toggle(
                    "Mark lifer",
                    value=bool(st.session_state.get(STREAMLIT_MARK_LIFER_KEY, True)),
                )
                mark_last_seen_w = st.toggle(
                    "Mark last-seen",
                    value=bool(st.session_state.get(STREAMLIT_MARK_LAST_SEEN_KEY, True)),
                )
                cluster_all_locations_w = st.toggle(
                    "Group nearby pins (All locations map)",
                    value=bool(
                        st.session_state.get(
                            STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                            MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
                        )
                    ),
                    help=(
                        "When on, nearby checklist locations are combined into clusters at low zoom; "
                        "zoom in or click a cluster to see individual pins. "
                        "Species and lifer maps always show one pin per location."
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
                st.session_state[STREAMLIT_MARK_LIFER_KEY] = bool(mark_lifer_w)
                st.session_state[STREAMLIT_MARK_LAST_SEEN_KEY] = bool(mark_last_seen_w)
                st.session_state[STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY] = bool(cluster_all_locations_w)
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
            # Same ``st.caption`` + Markdown pattern as the Tables & Lists intro (no custom SETTINGS_PANEL_CSS block).
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

    if st.session_state.get(EXPLORER_MAP_HTML_BYTES_KEY):
        with st.sidebar:
            st.divider()
            st.download_button(
                "Export map HTML",
                data=st.session_state[EXPLORER_MAP_HTML_BYTES_KEY],
                file_name=MAP_EXPORT_HTML_FILENAME,
                mime="text/html",
                key=EXPORT_MAP_HTML_BTN_KEY,
                help="Standalone HTML for the current map.",
            )

    sidebar_footer_links()


if __name__ == "__main__":
    main()

"""Map sidebar controls (basemap, view, dates, species) + working set resolution (refs #131)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from explorer.app.streamlit.app_constants import (
    EBIRD_DATA_SIG_KEY,
    EXPLORER_MAP_HTML_BYTES_KEY,
    REPO_ROOT,
    FILTERED_BY_LOC_CACHE_KEY,
    FOLIUM_MAP_MOUNT_NONCE_KEY,
    FOLIUM_STATIC_MAP_CACHE_KEY,
    MAP_VIEW_LABEL_TO_MODE,
    PERSIST_MAP_DATE_FILTER_KEY,
    PERSIST_MAP_DATE_RANGE_KEY,
    POPUP_HTML_CACHE_KEY,
    PERSIST_SPECIES_COMMON_KEY,
    PERSIST_SPECIES_SCI_KEY,
    SESSION_PREV_MAP_VIEW_KEY,
    SESSION_SPECIES_IX_KEY,
    SESSION_SPECIES_IX_SIG_KEY,
    SESSION_SPECIES_PICK_KEY,
    SESSION_SPECIES_SEARCH_KEY,
    SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY,
    SESSION_SPECIES_WS_KEY,
    STREAMLIT_MAP_BASEMAP_KEY,
    STREAMLIT_MAP_BASEMAP_SAVED_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
    STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
    STREAMLIT_MAP_DATE_FILTER_KEY,
    STREAMLIT_MAP_DATE_RANGE_KEY,
    STREAMLIT_MAP_HEIGHT_PX_KEY,
    STREAMLIT_MAP_VIEW_LABEL_KEY,
    SESSION_PREV_EFFECTIVE_BASEMAP_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
    STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
    STREAMLIT_SPECIES_HIDE_ONLY_KEY,
    STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY,
    STREAMLIT_FAMILY_MAP_FAMILY_KEY,
    STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY,
    SETTINGS_CONFIG_SOURCE_KEY,
    DEFAULT_TAXONOMY_LOCALE,
)
from explorer.app.streamlit.app_go_to_gps_ui import render_go_to_gps_sidebar_expander
from explorer.app.streamlit.app_map_ui import (
    ensure_streamlit_map_basemap_height_keys,
    ensure_streamlit_map_marker_colour_scheme_keys,
    inject_spinner_theme_css,
    species_searchbox_fragment,
)
from explorer.app.streamlit.app_settings_state import apply_pending_map_cluster_toggle
from explorer.app.streamlit.app_settings_state import apply_pending_map_basemap_override
from explorer.app.streamlit.app_settings_state import apply_pending_map_height_override
from explorer.app.streamlit.app_settings_state import apply_pending_map_marker_colour_scheme
from explorer.app.streamlit.defaults import (
    MAP_MARKER_COLOUR_SCHEME_1,
    MAP_MARKER_COLOUR_SCHEME_2,
    MAP_MARKER_COLOUR_SCHEME_3,
    MAP_BASEMAP_LABELS,
    MAP_BASEMAP_OPTIONS,
    MAP_DATE_FILTER_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
    MAP_SPECIES_HIDE_ONLY_DEFAULT,
    MAP_VIEW_LABELS,
)
from explorer.app.streamlit.map_working import (
    date_inception_to_today_default,
    streamlit_working_set_and_status,
)
from explorer.core.explorer_paths import settings_yaml_path_for_source
from explorer.app.streamlit.perf_instrumentation import render_explorer_perf_sidebar_panel
from explorer.app.streamlit.streamlit_ui_constants import (
    SPECIES_SEARCH_CAPTION,
    SPECIES_SEARCH_HELP_EXPANDER_LABEL,
)
from explorer.core.all_locations_viewport import (
    ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ALL_LOCATIONS_FRAMING_FIT_ALL,
    ALL_LOCATIONS_SCOPE_FOCUSED,
    all_locations_scope_option_values,
)
from explorer.core.region_display import map_focus_key_for_display
from explorer.core.species_search import (
    SPECIES_WHOOSH_INDEX_VERSION,
    build_ram_species_whoosh_index,
)


def invalidate_folium_map_embed_cache() -> None:
    """Bump Folium mount nonce and drop cached map HTML (basemap, family colours, etc.)."""
    st.session_state[FOLIUM_MAP_MOUNT_NONCE_KEY] = int(
        st.session_state.get(FOLIUM_MAP_MOUNT_NONCE_KEY, 0)
    ) + 1
    st.session_state.pop(FOLIUM_STATIC_MAP_CACHE_KEY, None)
    st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)


def _on_basemap_changed() -> None:
    """Invalidate Folium cache + remount iframe when the basemap **value** changes (refs #124)."""
    invalidate_folium_map_embed_cache()


@dataclass(frozen=True)
class MapWorkingContext:
    """Map sidebar selections and filtered dataframe for the dashboard (after working-set resolution)."""

    map_style: Any
    map_view_mode: str
    is_lifer_view: bool
    date_filter_banner: str
    work_df: Any
    hide_non_matching_locations: bool
    species_pick_common: str | None
    species_pick_sci: str
    map_height: int
    family_name: str
    family_highlight_base: str
    family_colour_scheme: int


def render_map_sidebar_and_working_set(df_full: Any) -> MapWorkingContext:
    """Map sidebar widgets, working set + species search, Folium cache invalidation on All↔Species."""
    ensure_streamlit_map_basemap_height_keys()
    ensure_streamlit_map_marker_colour_scheme_keys()

    apply_pending_map_cluster_toggle(st.session_state)
    apply_pending_map_basemap_override(st.session_state)
    apply_pending_map_height_override(st.session_state)
    apply_pending_map_marker_colour_scheme(st.session_state)

    inject_spinner_theme_css()

    with st.sidebar:
        st.header("Map")
        saved_basemap = st.session_state.get(STREAMLIT_MAP_BASEMAP_SAVED_KEY, MAP_BASEMAP_OPTIONS[0])
        if saved_basemap not in MAP_BASEMAP_OPTIONS:
            saved_basemap = MAP_BASEMAP_OPTIONS[0]
        override = st.session_state.get(STREAMLIT_MAP_BASEMAP_KEY, saved_basemap)
        if override not in MAP_BASEMAP_OPTIONS:
            override = saved_basemap
        map_style = override

        # Renamed label (was "Selected species"); keep existing sessions valid.
        if st.session_state.get(STREAMLIT_MAP_VIEW_LABEL_KEY) == "Selected species":
            st.session_state[STREAMLIT_MAP_VIEW_LABEL_KEY] = "Species locations"

        map_view_label = st.selectbox(
            "Map view",
            list(MAP_VIEW_LABELS),
            key=STREAMLIT_MAP_VIEW_LABEL_KEY,
        )
        map_view_mode = MAP_VIEW_LABEL_TO_MODE[map_view_label]
        is_lifer_view = map_view_mode == "lifers"
        is_family_view = map_view_mode == "families"

        if is_lifer_view:
            st.toggle(
                "Show subspecies lifers",
                key=STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
            )
            date_filter_on_effective = False
            date_range_sel: tuple | None = None
        elif is_family_view:
            # Family map view (v1): keep UI minimal; ignore date filter and clustering controls.
            # We do **not** clear persisted date filter state; switching back restores prior picks.
            date_filter_on_effective = False
            date_range_sel = None
        else:
            if STREAMLIT_MAP_DATE_FILTER_KEY not in st.session_state:
                st.session_state.streamlit_map_date_filter = bool(
                    st.session_state.get(PERSIST_MAP_DATE_FILTER_KEY, MAP_DATE_FILTER_DEFAULT)
                )
            if st.session_state.get(STREAMLIT_MAP_DATE_FILTER_KEY, False):
                if STREAMLIT_MAP_DATE_RANGE_KEY not in st.session_state:
                    pr = st.session_state.get(PERSIST_MAP_DATE_RANGE_KEY)
                    if isinstance(pr, tuple) and len(pr) == 2:
                        st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = pr
                    else:
                        a, b = date_inception_to_today_default(df_full)
                        st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = (a, b)

            date_filter_on_effective = st.toggle(
                "Date filter",
                key=STREAMLIT_MAP_DATE_FILTER_KEY,
                help="Filters the map to a selected date range.",
            )
            if not date_filter_on_effective:
                date_range_sel = None
            else:
                d_inception, today = date_inception_to_today_default(df_full)
                if STREAMLIT_MAP_DATE_RANGE_KEY not in st.session_state:
                    st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = (d_inception, today)
                rng = st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY]
                if not isinstance(rng, tuple) or len(rng) != 2:
                    st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = (d_inception, today)
                else:
                    r0 = max(min(rng[0], today), d_inception)
                    r1 = max(min(rng[1], today), d_inception)
                    rng_val = (r0, r1) if r0 <= r1 else (r1, r0)
                    if rng_val != rng:
                        st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = rng_val
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

        if map_view_mode == "all":
            st.toggle(
                "Group nearby markers",
                key=STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                help="Groups nearby markers when zoomed out to reduce clutter.",
            )

    # Working set is still date-filtered for checklist stats and other tabs.
    # Family map ignores date filtering (v1), but we preserve the date filter controls and state.
    _ws_mode = "all" if is_family_view else map_view_mode
    ws, date_filter_banner = streamlit_working_set_and_status(
        df_full,
        map_view_mode=_ws_mode,
        date_filter_on=date_filter_on_effective,
        date_range=date_range_sel,
        map_caches=(
            st.session_state.get(POPUP_HTML_CACHE_KEY),
            st.session_state.get(FILTERED_BY_LOC_CACHE_KEY),
        ),
    )
    if ws is None:
        st.error("Invalid date range. Using all-time data for this run.")
        ws, date_filter_banner = streamlit_working_set_and_status(
            df_full,
            map_view_mode=map_view_mode,
            date_filter_on=False,
            date_range=None,
            map_caches=(
                st.session_state.get(POPUP_HTML_CACHE_KEY),
                st.session_state.get(FILTERED_BY_LOC_CACHE_KEY),
            ),
        )
    work_df = ws.df

    if map_view_mode == "all":
        with st.sidebar:
            _scope_opts = all_locations_scope_option_values(work_df)
            _cur_scope = st.session_state.get(STREAMLIT_ALL_LOCATIONS_SCOPE_KEY)
            if _cur_scope not in _scope_opts:
                st.session_state[STREAMLIT_ALL_LOCATIONS_SCOPE_KEY] = ALL_LOCATIONS_SCOPE_FOCUSED
            st.selectbox(
                "Map focus",
                options=_scope_opts,
                format_func=lambda v: (
                    "All locations"
                    if v == ALL_LOCATIONS_FRAMING_FIT_ALL
                    else "Focused"
                    if v == ALL_LOCATIONS_SCOPE_FOCUSED
                    else "My activity centre"
                    if v == ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY
                    else map_focus_key_for_display(v)
                ),
                key=STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
            )
            _scope_sel = st.session_state.get(STREAMLIT_ALL_LOCATIONS_SCOPE_KEY)
            if _scope_sel == ALL_LOCATIONS_SCOPE_FOCUSED:
                st.caption(
                    "Focused view shows your main birding regions. "
                    "Other locations may be outside the current view; zoom or pan to find them."
                )
            elif _scope_sel == ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY:
                st.caption(
                    "Centres the map on the middle of the places you've birded. "
                    "You may need to zoom out to see more locations."
                )
            render_go_to_gps_sidebar_expander()

    hide_non_matching_locations = False
    species_pick_common: str | None = None
    species_pick_sci = ""
    family_name = ""
    family_highlight_base = ""
    family_colour_scheme = 1

    _prev_mv = st.session_state.get(SESSION_PREV_MAP_VIEW_KEY)
    if map_view_mode == "species" and _prev_mv is not None and _prev_mv != "species":
        st.session_state.pop(SESSION_SPECIES_SEARCH_KEY, None)
        _n = int(st.session_state.get(SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY, 0))
        st.session_state.pop(f"{SESSION_SPECIES_SEARCH_KEY}__v{_n}", None)
        st.session_state.pop(SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY, None)

    if map_view_mode == "species":
        # PICK is cleared when leaving species for All / Family / Lifers; PERSIST keeps the last
        # species name for the map. Restore PICK so the map, search box, and persist stay aligned.
        if not st.session_state.get(SESSION_SPECIES_PICK_KEY):
            _pc = st.session_state.get(PERSIST_SPECIES_COMMON_KEY)
            if _pc:
                st.session_state[SESSION_SPECIES_PICK_KEY] = str(_pc).strip()

        tax_loc = (
            str(st.session_state.get(STREAMLIT_TAXONOMY_LOCALE_KEY, "")).strip()
            or DEFAULT_TAXONOMY_LOCALE
        )
        _ix_sig = (
            SPECIES_WHOOSH_INDEX_VERSION,
            len(ws.species_list),
            st.session_state.get(EBIRD_DATA_SIG_KEY),
            tax_loc,
        )
        if st.session_state.get(SESSION_SPECIES_IX_SIG_KEY) != _ix_sig:
            st.session_state[SESSION_SPECIES_IX_KEY] = build_ram_species_whoosh_index(
                ws.species_list,
                ws.name_map,
                taxonomy_locale=tax_loc,
            )
            st.session_state[SESSION_SPECIES_IX_SIG_KEY] = _ix_sig
        st.session_state[SESSION_SPECIES_WS_KEY] = ws

        with st.sidebar:
            st.markdown("**Species**")
            species_searchbox_fragment()
            if STREAMLIT_SPECIES_HIDE_ONLY_KEY not in st.session_state:
                st.session_state[STREAMLIT_SPECIES_HIDE_ONLY_KEY] = MAP_SPECIES_HIDE_ONLY_DEFAULT
            hide_non_matching_locations = st.toggle(
                "Show only selected species",
                key=STREAMLIT_SPECIES_HIDE_ONLY_KEY,
            )
            with st.expander(SPECIES_SEARCH_HELP_EXPANDER_LABEL, expanded=False):
                # Match Yearly Summary helper line (``st.caption`` for “Showing results…”).
                for _para in (p.strip() for p in SPECIES_SEARCH_CAPTION.split("\n\n")):
                    if _para:
                        st.caption(_para)
            render_go_to_gps_sidebar_expander()

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

    if map_view_mode in ("all", "families"):
        from explorer.app.streamlit.app_caches import cached_family_map_bundle
        from explorer.core.family_map_compute import (
            filter_work_to_family,
            highlight_species_choices_alphabetical,
        )

        with st.sidebar:
            if map_view_mode == "families":
                tax_loc = (
                    str(st.session_state.get(STREAMLIT_TAXONOMY_LOCALE_KEY, "")).strip()
                    or DEFAULT_TAXONOMY_LOCALE
                )
                bundle = cached_family_map_bundle(df_full, tax_loc)
                fams = list(bundle.get("families") or ())
                work = bundle.get("work")
                base_to_common = bundle.get("base_to_common") or {}

                family_name = st.selectbox(
                    "Family",
                    options=[""] + fams,
                    format_func=lambda x: "— Select a family —" if x == "" else x,
                    key=STREAMLIT_FAMILY_MAP_FAMILY_KEY,
                )

                if family_name and isinstance(work, pd.DataFrame) and not work.empty:
                    wf = filter_work_to_family(work, family_name)
                    pairs = highlight_species_choices_alphabetical(wf, base_to_common)
                    bases = [b for _lab, b in pairs]
                    family_highlight_base = st.selectbox(
                        "Highlight species (optional)",
                        options=[""] + bases,
                        format_func=lambda b: "— None —" if b == "" else (base_to_common.get(b) or b),
                        key=STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY,
                    )
                else:
                    st.selectbox(
                        "Highlight species (optional)",
                        options=["— None —"],
                        disabled=True,
                        key=f"{STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY}__disabled",
                    )
                    family_highlight_base = ""

    _scheme_preset_labels = {
        1: MAP_MARKER_COLOUR_SCHEME_1.display_name,
        2: MAP_MARKER_COLOUR_SCHEME_2.display_name,
        3: MAP_MARKER_COLOUR_SCHEME_3.display_name,
    }

    with st.sidebar:
        st.divider()
        with st.expander("Basemap", expanded=False):
            st.selectbox(
                "Basemap",
                options=list(MAP_BASEMAP_OPTIONS),
                format_func=lambda k: MAP_BASEMAP_LABELS.get(k, k),
                key=STREAMLIT_MAP_BASEMAP_KEY,
                on_change=_on_basemap_changed,
            )
        with st.expander("Colour schemes", expanded=False):
            _scheme_sel = st.radio(
                "Map marker colour scheme",
                options=[1, 2, 3],
                format_func=lambda n: _scheme_preset_labels[int(n)],
                key=STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY,
                on_change=invalidate_folium_map_embed_cache,
                width="stretch",
            )
            family_colour_scheme = int(_scheme_sel if _scheme_sel is not None else 1)
        _src = str(st.session_state.get(SETTINGS_CONFIG_SOURCE_KEY, "") or "").strip()
        _map_height_help = (
            "Changes the map height for this session. Save a default in Settings if needed."
            if settings_yaml_path_for_source(REPO_ROOT, _src)
            else "Changes the map height."
        )
        map_height = st.slider(
            "Map height (px)",
            min_value=MAP_HEIGHT_PX_MIN,
            max_value=MAP_HEIGHT_PX_MAX,
            step=MAP_HEIGHT_PX_STEP,
            key=STREAMLIT_MAP_HEIGHT_PX_KEY,
            help=_map_height_help,
        )

    prev_effective = st.session_state.get(SESSION_PREV_EFFECTIVE_BASEMAP_KEY)
    if prev_effective != map_style:
        st.session_state[SESSION_PREV_EFFECTIVE_BASEMAP_KEY] = map_style
        invalidate_folium_map_embed_cache()

    if _prev_mv is not None and _prev_mv != map_view_mode:
        st.session_state.pop(FOLIUM_STATIC_MAP_CACHE_KEY, None)
        st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
        st.session_state[FOLIUM_MAP_MOUNT_NONCE_KEY] = int(
            st.session_state.get(FOLIUM_MAP_MOUNT_NONCE_KEY, 0)
        ) + 1

    st.session_state[SESSION_PREV_MAP_VIEW_KEY] = map_view_mode

    with st.sidebar:
        render_explorer_perf_sidebar_panel()

    return MapWorkingContext(
        map_style=map_style,
        map_view_mode=map_view_mode,
        is_lifer_view=is_lifer_view,
        date_filter_banner=date_filter_banner,
        work_df=work_df,
        hide_non_matching_locations=hide_non_matching_locations,
        species_pick_common=species_pick_common,
        species_pick_sci=species_pick_sci,
        map_height=map_height,
        family_name=str(family_name or ""),
        family_highlight_base=str(family_highlight_base or ""),
        family_colour_scheme=int(family_colour_scheme),
    )

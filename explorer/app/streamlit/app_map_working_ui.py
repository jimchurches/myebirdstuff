"""Map sidebar controls (basemap, view, dates, species) + working set resolution (refs #131)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from explorer.app.streamlit.app_constants import (
    EBIRD_DATA_SIG_KEY,
    EXPLORER_MAP_HTML_BYTES_KEY,
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
    SESSION_SPECIES_GROUP_PENDING_KEY,
    SESSION_SPECIES_GROUP_SEL_COMMIT_KEY,
    SESSION_SPECIES_GROUP_SPECIES_SELECT_KEY,
    SESSION_SPECIES_SEARCH_KEY,
    SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY,
    SESSION_SPECIES_WS_KEY,
    STREAMLIT_MAP_BASEMAP_KEY,
    STREAMLIT_MAP_BASEMAP_SAVED_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
    STREAMLIT_MAP_DATE_FILTER_KEY,
    STREAMLIT_MAP_DATE_RANGE_KEY,
    STREAMLIT_MAP_HEIGHT_PX_KEY,
    STREAMLIT_MAP_VIEW_LABEL_KEY,
    SESSION_PREV_EFFECTIVE_BASEMAP_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
    STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
    STREAMLIT_SPECIES_HIDE_ONLY_KEY,
    STREAMLIT_FAMILY_MAP_COLOUR_SCHEME_KEY,
    STREAMLIT_FAMILY_MAP_FAMILY_KEY,
    STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY,
    DEFAULT_TAXONOMY_LOCALE,
)
from explorer.app.streamlit.app_map_ui import (
    ensure_streamlit_map_basemap_height_keys,
    inject_sidebar_control_label_css,
    inject_spinner_theme_css,
    species_searchbox_fragment,
)
from explorer.app.streamlit.app_settings_state import apply_pending_map_cluster_toggle
from explorer.app.streamlit.app_settings_state import apply_pending_map_basemap_override
from explorer.app.streamlit.app_settings_state import apply_pending_map_height_override
from explorer.app.streamlit.defaults import (
    FAMILY_MAP_COLOUR_SCHEME_1,
    FAMILY_MAP_COLOUR_SCHEME_2,
    MAP_BASEMAP_LABELS,
    MAP_BASEMAP_OPTIONS,
    MAP_DATE_FILTER_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
    MAP_VIEW_LABELS,
)
from explorer.app.streamlit.map_working import (
    date_inception_to_today_default,
    streamlit_working_set_and_status,
)
from explorer.app.streamlit.streamlit_ui_constants import SPECIES_SEARCH_CAPTION
from explorer.core.species_search import (
    build_ram_species_whoosh_index,
    taxonomy_group_names_in_working_set,
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

    apply_pending_map_cluster_toggle(st.session_state)
    apply_pending_map_basemap_override(st.session_state)
    apply_pending_map_height_override(st.session_state)

    inject_spinner_theme_css()
    inject_sidebar_control_label_css()

    with st.sidebar:
        st.header("Map")
        saved_basemap = st.session_state.get(STREAMLIT_MAP_BASEMAP_SAVED_KEY, MAP_BASEMAP_OPTIONS[0])
        if saved_basemap not in MAP_BASEMAP_OPTIONS:
            saved_basemap = MAP_BASEMAP_OPTIONS[0]
        override = st.session_state.get(STREAMLIT_MAP_BASEMAP_KEY, "__default__")
        map_style = override if override in MAP_BASEMAP_OPTIONS else saved_basemap

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
                help="Turn on to limit the map and checklist stats to a date range.",
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
                "Group nearby pins",
                key=STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                help="Clusters nearby pins at low zoom. Session-only (save in Settings to persist).",
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
        tax_loc = (
            str(st.session_state.get(STREAMLIT_TAXONOMY_LOCALE_KEY, "")).strip()
            or DEFAULT_TAXONOMY_LOCALE
        )
        group_names = taxonomy_group_names_in_working_set(ws.species_list, ws.name_map, tax_loc)
        _ix_sig = (len(ws.species_list), st.session_state.get(EBIRD_DATA_SIG_KEY), tax_loc)
        if st.session_state.get(SESSION_SPECIES_IX_SIG_KEY) != _ix_sig:
            st.session_state[SESSION_SPECIES_IX_KEY] = build_ram_species_whoosh_index(
                ws.species_list,
                ws.name_map,
                taxonomy_group_names=group_names,
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
        st.session_state.pop(SESSION_SPECIES_GROUP_PENDING_KEY, None)
        st.session_state.pop(SESSION_SPECIES_GROUP_SEL_COMMIT_KEY, None)
        st.session_state.pop(SESSION_SPECIES_GROUP_SPECIES_SELECT_KEY, None)

    if map_view_mode == "families":
        from explorer.app.streamlit.app_caches import cached_family_map_bundle
        from explorer.core.family_map_compute import (
            filter_work_to_family,
            highlight_species_choices_alphabetical,
        )

        with st.sidebar:

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

            family_colour_scheme = int(
                st.radio(
                    "Colour scheme",
                    options=[1, 2],
                    format_func=lambda n: (
                        FAMILY_MAP_COLOUR_SCHEME_1.display_name
                        if n == 1
                        else FAMILY_MAP_COLOUR_SCHEME_2.display_name
                    ),
                    horizontal=True,
                    key=STREAMLIT_FAMILY_MAP_COLOUR_SCHEME_KEY,
                    index=0,
                    on_change=invalidate_folium_map_embed_cache,
                )
            )

    with st.sidebar:
        st.divider()
        with st.expander("Basemap", expanded=False):
            st.selectbox(
                "Basemap",
                options=["__default__"] + list(MAP_BASEMAP_OPTIONS),
                format_func=lambda k: (
                    f"Use default ({MAP_BASEMAP_LABELS.get(saved_basemap, saved_basemap)})"
                    if k == "__default__"
                    else MAP_BASEMAP_LABELS.get(k, k)
                ),
                key=STREAMLIT_MAP_BASEMAP_KEY,
                on_change=_on_basemap_changed,
            )
        map_height = st.slider(
            "Map height (px)",
            min_value=MAP_HEIGHT_PX_MIN,
            max_value=MAP_HEIGHT_PX_MAX,
            step=MAP_HEIGHT_PX_STEP,
            key=STREAMLIT_MAP_HEIGHT_PX_KEY,
            help="Session-only quick adjust. Set a saved default under Settings -> Map display.",
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

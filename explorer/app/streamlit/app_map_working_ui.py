"""Map sidebar controls (basemap, view, dates, species) and working-set resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from explorer.app.streamlit.app_constants import (
    DEFAULT_TAXONOMY_LOCALE,
    EBIRD_DATA_SIG_KEY,
    EXPLORER_MAP_HTML_BYTES_KEY,
    LEAFLET_EXPORT_BUILT_CACHE_KEY,
    LEAFLET_EXPORT_RECIPE_KEY,
    LEAFLET_MAP_MOUNT_NONCE_KEY,
    MAP_VIEW_LABEL_TO_MODE,
    PERSIST_MAP_DATE_FILTER_KEY,
    PERSIST_MAP_DATE_RANGE_KEY,
    PERSIST_SPECIES_COMMON_KEY,
    PERSIST_SPECIES_SCI_KEY,
    REPO_ROOT,
    SESSION_PREV_EFFECTIVE_BASEMAP_KEY,
    SESSION_PREV_MAP_VIEW_KEY,
    SESSION_SPECIES_IX_KEY,
    SESSION_SPECIES_IX_SIG_KEY,
    SESSION_SPECIES_PICK_KEY,
    SESSION_SPECIES_SEARCH_KEY,
    SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY,
    SESSION_SPECIES_WS_KEY,
    SETTINGS_CONFIG_SOURCE_KEY,
    STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
    STREAMLIT_FAMILY_MAP_FAMILY_KEY,
    STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY,
    STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
    STREAMLIT_MAP_BASEMAP_KEY,
    STREAMLIT_MAP_BASEMAP_SAVED_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
    STREAMLIT_MAP_DATE_FILTER_KEY,
    STREAMLIT_MAP_DATE_RANGE_KEY,
    STREAMLIT_MAP_HEIGHT_PX_KEY,
    STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY,
    STREAMLIT_MAP_VIEW_LABEL_KEY,
    STREAMLIT_SPECIES_HIDE_ONLY_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
)
from explorer.app.streamlit.app_go_to_gps_ui import render_go_to_gps_sidebar_expander
from explorer.app.streamlit.app_main_tab_ui import is_social_cards_main_tab
from explorer.app.streamlit.app_map_ui import (
    ensure_streamlit_map_basemap_height_keys,
    ensure_streamlit_map_marker_colour_scheme_keys,
    inject_spinner_theme_css,
    species_searchbox_fragment,
)
from explorer.app.streamlit.app_settings_state import (
    apply_pending_map_basemap_override,
    apply_pending_map_cluster_toggle,
    apply_pending_map_height_override,
    apply_pending_map_marker_colour_scheme,
)
from explorer.app.streamlit.app_social_cards_sidebar_ui import (
    render_social_cards_main_sidebar,
)
from explorer.app.streamlit.defaults import (
    MAP_BASEMAP_LABELS,
    MAP_BASEMAP_OPTIONS,
    MAP_DATE_FILTER_DEFAULT,
    MAP_HEIGHT_PX_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
    MAP_MARKER_COLOUR_SCHEME_1,
    MAP_MARKER_COLOUR_SCHEME_2,
    MAP_MARKER_COLOUR_SCHEME_3,
    MAP_SPECIES_HIDE_ONLY_DEFAULT,
    MAP_VIEW_LABELS,
)
from explorer.app.streamlit.map_working import (
    date_inception_to_today_default,
    streamlit_working_set_and_status,
)
from explorer.app.streamlit.perf_instrumentation import (
    render_explorer_perf_sidebar_panel,
)
from explorer.app.streamlit.streamlit_ui_constants import (
    MAP_DATE_FILTER_ALL_LOCATIONS_CAPTION,
    MAP_DATE_FILTER_SPECIES_MARKERS_CAPTION,
    MAP_DATE_FILTER_SPECIES_SIGHTINGS_CAPTION,
    SPECIES_SEARCH_CAPTION,
    SPECIES_SEARCH_HELP_EXPANDER_LABEL,
)
from explorer.core.all_locations_viewport import (
    ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ALL_LOCATIONS_FRAMING_FIT_ALL,
    ALL_LOCATIONS_SCOPE_FOCUSED,
    all_locations_scope_option_values,
)
from explorer.core.explorer_paths import settings_yaml_path_for_source
from explorer.core.region_display import map_focus_key_for_display
from explorer.core.species_search import (
    SPECIES_WHOOSH_INDEX_VERSION,
    build_ram_species_whoosh_index,
)


def _all_locations_leaflet_embed_active(session_state: Any) -> bool:
    """Prep renders the custom Leaflet component (not Folium) for unfiltered All locations."""
    label = session_state.get(STREAMLIT_MAP_VIEW_LABEL_KEY, "")
    mode = MAP_VIEW_LABEL_TO_MODE.get(label, "")
    if mode != "all":
        return False
    sci = str(session_state.get(PERSIST_SPECIES_SCI_KEY, "") or "").strip()
    return not sci


def invalidate_map_embed_cache(*, bump_mount_nonce: bool = True) -> None:
    """Bump Leaflet component mount nonce and clear export HTML when map chrome changes."""
    if bump_mount_nonce:
        st.session_state[LEAFLET_MAP_MOUNT_NONCE_KEY] = (
            int(st.session_state.get(LEAFLET_MAP_MOUNT_NONCE_KEY, 0)) + 1
        )
    st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
    st.session_state.pop(LEAFLET_EXPORT_RECIPE_KEY, None)
    st.session_state.pop(LEAFLET_EXPORT_BUILT_CACHE_KEY, None)


def _on_basemap_changed() -> None:
    """Leaflet component swaps basemap tiles in-place; no remount required."""
    return


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


def _effective_map_style() -> str:
    """Basemap key from session, falling back to saved/default when invalid."""
    saved_basemap = st.session_state.get(
        STREAMLIT_MAP_BASEMAP_SAVED_KEY, MAP_BASEMAP_OPTIONS[0]
    )
    if saved_basemap not in MAP_BASEMAP_OPTIONS:
        saved_basemap = MAP_BASEMAP_OPTIONS[0]
    override = st.session_state.get(STREAMLIT_MAP_BASEMAP_KEY, saved_basemap)
    if override not in MAP_BASEMAP_OPTIONS:
        override = saved_basemap
    return override


def _map_view_from_session() -> tuple[str, str, bool, bool]:
    """Map view label/mode and lifer/family flags from session (legacy label migration)."""
    map_view_label = st.session_state.get(
        STREAMLIT_MAP_VIEW_LABEL_KEY, MAP_VIEW_LABELS[0]
    )
    if map_view_label == "Selected species":
        map_view_label = "Species locations"
    map_view_mode = MAP_VIEW_LABEL_TO_MODE.get(map_view_label, "all")
    is_lifer_view = map_view_mode == "lifers"
    is_family_view = map_view_mode == "families"
    return map_view_label, map_view_mode, is_lifer_view, is_family_view


def _date_filter_from_session(
    df_full: Any,
    *,
    is_lifer_view: bool,
    is_family_view: bool,
) -> tuple[bool, tuple | None]:
    """Date-filter toggle and clamped range from session; disabled for lifer/family views."""
    if is_lifer_view or is_family_view:
        return False, None
    if STREAMLIT_MAP_DATE_FILTER_KEY not in st.session_state:
        st.session_state[STREAMLIT_MAP_DATE_FILTER_KEY] = bool(
            st.session_state.get(PERSIST_MAP_DATE_FILTER_KEY, MAP_DATE_FILTER_DEFAULT)
        )
    date_filter_on_effective = bool(
        st.session_state.get(STREAMLIT_MAP_DATE_FILTER_KEY, False)
    )
    if not date_filter_on_effective:
        return False, None
    d_inception, today = date_inception_to_today_default(df_full)
    if STREAMLIT_MAP_DATE_RANGE_KEY not in st.session_state:
        st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = (d_inception, today)
    rng = st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY]
    if not isinstance(rng, tuple) or len(rng) != 2:
        return date_filter_on_effective, (d_inception, today)
    r0 = max(min(rng[0], today), d_inception)
    r1 = max(min(rng[1], today), d_inception)
    date_range_sel = (r0, r1) if r0 <= r1 else (r1, r0)
    return date_filter_on_effective, date_range_sel


def render_map_sidebar(df_full: Any, *, work_df: Any) -> None:
    """Map sidebar widgets only; map session keys persist when another main tab is active."""
    with st.sidebar:
        st.header("Map")
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
        elif is_family_view:
            # Family map view (v1): ignore date filter controls in the sidebar.
            pass
        else:
            if STREAMLIT_MAP_DATE_FILTER_KEY not in st.session_state:
                st.session_state[STREAMLIT_MAP_DATE_FILTER_KEY] = bool(
                    st.session_state.get(
                        PERSIST_MAP_DATE_FILTER_KEY, MAP_DATE_FILTER_DEFAULT
                    )
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
            )
            if date_filter_on_effective:
                d_inception, today = date_inception_to_today_default(df_full)
                if STREAMLIT_MAP_DATE_RANGE_KEY not in st.session_state:
                    st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = (
                        d_inception,
                        today,
                    )
                rng = st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY]
                if not isinstance(rng, tuple) or len(rng) != 2:
                    st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = (
                        d_inception,
                        today,
                    )
                else:
                    r0 = max(min(rng[0], today), d_inception)
                    r1 = max(min(rng[1], today), d_inception)
                    rng_val = (r0, r1) if r0 <= r1 else (r1, r0)
                    if rng_val != rng:
                        st.session_state[STREAMLIT_MAP_DATE_RANGE_KEY] = rng_val
                st.date_input(
                    "Date range",
                    min_value=d_inception,
                    max_value=today,
                    key=STREAMLIT_MAP_DATE_RANGE_KEY,
                )
                if map_view_mode == "species":
                    st.caption(MAP_DATE_FILTER_SPECIES_SIGHTINGS_CAPTION)
                    st.caption(MAP_DATE_FILTER_SPECIES_MARKERS_CAPTION)
                else:
                    st.caption(MAP_DATE_FILTER_ALL_LOCATIONS_CAPTION)

            date_filter_on_effective = bool(
                st.session_state.get(STREAMLIT_MAP_DATE_FILTER_KEY, False)
            )
            date_range_sel = (
                st.session_state.get(STREAMLIT_MAP_DATE_RANGE_KEY)
                if date_filter_on_effective
                else None
            )
            st.session_state[PERSIST_MAP_DATE_FILTER_KEY] = date_filter_on_effective
            if (
                date_filter_on_effective
                and isinstance(date_range_sel, tuple)
                and len(date_range_sel) == 2
            ):
                st.session_state[PERSIST_MAP_DATE_RANGE_KEY] = date_range_sel

        if map_view_mode == "all":
            st.toggle(
                "Group nearby markers",
                key=STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                help="Groups nearby markers when zoomed out to reduce clutter.",
            )

    _, map_view_mode, _, _ = _map_view_from_session()

    if map_view_mode == "all":
        with st.sidebar:
            _scope_opts = all_locations_scope_option_values(work_df)
            _cur_scope = st.session_state.get(STREAMLIT_ALL_LOCATIONS_SCOPE_KEY)
            if _cur_scope not in _scope_opts:
                st.session_state[STREAMLIT_ALL_LOCATIONS_SCOPE_KEY] = (
                    ALL_LOCATIONS_SCOPE_FOCUSED
                )
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

    if map_view_mode == "species":
        with st.sidebar:
            st.markdown("**Species**")
            species_searchbox_fragment()
            if STREAMLIT_SPECIES_HIDE_ONLY_KEY not in st.session_state:
                st.session_state[STREAMLIT_SPECIES_HIDE_ONLY_KEY] = (
                    MAP_SPECIES_HIDE_ONLY_DEFAULT
                )
            st.toggle(
                "Show only selected species",
                key=STREAMLIT_SPECIES_HIDE_ONLY_KEY,
            )
            with st.expander(SPECIES_SEARCH_HELP_EXPANDER_LABEL, expanded=False):
                for _para in (p.strip() for p in SPECIES_SEARCH_CAPTION.split("\n\n")):
                    if _para:
                        st.caption(_para)
            render_go_to_gps_sidebar_expander()

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

                st.selectbox(
                    "Family",
                    options=[""] + fams,
                    format_func=lambda x: "— Select a family —" if x == "" else x,
                    key=STREAMLIT_FAMILY_MAP_FAMILY_KEY,
                )

                family_name = st.session_state.get(STREAMLIT_FAMILY_MAP_FAMILY_KEY, "")
                if family_name and isinstance(work, pd.DataFrame) and not work.empty:
                    wf = filter_work_to_family(work, family_name)
                    pairs = highlight_species_choices_alphabetical(wf, base_to_common)
                    bases = [b for _lab, b in pairs]
                    st.selectbox(
                        "Highlight species (optional)",
                        options=[""] + bases,
                        format_func=lambda b: (
                            "— None —"
                            if b == ""
                            else (base_to_common.get(str(b).strip().lower()) or b)
                        ),
                        key=STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY,
                    )
                else:
                    st.selectbox(
                        "Highlight species (optional)",
                        options=["— None —"],
                        disabled=True,
                        key=f"{STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY}__disabled",
                    )

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
            st.radio(
                "Map marker colour scheme",
                options=[1, 2, 3],
                format_func=lambda n: _scheme_preset_labels[int(n)],
                key=STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY,
                on_change=invalidate_map_embed_cache,
                width="stretch",
            )
        _src = str(st.session_state.get(SETTINGS_CONFIG_SOURCE_KEY, "") or "").strip()
        _map_height_help = (
            "Changes the map height for this session. Save a default in Settings if needed."
            if settings_yaml_path_for_source(REPO_ROOT, _src)
            else "Changes the map height."
        )
        st.slider(
            "Map height (px)",
            min_value=MAP_HEIGHT_PX_MIN,
            max_value=MAP_HEIGHT_PX_MAX,
            step=MAP_HEIGHT_PX_STEP,
            key=STREAMLIT_MAP_HEIGHT_PX_KEY,
            help=_map_height_help,
        )

    with st.sidebar:
        render_explorer_perf_sidebar_panel()


def render_map_sidebar_and_working_set(df_full: Any) -> MapWorkingContext:
    """Sidebar (map or Social Cards) plus working-set resolution for all main tabs."""
    ensure_streamlit_map_basemap_height_keys()
    ensure_streamlit_map_marker_colour_scheme_keys()

    apply_pending_map_cluster_toggle(st.session_state)
    apply_pending_map_basemap_override(st.session_state)
    apply_pending_map_height_override(st.session_state)
    apply_pending_map_marker_colour_scheme(st.session_state)

    # Every rerun (including Social Cards): omit the ``<style>`` and spinner chrome reverts.
    inject_spinner_theme_css()

    social_cards_tab = is_social_cards_main_tab()
    if social_cards_tab:
        render_social_cards_main_sidebar(df_full)

    map_style = _effective_map_style()
    _map_view_label, map_view_mode, is_lifer_view, is_family_view = (
        _map_view_from_session()
    )
    date_filter_on_effective, date_range_sel = _date_filter_from_session(
        df_full,
        is_lifer_view=is_lifer_view,
        is_family_view=is_family_view,
    )

    _ws_mode = "all" if is_family_view else map_view_mode
    ws, date_filter_banner = streamlit_working_set_and_status(
        df_full,
        map_view_mode=_ws_mode,
        date_filter_on=date_filter_on_effective,
        date_range=date_range_sel,
    )
    if ws is None:
        st.error("Invalid date range. Using all-time data for this run.")
        ws, date_filter_banner = streamlit_working_set_and_status(
            df_full,
            map_view_mode=map_view_mode,
            date_filter_on=False,
            date_range=None,
        )
    work_df = ws.df

    # Species session prep must run BEFORE the sidebar renders: the searchbox
    # fragment renders nothing when SESSION_SPECIES_IX_KEY is absent, and the
    # stale-search-key clearing must not run under an already-rendered fragment
    # (#362 — species search controls disappeared in the 2026-07-17 release).
    prev_map_view_mode = st.session_state.get(SESSION_PREV_MAP_VIEW_KEY)
    if map_view_mode == "species":
        if prev_map_view_mode is not None and prev_map_view_mode != "species":
            st.session_state.pop(SESSION_SPECIES_SEARCH_KEY, None)
            remount_nonce = int(
                st.session_state.get(SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY, 0)
            )
            st.session_state.pop(
                f"{SESSION_SPECIES_SEARCH_KEY}__v{remount_nonce}", None
            )
            st.session_state.pop(SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY, None)

        if not st.session_state.get(SESSION_SPECIES_PICK_KEY):
            persisted_common = st.session_state.get(PERSIST_SPECIES_COMMON_KEY)
            if persisted_common:
                st.session_state[SESSION_SPECIES_PICK_KEY] = str(
                    persisted_common
                ).strip()

        tax_loc = (
            str(st.session_state.get(STREAMLIT_TAXONOMY_LOCALE_KEY, "")).strip()
            or DEFAULT_TAXONOMY_LOCALE
        )
        index_signature = (
            SPECIES_WHOOSH_INDEX_VERSION,
            len(ws.species_list),
            st.session_state.get(EBIRD_DATA_SIG_KEY),
            tax_loc,
        )
        if st.session_state.get(SESSION_SPECIES_IX_SIG_KEY) != index_signature:
            st.session_state[SESSION_SPECIES_IX_KEY] = build_ram_species_whoosh_index(
                ws.species_list,
                ws.name_map,
                taxonomy_locale=tax_loc,
            )
            st.session_state[SESSION_SPECIES_IX_SIG_KEY] = index_signature
        st.session_state[SESSION_SPECIES_WS_KEY] = ws

    if not social_cards_tab:
        render_map_sidebar(df_full, work_df=work_df)

    hide_non_matching_locations = False
    species_pick_common: str | None = None
    species_pick_sci = ""
    family_name = ""
    family_highlight_base = ""
    scheme_sel = st.session_state.get(STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY, 1)
    family_colour_scheme = int(scheme_sel if scheme_sel is not None else 1)
    map_height = int(
        st.session_state.get(STREAMLIT_MAP_HEIGHT_PX_KEY, MAP_HEIGHT_PX_DEFAULT)
    )

    if map_view_mode == "species":
        hide_non_matching_locations = bool(
            st.session_state.get(
                STREAMLIT_SPECIES_HIDE_ONLY_KEY, MAP_SPECIES_HIDE_ONLY_DEFAULT
            )
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

    if map_view_mode == "families":
        family_name = str(
            st.session_state.get(STREAMLIT_FAMILY_MAP_FAMILY_KEY, "") or ""
        )
        family_highlight_base = str(
            st.session_state.get(STREAMLIT_FAMILY_MAP_HIGHLIGHT_KEY, "") or ""
        )

    prev_effective = st.session_state.get(SESSION_PREV_EFFECTIVE_BASEMAP_KEY)
    if prev_effective != map_style:
        st.session_state[SESSION_PREV_EFFECTIVE_BASEMAP_KEY] = map_style
        if not _all_locations_leaflet_embed_active(st.session_state):
            invalidate_map_embed_cache()

    if prev_map_view_mode is not None and prev_map_view_mode != map_view_mode:
        st.session_state[LEAFLET_MAP_MOUNT_NONCE_KEY] = (
            int(st.session_state.get(LEAFLET_MAP_MOUNT_NONCE_KEY, 0)) + 1
        )

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
        family_name=family_name,
        family_highlight_base=family_highlight_base,
        family_colour_scheme=family_colour_scheme,
    )

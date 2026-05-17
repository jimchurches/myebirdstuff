"""Sidebar prep spinners (map-first, then checklist / rankings / tab sync) and Map tab embed.

Map build runs under the first spinner so the map can render before heavy checklist/rankings caches
(map builds before heavy checklist/rankings caches). **All locations**, **Lifer locations**, **Species locations**, and **Family locations** use the
Leaflet Streamlit custom component; other modes use Folium + ``st_folium``. Tab session sync runs in a second spinner so
other tabs get payloads before fragments run. Partial ``@st.fragment`` reruns do not use this path.

**Export map HTML** uses :func:`~explorer.app.streamlit.map_working.folium_map_to_html_bytes` on a
**deep-copied** Folium map (``branca`` mutates on render), with ``html_bytes`` cached on hit. The live
Folium map uses **streamlit-folium** ``st_folium`` with a **deep copy** of the cached map so embed
rendering cannot strip layers from the session cache. Session :data:`FOLIUM_STATIC_MAP_CACHE_KEY`
stores unrendered Folium :class:`folium.Map` entries for the LRU. Leaflet GeoJSON payloads are cached under
:data:`ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY`, :data:`LIFER_LEAFLET_PAYLOAD_CACHE_KEY`, and
:data:`SPECIES_LEAFLET_PAYLOAD_CACHE_KEY`, and :data:`FAMILY_LEAFLET_PAYLOAD_CACHE_KEY`.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from collections import OrderedDict
from typing import Any, Callable, Literal

import streamlit as st

from explorer.app.streamlit.app_caches import (
    cached_checklist_stats_payload,
    cached_family_map_bundle,
    cached_full_export_checklist_stats_payload,
    cached_sex_notation_by_year,
    full_location_data_for_maintenance,
    static_map_cache_key,
)
from explorer.app.streamlit.app_constants import (
    ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
    FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
    LIFER_LEAFLET_PAYLOAD_CACHE_KEY,
    SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
    EBIRD_DATA_SIG_KEY,
    EXPLORER_MAP_HTML_BYTES_KEY,
    EXPORT_MAP_HTML_BTN_KEY,
    FILTERED_BY_LOC_CACHE_KEY,
    FOLIUM_MAP_MOUNT_NONCE_KEY,
    FOLIUM_STATIC_MAP_CACHE_KEY,
    POPUP_FRAGMENT_CACHE_KEY,
    POPUP_HTML_CACHE_KEY,
    STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
    STREAMLIT_CLOSE_LOCATION_METERS_KEY,
    STREAMLIT_COUNTRY_TAB_SORT_KEY,
    STREAMLIT_HIGH_COUNT_SORT_KEY,
    STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
    STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
    STREAMLIT_BLANK_MAP_DEFAULT_VIEWPORT_RECIPE_KEY,
    STREAMLIT_MAP_DATE_FILTER_KEY,
    STREAMLIT_RANKINGS_TOP_N_KEY,
)
from explorer.app.streamlit.app_go_to_gps_ui import go_to_gps_pin_from_session
from explorer.app.streamlit.app_map_ui import (
    inject_map_folium_iframe_min_height_css,
    inject_sidebar_outline_download_button_css,
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
    MAP_EXPORT_HTML_FILENAME,
    MAP_PREP_SPINNER_TEXT,
    SIDEBAR_FOOTER_LINK_HEX,
    TAB_PREP_SPINNER_TEXT,
)
from explorer.app.streamlit.perf_instrumentation import perf_record_point, perf_span
from explorer.app.streamlit.yearly_summary_streamlit_html import sync_yearly_summary_session_inputs
from explorer.core.all_locations_viewport import (
    ALL_LOCATIONS_FOCUS_ALL,
    ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ALL_LOCATIONS_FRAMING_FIT_ALL,
    ALL_LOCATIONS_SCOPE_FOCUSED,
    coordinate_pairs_focused_viewport,
    coordinate_pairs_for_viewport,
    location_id_to_country_map,
    mean_center_from_pairs,
    observation_row_counts_by_country_key,
)
from explorer.core.lifer_locations_geojson import build_lifer_locations_geojson_payload
from explorer.core.lifer_last_seen_prep import count_subspecies_lifer_taxa
from explorer.core.map_controller import build_species_overlay_map
from explorer.core.map_marker_colour_resolve import (
    resolve_lifer_overlay_pin_params,
    resolve_species_visit_pin,
)
from explorer.core.map_overlay_lifer_map import lifer_leaflet_viewport_recipe
from explorer.core.family_locations_geojson import build_family_locations_geojson_payload
from explorer.core.map_overlay_visit_map import (
    all_locations_leaflet_viewport_recipe,
    family_leaflet_viewport_recipe,
    species_leaflet_viewport_recipe,
)
from explorer.core.species_locations_geojson import (
    build_species_locations_geojson_payload,
    compute_species_map_banner_fields,
)
from explorer.core.map_prep import (
    data_signature_for_caches,
    prepare_all_locations_map_context,
)
from explorer.core.settings_schema_defaults import MAP_CLUSTER_ALL_LOCATIONS_DEFAULT
from explorer.core.species_logic import base_species_for_lifer, filter_species
from explorer.core.family_map_compute import (
    build_family_location_pins,
    compute_family_map_banner_metrics,
    filter_work_to_family,
    selected_species_checklist_individual_counts,
)
from explorer.app.streamlit.defaults import (
    MAP_ALL_LOCATIONS_CENTRE_OF_GRAVITY_ZOOM,
    MAP_ALL_LOCATIONS_FIT_BOUNDS_MAX_ZOOM,
    MAP_ALL_LOCATIONS_FIT_BOUNDS_PADDING_PX,
    MAP_ALL_LOCATIONS_FOCUSED_MIN_OBSERVATIONS_PER_COUNTRY,
    MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_HIGH,
    MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_LOW,
    MAP_ALL_LOCATIONS_SINGLE_POINT_ZOOM,
    MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
    MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
    MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS,
    MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
    MAP_SPECIES_DEFAULT_CENTER_LAT,
    MAP_SPECIES_DEFAULT_CENTER_LON,
    MAP_SPECIES_DEFAULT_ZOOM,
    active_map_marker_colour_scheme,
)
from explorer.core.family_map_folium import (
    build_family_map_banner_overlay_html,
    build_family_map_legend_overlay_html_for_pins,
)
from explorer.components.all_locations_map import render_all_locations_map_component
from explorer.core.all_locations_experimental_marker_style import (
    circle_marker_style_for_all_locations_map,
    cluster_icon_style_for_all_locations_map,
)
from explorer.core.all_locations_geojson import build_all_locations_geojson_payload
from explorer.presentation.map_renderer import (
    STREAMLIT_COMPONENT_MAP_LEGEND_STYLE,
    build_all_locations_banner_html,
    build_lifer_locations_banner_html,
    build_legend_html,
    build_species_banner_html,
    build_species_locations_awaiting_selection_banner_html,
    map_overlay_theme_stylesheet,
)


_MAP_RENDER_CACHE_MAX_ENTRIES = 6
# Species map: cache hide-only vs all-locations payloads separately (toggle thrashes a single slot).
_SPECIES_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES = 2
_FAMILY_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES = 4


def _leaflet_payload_cache_lookup(
    session_key: str,
    payload_cache_key: tuple[Any, ...],
) -> dict[str, Any] | None:
    """LRU lookup for Leaflet GeoJSON session caches keyed by ``payload_cache_key``."""
    cached = st.session_state.get(session_key)
    if isinstance(cached, OrderedDict):
        entry = cached.get(payload_cache_key)
        if isinstance(entry, dict):
            cached.move_to_end(payload_cache_key)
            return entry
        return None
    if isinstance(cached, dict) and cached.get("payload_cache_key") == payload_cache_key:
        return cached
    return None


def _leaflet_payload_cache_store(
    session_key: str,
    payload_cache_key: tuple[Any, ...],
    entry: dict[str, Any],
    *,
    max_entries: int,
) -> None:
    """Store Leaflet payload; keep at most *max_entries* variants (e.g. hide-only on/off)."""
    cached = st.session_state.get(session_key)
    if not isinstance(cached, OrderedDict):
        converted: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
        if isinstance(cached, dict) and cached.get("payload_cache_key") is not None:
            legacy_key = cached["payload_cache_key"]
            if isinstance(legacy_key, tuple):
                converted[legacy_key] = cached
        cached = converted
    cached[payload_cache_key] = entry
    cached.move_to_end(payload_cache_key)
    while len(cached) > max_entries:
        cached.popitem(last=False)
    st.session_state[session_key] = cached


def _map_cache_lookup(cache_key: tuple[Any, ...]) -> dict[str, Any] | None:
    """Session map cache lookup with backward compatibility for old single-entry payloads."""
    cached = st.session_state.get(FOLIUM_STATIC_MAP_CACHE_KEY)
    if isinstance(cached, OrderedDict):
        entry = cached.get(cache_key)
        if isinstance(entry, dict):
            cached.move_to_end(cache_key)
            return entry
        return None
    if isinstance(cached, dict) and cached.get("key") == cache_key:
        return cached
    return None


def _map_cache_store(cache_key: tuple[Any, ...], entry: dict[str, Any]) -> None:
    """Store/refresh a map cache entry and keep an LRU cap."""
    cached = st.session_state.get(FOLIUM_STATIC_MAP_CACHE_KEY)
    if not isinstance(cached, OrderedDict):
        converted: OrderedDict = OrderedDict()
        if isinstance(cached, dict) and cached.get("key") is not None:
            converted[cached["key"]] = cached
        cached = converted
    cached[cache_key] = entry
    cached.move_to_end(cache_key)
    while len(cached) > _MAP_RENDER_CACHE_MAX_ENTRIES:
        cached.popitem(last=False)
    st.session_state[FOLIUM_STATIC_MAP_CACHE_KEY] = cached


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
    family_name: str,
    family_highlight_base: str,
    family_colour_scheme: int,
    hide_non_matching_locations: bool,
    popup_sort_order: Any,
    popup_scroll_hint: Any,
    mark_lifer: bool,
    mark_last_seen: bool,
    species_url_fn: Callable[..., str],
) -> None:
    """Run map prep first (spinner), then heavy tab caches + session sync (second spinner)."""
    with st.sidebar:
        sidebar_bottom_slot_start()
        with st.spinner(MAP_PREP_SPINNER_TEXT):
            _spinner_emoji_placeholder = place_spinner_emoji_strip()
            with perf_span("prep.data_signature"):
                prov_plain = provenance or ""
                sig = data_signature_for_caches(df_full, prov_plain)
                _prev_sig = st.session_state.get(EBIRD_DATA_SIG_KEY)
                if _prev_sig != sig:
                    perf_record_point(
                        "prep.data_sig_change",
                        extra={
                            "prev_present": _prev_sig is not None,
                            "prev_sig": list(_prev_sig) if isinstance(_prev_sig, tuple) else _prev_sig,
                            "new_sig": list(sig) if isinstance(sig, tuple) else sig,
                            "map_cache_entries_before_nuke": (
                                len(st.session_state[FOLIUM_STATIC_MAP_CACHE_KEY])
                                if isinstance(st.session_state.get(FOLIUM_STATIC_MAP_CACHE_KEY), OrderedDict)
                                else 0
                            ),
                        },
                    )
                    st.session_state[EBIRD_DATA_SIG_KEY] = sig
                    st.session_state[POPUP_HTML_CACHE_KEY] = {}
                    st.session_state[POPUP_FRAGMENT_CACHE_KEY] = {}
                    st.session_state[FILTERED_BY_LOC_CACHE_KEY] = OrderedDict()
                    st.session_state.pop(FOLIUM_STATIC_MAP_CACHE_KEY, None)
                    st.session_state.pop(ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY, None)
                    st.session_state.pop(LIFER_LEAFLET_PAYLOAD_CACHE_KEY, None)
                    st.session_state.pop(SPECIES_LEAFLET_PAYLOAD_CACHE_KEY, None)
                    st.session_state.pop(FAMILY_LEAFLET_PAYLOAD_CACHE_KEY, None)

            map_warning_text: str | None = None
            map_hint_text: str | None = None
            folium_st_key: str | None = None
            capture_all_locations_view = False
            try:
                with perf_span("prep.map_context_prepare"):
                    ctx = prepare_all_locations_map_context(work_df, full_df=df_full)
            except ValueError as e:
                map_warning_text = str(e)
                st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
            else:
                # Blank-map viewport recipe (session-only): same framing recipe as all-data All locations
                # for non-country scopes, so Species/Families blank maps match the initial data framing.
                _seed_recipe = {
                    "mode": "center_zoom",
                    "center": [float(MAP_SPECIES_DEFAULT_CENTER_LAT), float(MAP_SPECIES_DEFAULT_CENTER_LON)],
                    "zoom": int(MAP_SPECIES_DEFAULT_ZOOM),
                }
                _cached_recipe = st.session_state.get(STREAMLIT_BLANK_MAP_DEFAULT_VIEWPORT_RECIPE_KEY)
                blank_viewport_recipe = _cached_recipe if isinstance(_cached_recipe, dict) else _seed_recipe

                _date_filter_on = bool(st.session_state.get(STREAMLIT_MAP_DATE_FILTER_KEY, False))
                if map_view_mode == "all" and not _date_filter_on:
                    _scope = str(
                        st.session_state.get(
                            STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
                            ALL_LOCATIONS_SCOPE_FOCUSED,
                        )
                        or ALL_LOCATIONS_SCOPE_FOCUSED
                    ).strip()
                    _allowed_scopes = {
                        ALL_LOCATIONS_FRAMING_FIT_ALL,
                        ALL_LOCATIONS_SCOPE_FOCUSED,
                        ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
                    }
                    if _scope in _allowed_scopes:
                        _loc_c = location_id_to_country_map(ctx["df"])
                        _pairs: list[list[float]] = []
                        if _scope == ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY:
                            _pairs = coordinate_pairs_for_viewport(
                                ctx["effective_location_data"],
                                location_id_to_country=_loc_c,
                                focus_country=ALL_LOCATIONS_FOCUS_ALL,
                            )
                            _mc = mean_center_from_pairs(_pairs)
                            if _mc is not None:
                                blank_viewport_recipe = {
                                    "mode": "center_zoom",
                                    "center": [float(_mc[0]), float(_mc[1])],
                                    "zoom": int(MAP_ALL_LOCATIONS_CENTRE_OF_GRAVITY_ZOOM),
                                }
                        elif _scope == ALL_LOCATIONS_SCOPE_FOCUSED:
                            _min_c = int(MAP_ALL_LOCATIONS_FOCUSED_MIN_OBSERVATIONS_PER_COUNTRY)
                            _obs_by_c = observation_row_counts_by_country_key(ctx["df"]) if _min_c > 0 else {}
                            _pairs = coordinate_pairs_focused_viewport(
                                ctx["effective_location_data"],
                                location_id_to_country=_loc_c,
                                observation_counts_by_country=_obs_by_c,
                                quantile_low=MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_LOW,
                                quantile_high=MAP_ALL_LOCATIONS_FOCUSED_QUANTILE_HIGH,
                                min_observations_full_country=_min_c,
                            )
                        else:
                            _pairs = coordinate_pairs_for_viewport(
                                ctx["effective_location_data"],
                                location_id_to_country=_loc_c,
                                focus_country=ALL_LOCATIONS_FOCUS_ALL,
                            )
                        if _scope != ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY and _pairs:
                            blank_viewport_recipe = {
                                "mode": "fit_bounds",
                                "pairs": [[float(p[0]), float(p[1])] for p in _pairs],
                                "padding_px": int(MAP_ALL_LOCATIONS_FIT_BOUNDS_PADDING_PX),
                                "max_zoom": int(MAP_ALL_LOCATIONS_FIT_BOUNDS_MAX_ZOOM),
                                "single_point_zoom": int(MAP_ALL_LOCATIONS_SINGLE_POINT_ZOOM),
                            }
                        st.session_state[STREAMLIT_BLANK_MAP_DEFAULT_VIEWPORT_RECIPE_KEY] = blank_viewport_recipe

                use_all_locations_leaflet = False
                use_lifer_leaflet = False
                use_species_leaflet = False
                use_family_leaflet = False
                leaflet_revision: str | None = None
                leaflet_geojson: dict[str, Any] | None = None
                leaflet_cluster_opts: dict[str, Any] | None = None
                leaflet_circle_style: dict[str, Any] | None = None
                leaflet_cluster_icon_style: dict[str, Any] | None = None
                leaflet_viewport: dict[str, Any] | None = None
                all_locations_leaflet_banner_html = ""
                all_locations_leaflet_legend_html = ""

                if map_view_mode == "families":
                    use_family_leaflet = True
                    result_map = None
                    folium_st_key = None
                    result_warning = None
                    fam = (family_name or "").strip()
                    hl = (family_highlight_base or "").strip().lower()

                    with perf_span("prep.cached_family_map_bundle"):
                        bundle = cached_family_map_bundle(df_full, tax_locale_effective)
                    fams = set(bundle.get("families") or ())
                    work = bundle.get("work")
                    tax_merged = bundle.get("tax_merged")

                    _ck = static_map_cache_key(
                        work_df,
                        "families",
                        date_filter_banner,
                        map_style,
                        (fam, hl, int(map_height), int(family_colour_scheme)),
                        taxonomy_locale=tax_locale_effective,
                    )

                    leaflet_cluster_opts = {
                        "enabled": False,
                        "max_cluster_radius": MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
                        "disable_clustering_at_zoom": MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
                        "spiderfy_on_max_zoom": MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
                        "remove_outside_visible_bounds": (
                            MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS
                        ),
                    }
                    leaflet_circle_style = {}
                    leaflet_cluster_icon_style = {}
                    family_framing_pairs: list[list[float]] = []
                    family_highlight_framed = False
                    pins: tuple = ()
                    _visit_sch = active_map_marker_colour_scheme(int(family_colour_scheme))

                    revision_bundle = {
                        "family_leaflet": True,
                        "map_style": map_style,
                        "scheme": int(family_colour_scheme),
                        "fam": fam,
                        "hl": hl,
                    }
                    revision_extra_json = json.dumps(revision_bundle, sort_keys=True)
                    payload_cache_key = (_ck, revision_extra_json)

                    if not fam:
                        map_hint_text = "Select a family in the sidebar to load the map data"
                        all_locations_leaflet_banner_html = ""
                        all_locations_leaflet_legend_html = ""
                    elif fam not in fams or work is None or getattr(work, "empty", True):
                        map_hint_text = "No family data available (taxonomy may not have loaded)."
                        all_locations_leaflet_banner_html = ""
                        all_locations_leaflet_legend_html = ""
                    else:
                        map_hint_text = None
                        with perf_span("prep.family_map_composition_with_pins"):
                            wf = filter_work_to_family(work, fam)
                            metrics = (
                                compute_family_map_banner_metrics(work, fam, tax_merged)
                                if tax_merged is not None
                                else None
                            )
                            pins = build_family_location_pins(
                                wf,
                                highlight_base_species=hl or None,
                            )
                            base_to_common = bundle.get("base_to_common") or {}
                            hl_label = (base_to_common.get(hl) or hl) if hl else ""
                            sel_counts = (
                                selected_species_checklist_individual_counts(wf, hl)
                                if hl and metrics
                                else None
                            )
                            hl_species_url = None
                            if hl and hl_label:
                                _u = species_url_fn(hl_label)
                                hl_species_url = _u if _u else None
                            all_locations_leaflet_banner_html = (
                                build_family_map_banner_overlay_html(
                                    metrics,
                                    selected_species_n_checklists=sel_counts[0] if sel_counts else None,
                                    selected_species_n_individuals=sel_counts[1] if sel_counts else None,
                                    selected_species_display_name=hl_label or None,
                                    selected_species_url=hl_species_url,
                                )
                                if metrics
                                else ""
                            )
                            all_locations_leaflet_legend_html = build_family_map_legend_overlay_html_for_pins(
                                pins,
                                highlight_label=hl_label or None,
                                highlight_species_url=hl_species_url,
                                style=_visit_sch,
                            )

                    _perf_family: dict[str, Any] = {
                        "embed": "family_leaflet",
                        "map_view_mode": map_view_mode,
                        "payload_cache_hit": False,
                        "family_selected": bool(fam),
                    }
                    with perf_span("map.family_leaflet.payload", extra=_perf_family):
                        cached_fam = _leaflet_payload_cache_lookup(
                            FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
                            payload_cache_key,
                        )
                        if cached_fam is not None:
                            leaflet_revision = str(cached_fam["revision"])
                            leaflet_geojson = cached_fam["geojson"]
                            family_framing_pairs = list(cached_fam.get("framing_pairs") or [])
                            family_highlight_framed = bool(cached_fam.get("highlight_framed"))
                            _perf_family["payload_cache_hit"] = True
                        elif not fam or fam not in fams or work is None or getattr(work, "empty", True):
                            family_framing_pairs = []
                            empty_features: list[dict[str, Any]] = []
                            rev_payload = (
                                json.dumps(empty_features, separators=(",", ":"))
                                + "|"
                                + revision_extra_json
                            )
                            leaflet_revision = hashlib.sha256(
                                rev_payload.encode("utf-8")
                            ).hexdigest()[:24]
                            leaflet_geojson = {
                                "type": "FeatureCollection",
                                "features": empty_features,
                            }
                        else:
                            (
                                leaflet_revision,
                                leaflet_geojson,
                                family_framing_pairs,
                                family_highlight_framed,
                            ) = build_family_locations_geojson_payload(
                                pins,
                                visit_marker_scheme=_visit_sch,
                                location_page_url_fn=lambda lid: (
                                    f"https://ebird.org/lifelist/{lid}" if lid else None
                                ),
                                species_url_fn=species_url_fn,
                                fit_bounds_highlight_only=bool(hl),
                                revision_extra=revision_extra_json,
                            )
                            _leaflet_payload_cache_store(
                                FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
                                payload_cache_key,
                                {
                                    "revision": leaflet_revision,
                                    "geojson": leaflet_geojson,
                                    "framing_pairs": family_framing_pairs,
                                    "highlight_framed": family_highlight_framed,
                                },
                                max_entries=_FAMILY_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
                            )

                    if leaflet_revision and leaflet_geojson is not None:
                        leaflet_viewport = family_leaflet_viewport_recipe(
                            family_framing_pairs,
                            blank_viewport_recipe=blank_viewport_recipe,
                            highlight_framed=family_highlight_framed,
                        )
                    st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                else:
                    overlay_common = (
                        (species_pick_common or "").strip() if map_view_mode == "species" else ""
                    )
                    overlay_sci = (species_pick_sci or "").strip() if map_view_mode == "species" else ""
                    if map_view_mode == "species" and not overlay_sci:
                        map_hint_text = "Select a species in the sidebar to load the map data"
                    hide_nm = (
                        map_view_mode == "species" and bool(hide_non_matching_locations)
                    )
                    capture_all_locations_view = map_view_mode == "all" and not overlay_sci
                    use_all_locations_leaflet = capture_all_locations_view
                    use_lifer_leaflet = map_view_mode == "lifers"
                    use_species_leaflet = map_view_mode == "species"
                    _go_pin = go_to_gps_pin_from_session()
                    _visit_sch = active_map_marker_colour_scheme(int(family_colour_scheme))
                    _map_kw = {
                        **ctx,
                        "selected_species": overlay_sci,
                        "selected_common_name": overlay_common,
                        "map_style": map_style,
                        "popup_sort_order": popup_sort_order,
                        "popup_scroll_hint": popup_scroll_hint,
                        "mark_lifer": mark_lifer,
                        "mark_last_seen": mark_last_seen,
                        "cluster_all_locations": bool(
                            st.session_state.get(
                                STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                                MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
                            )
                        ),
                        # Banner: context + counts only; date filter remains in the sidebar.
                        "date_filter_status": "",
                        "species_url_fn": species_url_fn,
                        "base_species_fn": base_species_for_lifer,
                        "taxonomy_locale": tax_locale_effective,
                        "popup_html_cache": st.session_state.get(POPUP_HTML_CACHE_KEY),
                        "popup_fragment_cache": st.session_state.get(POPUP_FRAGMENT_CACHE_KEY),
                        "filtered_by_loc_cache": st.session_state.get(FILTERED_BY_LOC_CACHE_KEY),
                        "map_view_mode": map_view_mode,
                        "hide_non_matching_locations": hide_nm,
                        "show_subspecies_lifers": bool(
                            st.session_state.get(STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY, False)
                        ),
                        "map_height_px": int(map_height),
                        "visit_marker_scheme": _visit_sch,
                        "species_blank_default_center": tuple(blank_viewport_recipe.get("center", [MAP_SPECIES_DEFAULT_CENTER_LAT, MAP_SPECIES_DEFAULT_CENTER_LON])),
                        "species_blank_default_zoom": int(blank_viewport_recipe.get("zoom", MAP_SPECIES_DEFAULT_ZOOM)),
                        "species_blank_viewport_recipe": blank_viewport_recipe,
                        "go_to_gps_pin": _go_pin,
                    }
                    if capture_all_locations_view:
                        _valid = {
                            ALL_LOCATIONS_FRAMING_FIT_ALL,
                            ALL_LOCATIONS_SCOPE_FOCUSED,
                            ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
                        } | set(location_id_to_country_map(ctx["df"]).values())
                        _scope = str(
                            st.session_state.get(
                                STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
                                ALL_LOCATIONS_SCOPE_FOCUSED,
                            )
                            or ALL_LOCATIONS_SCOPE_FOCUSED
                        ).strip()
                        if _scope not in _valid:
                            _scope = ALL_LOCATIONS_SCOPE_FOCUSED
                            st.session_state[STREAMLIT_ALL_LOCATIONS_SCOPE_KEY] = _scope
                        _map_kw["all_locations_scope"] = _scope
                        _map_kw["all_locations_location_country"] = location_id_to_country_map(
                            ctx["df"]
                        )
                    _render_opts_sig = (
                        popup_sort_order,
                        popup_scroll_hint,
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
                        int(family_colour_scheme),
                        str(
                            st.session_state.get(
                                STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
                                ALL_LOCATIONS_SCOPE_FOCUSED,
                            )
                            or ALL_LOCATIONS_SCOPE_FOCUSED
                        )
                        if capture_all_locations_view
                        else "",
                    )
                    _species_selected = bool(overlay_sci)
                    _ck = static_map_cache_key(
                        work_df,
                        map_view_mode,
                        date_filter_banner,
                        map_style,
                        _render_opts_sig,
                        taxonomy_locale=tax_locale_effective,
                        species_selected_sci=overlay_sci if _species_selected else "",
                        species_selected_common=overlay_common if _species_selected else "",
                        hide_non_matching_locations=bool(hide_nm),
                        go_to_gps_pin=_go_pin,
                    )
                    _cache_at_lookup = st.session_state.get(FOLIUM_STATIC_MAP_CACHE_KEY)
                    perf_record_point(
                        "prep.map_cache_key_components",
                        extra={
                            "mode": map_view_mode,
                            "k_map_view_mode": _ck[0],
                            "k_date_filter_banner": _ck[1],
                            "k_map_style": _ck[2],
                            "k_render_opts_sig": list(_ck[3]),
                            "k_n": _ck[4],
                            "k_sid0": _ck[5],
                            "k_tax": _ck[6],
                            "k_sci": _ck[7],
                            "k_common": _ck[8],
                            "k_hide_nm": _ck[9],
                            "k_gps_sig": _ck[10],
                            "cache_entries_at_lookup": (
                                len(_cache_at_lookup)
                                if isinstance(_cache_at_lookup, OrderedDict)
                                else (1 if isinstance(_cache_at_lookup, dict) else 0)
                            ),
                        },
                    )
                    if use_all_locations_leaflet:
                        raw_vis = str(
                            os.environ.get("EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP", "") or ""
                        ).strip()
                        visits_inline_max: int | None = None
                        if raw_vis:
                            try:
                                n_vis = int(raw_vis)
                                visits_inline_max = n_vis if n_vis > 0 else None
                            except ValueError:
                                visits_inline_max = None
                        leaflet_circle_style = circle_marker_style_for_all_locations_map(
                            int(family_colour_scheme)
                        )
                        leaflet_cluster_icon_style = cluster_icon_style_for_all_locations_map(
                            int(family_colour_scheme)
                        )
                        leaflet_cluster_opts = {
                            "enabled": bool(
                                st.session_state.get(
                                    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                                    MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
                                )
                            ),
                            "max_cluster_radius": MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
                            "disable_clustering_at_zoom": MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
                            "spiderfy_on_max_zoom": MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
                            "remove_outside_visible_bounds": (
                                MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS
                            ),
                        }
                        leaflet_viewport = all_locations_leaflet_viewport_recipe(
                            effective_location_data=ctx["effective_location_data"],
                            df=ctx["df"],
                            all_locations_scope=_scope,
                            all_locations_location_country=location_id_to_country_map(ctx["df"]),
                            go_to_gps_pin=_go_pin,
                        )
                        revision_bundle = {
                            "circle_marker": leaflet_circle_style,
                            "cluster": leaflet_cluster_opts,
                            "cluster_icon_style": leaflet_cluster_icon_style,
                            "viewport": leaflet_viewport,
                        }
                        revision_extra_json = json.dumps(revision_bundle, sort_keys=True)
                        payload_cache_key = (_ck, revision_extra_json, visits_inline_max)
                        _perf_leaflet: dict[str, Any] = {
                            "embed": "all_locations_leaflet",
                            "map_view_mode": map_view_mode,
                            "payload_cache_hit": False,
                            "visits_inline_cap": visits_inline_max,
                        }
                        with perf_span("map.all_locations_leaflet.payload", extra=_perf_leaflet):
                            cached_pl = st.session_state.get(ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY)
                            if (
                                isinstance(cached_pl, dict)
                                and cached_pl.get("payload_cache_key") == payload_cache_key
                            ):
                                leaflet_revision = str(cached_pl["revision"])
                                leaflet_geojson = cached_pl["geojson"]
                                _perf_leaflet["payload_cache_hit"] = True
                            else:
                                loc_df = ctx["location_data"]
                                work = ctx["df"]
                                counts = work.groupby("Location ID")["Submission ID"].nunique()
                                popup_visit_dates_ascending = (
                                    str(popup_sort_order).strip().lower() != "descending"
                                )
                                leaflet_revision, leaflet_geojson = build_all_locations_geojson_payload(
                                    loc_df,
                                    checklist_counts_by_location=counts.to_dict(),
                                    records_by_location=ctx["records_by_loc"],
                                    popup_visit_dates_ascending=popup_visit_dates_ascending,
                                    visits_inline_max=visits_inline_max,
                                    omit_pin_colour=True,
                                    revision_extra=revision_extra_json,
                                )
                                st.session_state[ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY] = {
                                    "payload_cache_key": payload_cache_key,
                                    "revision": leaflet_revision,
                                    "geojson": leaflet_geojson,
                                }
                        n_loc, n_chk, n_sp, n_ind = ctx["effective_totals"]
                        all_locations_leaflet_banner_html = build_all_locations_banner_html(
                            n_loc,
                            n_chk,
                            n_sp,
                            n_ind,
                        )
                        _ls = str(leaflet_circle_style.get("stroke_hex") or "#1c2630")
                        _lf = str(leaflet_circle_style.get("fill_hex") or "#3388ff")
                        all_locations_leaflet_legend_html = build_legend_html(
                            [(_ls, _lf, "All locations")],
                            container_style=STREAMLIT_COMPONENT_MAP_LEGEND_STYLE,
                        )
                        result_map = None
                        result_warning = None
                        folium_st_key = None
                        st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                    elif use_lifer_leaflet:
                        result_warning = None
                        leaflet_cluster_opts = {
                            "enabled": False,
                            "max_cluster_radius": MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
                            "disable_clustering_at_zoom": MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
                            "spiderfy_on_max_zoom": MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
                            "remove_outside_visible_bounds": (
                                MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS
                            ),
                        }
                        leaflet_circle_style = {}
                        leaflet_cluster_icon_style = {}
                        subsp = bool(st.session_state.get(STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY, False))
                        revision_bundle = {
                            "lifer_leaflet": True,
                            "map_style": map_style,
                            "subspecies": subsp,
                            "scheme": int(family_colour_scheme),
                            "popup_sort": str(popup_sort_order),
                        }
                        revision_extra_json = json.dumps(revision_bundle, sort_keys=True)
                        payload_cache_key = (_ck, revision_extra_json)
                        lifer_framing_pairs: list[list[float]] = []
                        _perf_lifer: dict[str, Any] = {
                            "embed": "lifer_leaflet",
                            "map_view_mode": map_view_mode,
                            "payload_cache_hit": False,
                        }
                        with perf_span("map.lifer_leaflet.payload", extra=_perf_lifer):
                            cached_lif = st.session_state.get(LIFER_LEAFLET_PAYLOAD_CACHE_KEY)
                            if (
                                isinstance(cached_lif, dict)
                                and cached_lif.get("payload_cache_key") == payload_cache_key
                            ):
                                leaflet_revision = str(cached_lif["revision"])
                                leaflet_geojson = cached_lif["geojson"]
                                lifer_framing_pairs = list(cached_lif.get("framing_pairs") or [])
                                _perf_lifer["payload_cache_hit"] = True
                            else:
                                (
                                    leaflet_revision,
                                    leaflet_geojson,
                                    lifer_warn,
                                    lifer_framing_pairs,
                                ) = build_lifer_locations_geojson_payload(
                                    full_location_data=ctx["full_location_data"],
                                    lifer_lookup_df=ctx["lifer_lookup_df"],
                                    true_lifer_locations=ctx["true_lifer_locations"],
                                    true_lifer_locations_taxon=ctx["true_lifer_locations_taxon"],
                                    show_subspecies_lifers=subsp,
                                    base_species_fn=base_species_for_lifer,
                                    visit_marker_scheme=_visit_sch,
                                    revision_extra=revision_extra_json,
                                )
                                if lifer_warn:
                                    result_warning = lifer_warn
                                    leaflet_revision = None
                                    leaflet_geojson = None
                                    lifer_framing_pairs = []
                                else:
                                    st.session_state[LIFER_LEAFLET_PAYLOAD_CACHE_KEY] = {
                                        "payload_cache_key": payload_cache_key,
                                        "revision": leaflet_revision,
                                        "geojson": leaflet_geojson,
                                        "framing_pairs": lifer_framing_pairs,
                                    }
                            if leaflet_revision and leaflet_geojson is not None:
                                leaflet_viewport = lifer_leaflet_viewport_recipe(lifer_framing_pairs)
                                n_lifer_sp = len(ctx["true_lifer_locations"])
                                n_pin = len(leaflet_geojson.get("features") or [])
                                all_locations_leaflet_banner_html = build_lifer_locations_banner_html(
                                    n_lifer_sp,
                                    n_pin,
                                    include_subspecies=subsp,
                                    n_subspecies_lifers=(
                                        count_subspecies_lifer_taxa(
                                            ctx["lifer_lookup_df"],
                                            ctx["true_lifer_locations_taxon"],
                                        )
                                        if subsp
                                        else None
                                    ),
                                )
                                le, lf, se, sp, _rl, _rs, _sw, _fo1, _fo2 = (
                                    resolve_lifer_overlay_pin_params(_visit_sch)
                                )
                                if not subsp:
                                    all_locations_leaflet_legend_html = build_legend_html(
                                        [(le, lf, "Lifer")],
                                        container_style=STREAMLIT_COMPONENT_MAP_LEGEND_STYLE,
                                    )
                                else:
                                    kinds_present: set[str] = set()
                                    for f in leaflet_geojson.get("features") or []:
                                        pr = f.get("properties")
                                        if isinstance(pr, dict):
                                            pk = pr.get("pin_kind")
                                            if pk:
                                                kinds_present.add(str(pk))
                                    legend_rows: list[tuple[str, str, str]] = []
                                    if "lifer" in kinds_present:
                                        legend_rows.append((le, lf, "Lifer"))
                                    if "subspecies" in kinds_present:
                                        legend_rows.append((se, sp, "Subspecies"))
                                    all_locations_leaflet_legend_html = build_legend_html(
                                        legend_rows,
                                        container_style=STREAMLIT_COMPONENT_MAP_LEGEND_STYLE,
                                    )
                        result_map = None
                        folium_st_key = None
                        st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                    elif use_species_leaflet:
                        result_warning = None
                        leaflet_cluster_opts = {
                            "enabled": False,
                            "max_cluster_radius": MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
                            "disable_clustering_at_zoom": MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
                            "spiderfy_on_max_zoom": MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
                            "remove_outside_visible_bounds": (
                                MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS
                            ),
                        }
                        leaflet_circle_style = {}
                        leaflet_cluster_icon_style = {}
                        species_framing_pairs: list[list[float]] = []
                        species_pin_roles: set[str] = set()
                        revision_bundle = {
                            "species_leaflet": True,
                            "map_style": map_style,
                            "scheme": int(family_colour_scheme),
                            "popup_sort": str(popup_sort_order),
                            "hide_nm": bool(hide_nm),
                            "mark_lifer": bool(mark_lifer),
                            "mark_last_seen": bool(mark_last_seen),
                            "selected_sci": overlay_sci,
                        }
                        revision_extra_json = json.dumps(revision_bundle, sort_keys=True)
                        payload_cache_key = (_ck, revision_extra_json)
                        _perf_species: dict[str, Any] = {
                            "embed": "species_leaflet",
                            "map_view_mode": map_view_mode,
                            "payload_cache_hit": False,
                            "species_selected": bool(overlay_sci),
                        }
                        with perf_span("map.species_leaflet.payload", extra=_perf_species):
                            cached_sp = _leaflet_payload_cache_lookup(
                                SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
                                payload_cache_key,
                            )
                            if cached_sp is not None:
                                leaflet_revision = str(cached_sp["revision"])
                                leaflet_geojson = cached_sp["geojson"]
                                species_framing_pairs = list(cached_sp.get("framing_pairs") or [])
                                species_pin_roles = set(cached_sp.get("pin_roles") or [])
                                _perf_species["payload_cache_hit"] = True
                            elif not overlay_sci:
                                species_framing_pairs = []
                                empty_features: list[dict[str, Any]] = []
                                rev_payload = (
                                    json.dumps(empty_features, separators=(",", ":"))
                                    + "|"
                                    + revision_extra_json
                                )
                                leaflet_revision = hashlib.sha256(
                                    rev_payload.encode("utf-8")
                                ).hexdigest()[:24]
                                leaflet_geojson = {
                                    "type": "FeatureCollection",
                                    "features": empty_features,
                                }
                            else:
                                popup_visit_dates_ascending = (
                                    str(popup_sort_order).strip().lower() != "descending"
                                )
                                (
                                    leaflet_revision,
                                    leaflet_geojson,
                                    sp_warn,
                                    species_framing_pairs,
                                    pin_roles,
                                ) = build_species_locations_geojson_payload(
                                    df=ctx["df"],
                                    location_data=ctx["location_data"],
                                    records_by_loc=ctx["records_by_loc"],
                                    selected_species=overlay_sci,
                                    true_lifer_locations=ctx["true_lifer_locations"],
                                    true_lifer_locations_taxon=ctx["true_lifer_locations_taxon"],
                                    true_last_seen_locations=ctx["true_last_seen_locations"],
                                    true_last_seen_locations_taxon=ctx[
                                        "true_last_seen_locations_taxon"
                                    ],
                                    hide_non_matching_locations=bool(hide_nm),
                                    mark_lifer=bool(mark_lifer),
                                    mark_last_seen=bool(mark_last_seen),
                                    base_species_fn=base_species_for_lifer,
                                    visit_marker_scheme=_visit_sch,
                                    popup_visit_dates_ascending=popup_visit_dates_ascending,
                                    revision_extra=revision_extra_json,
                                )
                                if sp_warn:
                                    result_warning = sp_warn
                                    leaflet_revision = None
                                    leaflet_geojson = None
                                    species_framing_pairs = []
                                    pin_roles = set()
                                else:
                                    species_pin_roles = set(pin_roles)
                                    _leaflet_payload_cache_store(
                                        SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
                                        payload_cache_key,
                                        {
                                            "revision": leaflet_revision,
                                            "geojson": leaflet_geojson,
                                            "framing_pairs": species_framing_pairs,
                                            "pin_roles": sorted(species_pin_roles),
                                        },
                                        max_entries=_SPECIES_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
                                    )
                            if leaflet_revision and leaflet_geojson is not None:
                                leaflet_viewport = species_leaflet_viewport_recipe(
                                    species_framing_pairs,
                                    go_to_gps_pin=_go_pin,
                                    blank_viewport_recipe=blank_viewport_recipe
                                    if not overlay_sci
                                    else None,
                                )
                                if not overlay_sci:
                                    all_locations_leaflet_banner_html = (
                                        build_species_locations_awaiting_selection_banner_html()
                                    )
                                    all_locations_leaflet_legend_html = ""
                                else:
                                    _filtered_sp = filter_species(ctx["df"], overlay_sci)
                                    _banner_fields = compute_species_map_banner_fields(
                                        filtered=_filtered_sp,
                                        selected_species=overlay_sci,
                                        selected_common_name=overlay_common,
                                        lifer_lookup_df=ctx["lifer_lookup_df"],
                                        base_species_fn=base_species_for_lifer,
                                    )
                                    _sp_url = species_url_fn(_banner_fields["display_name"])
                                    all_locations_leaflet_banner_html = build_species_banner_html(
                                        species_url=_sp_url if _sp_url else None,
                                        date_filter_status="",
                                        **_banner_fields,
                                    )
                                    _legend_roles: list[
                                        tuple[str, Literal["lifer", "last_seen", "species", "default"]]
                                    ] = [
                                        ("Species", "species"),
                                        ("Locations", "default"),
                                        ("Lifer", "lifer"),
                                        ("Last seen", "last_seen"),
                                    ]
                                    legend_rows: list[tuple[str, str, str]] = []
                                    for _lbl, _role in _legend_roles:
                                        if _lbl not in species_pin_roles:
                                            continue
                                        e, f, _, _, _ = resolve_species_visit_pin(
                                            _visit_sch, _role
                                        )
                                        legend_rows.append((e, f, _lbl))
                                    all_locations_leaflet_legend_html = (
                                        build_legend_html(
                                            legend_rows,
                                            container_style=STREAMLIT_COMPONENT_MAP_LEGEND_STYLE,
                                        )
                                        if legend_rows
                                        else ""
                                    )
                        result_map = None
                        folium_st_key = None
                        st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                    else:
                        _cached = _map_cache_lookup(_ck)
                        if isinstance(_cached, dict) and _cached.get("map") is not None:
                            perf_record_point("prep.map_cache_hit", extra={"mode": map_view_mode})
                            result_map = _cached["map"]
                            result_warning = _cached.get("warning")
                        else:
                            perf_record_point("prep.map_cache_miss", extra={"mode": map_view_mode})
                            # Perf: split popup-build vs marker-count spans inside
                            # the same perf event. ``perf_span`` stamps ``extra`` by reference at
                            # finalize time, so mutations inside :func:`build_species_overlay_map`
                            # land on the emitted record.
                            _build_metrics: dict[str, Any] = {"mode": map_view_mode}
                            with perf_span(
                                "prep.build_species_overlay_map", extra=_build_metrics
                            ):
                                result = build_species_overlay_map(
                                    metrics_sink=_build_metrics, **_map_kw
                                )
                                result_map = result.map
                                result_warning = result.warning
                            if result_map is not None:
                                _map_cache_store(
                                    _ck,
                                    {
                                        "key": _ck,
                                        "map": result_map,
                                        "warning": result_warning,
                                    },
                                )
                                _cache_after = st.session_state.get(FOLIUM_STATIC_MAP_CACHE_KEY)
                                perf_record_point(
                                    "prep.map_cache_store",
                                    extra={
                                        "mode": map_view_mode,
                                        "site": "after_build_species_overlay_map",
                                        "cache_entries_after_store": (
                                            len(_cache_after)
                                            if isinstance(_cache_after, OrderedDict)
                                            else 0
                                        ),
                                    },
                                )

                if use_all_locations_leaflet and leaflet_revision and leaflet_geojson is not None:
                    pass
                elif use_lifer_leaflet and leaflet_revision and leaflet_geojson is not None:
                    pass
                elif use_species_leaflet and leaflet_revision and leaflet_geojson is not None:
                    pass
                elif use_family_leaflet and leaflet_revision and leaflet_geojson is not None:
                    pass
                elif result_warning:
                    map_warning_text = result_warning
                    st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                elif result_map is None:
                    map_warning_text = "Map could not be built."
                    st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
                else:
                    _cached_for_html = _map_cache_lookup(_ck)
                    _cached_html = (
                        _cached_for_html.get("html_bytes")
                        if isinstance(_cached_for_html, dict)
                        else None
                    )
                    if isinstance(_cached_html, (bytes, bytearray)):
                        perf_record_point("prep.map_html_cache_hit")
                        st.session_state[EXPLORER_MAP_HTML_BYTES_KEY] = bytes(_cached_html)
                    else:
                        perf_record_point("prep.map_html_cache_miss")
                        with perf_span("prep.folium_map_to_html_bytes"):
                            st.session_state[EXPLORER_MAP_HTML_BYTES_KEY] = folium_map_to_html_bytes(
                                copy.deepcopy(result_map)
                            )
                        if isinstance(_cached_for_html, dict):
                            _cached_for_html["html_bytes"] = st.session_state[EXPLORER_MAP_HTML_BYTES_KEY]
                            _map_cache_store(_ck, _cached_for_html)
                    folium_st_key = (
                        f"explorer_folium_{abs(hash(_ck))}_h{map_height}_mv{map_view_mode}_n"
                        f"{int(st.session_state.get(FOLIUM_MAP_MOUNT_NONCE_KEY, 0))}"
                    )

            with tab_map:
                if map_warning_text is not None:
                    st.warning(map_warning_text)
                elif (
                    (
                        use_all_locations_leaflet
                        or use_lifer_leaflet
                        or use_species_leaflet
                        or use_family_leaflet
                    )
                    and leaflet_revision
                    and leaflet_geojson is not None
                    and leaflet_cluster_opts is not None
                    and leaflet_circle_style is not None
                ):
                    inject_map_folium_iframe_min_height_css(map_height)
                    if map_hint_text:
                        st.info(map_hint_text)
                    _embed_extra: dict[str, Any] = {
                        "revision_prefix": leaflet_revision[:12],
                        "n_features": len(leaflet_geojson.get("features", [])),
                        "cluster_enabled": leaflet_cluster_opts.get("enabled"),
                    }
                    if use_lifer_leaflet:
                        _embed_extra["embed"] = "lifer_leaflet"
                        _span_name = "map.lifer_leaflet.component_embed"
                    elif use_species_leaflet:
                        _embed_extra["embed"] = "species_leaflet"
                        _span_name = "map.species_leaflet.component_embed"
                    elif use_family_leaflet:
                        _embed_extra["embed"] = "family_leaflet"
                        _span_name = "map.family_leaflet.component_embed"
                    else:
                        _embed_extra["embed"] = "all_locations_leaflet"
                        _embed_extra["map_view_mode"] = map_view_mode
                        _span_name = "map.all_locations_leaflet.component_embed"
                    with perf_span(_span_name, extra=_embed_extra):
                        render_all_locations_map_component(
                            revision=leaflet_revision,
                            geojson=leaflet_geojson,
                            height=int(map_height),
                            map_style=map_style,
                            cluster_options=leaflet_cluster_opts,
                            circle_marker_style=leaflet_circle_style,
                            cluster_icon_style=leaflet_cluster_icon_style or {},
                            viewport=leaflet_viewport or {},
                            map_theme_css=map_overlay_theme_stylesheet(),
                            banner_html=all_locations_leaflet_banner_html,
                            legend_html=all_locations_leaflet_legend_html,
                            key=(
                                f"explorer_{'lifer' if use_lifer_leaflet else 'species' if use_species_leaflet else 'family' if use_family_leaflet else 'all_locations'}_leaflet_h{map_height}_"
                                f"n{int(st.session_state.get(FOLIUM_MAP_MOUNT_NONCE_KEY, 0))}"
                            ),
                        )
                elif (
                    folium_st_key is not None
                    and st.session_state.get(EXPLORER_MAP_HTML_BYTES_KEY) is not None
                ):
                    if map_hint_text:
                        st.info(map_hint_text)
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
                    with perf_span("prep.map_iframe_embed"):
                        # Deep copy: ``st_folium`` / Folium render paths mutate in memory; mutating the
                        # cached ``folium.Map`` causes intermittent empty maps on subsequent cache hits.
                        st_folium(
                            copy.deepcopy(result_map),
                            use_container_width=True,
                            height=int(map_height),
                            key=folium_st_key,
                            returned_objects=[],
                            return_on_hover=False,
                        )

        with st.spinner(TAB_PREP_SPINNER_TEXT):
            with perf_span("prep.cache_checklist_stats"):
                checklist_payload = cached_checklist_stats_payload(work_df, tax_locale_effective)
            with perf_span("prep.cache_maint_rankings_sex_notation"):
                top_n = int(st.session_state.get(STREAMLIT_RANKINGS_TOP_N_KEY))
                hc_sort = str(st.session_state.get(STREAMLIT_HIGH_COUNT_SORT_KEY))
                hc_tb = str(st.session_state.get(STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY))
                if df_full is not None and not df_full.empty:
                    maint_full_payload = cached_full_export_checklist_stats_payload(
                        df_full, top_n, hc_sort, hc_tb, tax_locale_effective
                    )
                    rankings_bundle = build_rankings_tab_bundle(
                        df_full,
                        country_sort=st.session_state.get(STREAMLIT_COUNTRY_TAB_SORT_KEY),
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

            with perf_span("prep.tab_session_sync"):
                sync_checklist_stats_tab_session_inputs(checklist_payload)
                sync_rankings_tab_session_inputs(rankings_bundle)
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

        _spinner_emoji_placeholder.empty()
        _has_map_export = bool(st.session_state.get(EXPLORER_MAP_HTML_BYTES_KEY))
        if _has_map_export:
            st.divider()
            _ex1, _ex2, _ex3 = st.columns([1, 3, 1])
            with _ex2:
                # Match outline “Buy me a coffee” pill (``st.download_button`` is a real widget, not an ``<a>``).
                inject_sidebar_outline_download_button_css(SIDEBAR_FOOTER_LINK_HEX)
                st.download_button(
                    "Export map HTML",
                    data=st.session_state[EXPLORER_MAP_HTML_BYTES_KEY],
                    file_name=MAP_EXPORT_HTML_FILENAME,
                    mime="text/html",
                    key=EXPORT_MAP_HTML_BTN_KEY,
                    help="Standalone HTML for the current map.",
                    use_container_width=True,
                    type="secondary",
                )
        sidebar_footer_links(leading_divider=not _has_map_export)
        sidebar_bottom_slot_end()

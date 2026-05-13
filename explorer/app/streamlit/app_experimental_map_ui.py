"""Experimental All locations map tab — Streamlit custom component spike (#221).

``map.experimental.payload`` spans GeoJSON build when the session cache misses; hits reuse
``(revision, geojson)`` keyed like Folium ``static_map_cache_key`` + cluster/circle ``revision_extra``
+ optional ``EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP``. See ``docs/explorer/issue-221-map-component-spike.md``.
"""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st

from explorer.app.streamlit.app_caches import static_map_cache_key
from explorer.app.streamlit.app_constants import (
    EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY,
    STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
    STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
)
from explorer.app.streamlit.app_go_to_gps_ui import go_to_gps_pin_from_session
from explorer.app.streamlit.defaults import (
    MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
    MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
    MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS,
    MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
)
from explorer.app.streamlit.perf_instrumentation import perf_span
from explorer.components.all_locations_map import render_all_locations_map_component
from explorer.core.all_locations_experimental_marker_style import (
    experimental_default_scheme_circle_marker_props,
)
from explorer.core.all_locations_geojson import build_all_locations_geojson_payload
from explorer.core.all_locations_viewport import ALL_LOCATIONS_SCOPE_FOCUSED
from explorer.core.map_prep import prepare_all_locations_map_context
from explorer.core.settings_schema_defaults import MAP_CLUSTER_ALL_LOCATIONS_DEFAULT


def _visits_inline_max_from_env() -> int | None:
    """Optional cap on checklist rows per pin (smaller GeoJSON); unset = classic full parity."""
    raw = str(os.environ.get("EXPLORER_EXPERIMENTAL_VISITS_INLINE_CAP", "") or "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if n > 0 else None


def render_map_experimental_tab(
    *,
    work_df: Any,
    df_full: Any,
    map_view_mode: str,
    map_height: int,
    date_filter_banner: str,
    map_style: str,
    popup_sort_order: str,
    popup_scroll_hint: str,
    mark_lifer: bool,
    mark_last_seen: bool,
    family_colour_scheme: int,
    taxonomy_locale: str,
) -> None:
    st.caption(
        "**Map (experimental)** — Leaflet + clustering (#221). Cluster toggle matches classic Map; "
        "**pin colours/radius** match preset **1** (Eucalypt) — sidebar marker scheme not applied here yet."
    )
    if map_view_mode != "all":
        st.info('Switch **Map view** in the sidebar to **All locations** to try this prototype.')
        return

    visits_inline_max = _visits_inline_max_from_env()
    circle_style = experimental_default_scheme_circle_marker_props()
    cluster_opts: dict[str, Any] = {
        "enabled": bool(
            st.session_state.get(
                STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
                MAP_CLUSTER_ALL_LOCATIONS_DEFAULT,
            )
        ),
        "max_cluster_radius": MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
        "disable_clustering_at_zoom": MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
        "spiderfy_on_max_zoom": MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
        "remove_outside_visible_bounds": MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS,
    }
    revision_bundle = {"circle_marker": circle_style, "cluster": cluster_opts}
    revision_extra_json = json.dumps(revision_bundle, sort_keys=True)

    _scope = str(
        st.session_state.get(STREAMLIT_ALL_LOCATIONS_SCOPE_KEY, ALL_LOCATIONS_SCOPE_FOCUSED)
        or ALL_LOCATIONS_SCOPE_FOCUSED
    ).strip()
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
        _scope,
    )
    _ck = static_map_cache_key(
        work_df,
        "all",
        date_filter_banner,
        map_style,
        _render_opts_sig,
        taxonomy_locale=str(taxonomy_locale or "").strip(),
        species_selected_sci="",
        species_selected_common="",
        hide_non_matching_locations=False,
        go_to_gps_pin=go_to_gps_pin_from_session(),
    )
    payload_cache_key = (_ck, revision_extra_json, visits_inline_max)

    try:
        _perf_extra: dict[str, Any] = {
            "embed": "experimental_leaflet",
            "map_view_mode": map_view_mode,
            "payload_cache_hit": False,
            "visits_inline_cap": visits_inline_max,
        }
        with perf_span("map.experimental.payload", extra=_perf_extra):
            cached = st.session_state.get(EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY)
            if isinstance(cached, dict) and cached.get("payload_cache_key") == payload_cache_key:
                revision = str(cached["revision"])
                geojson = cached["geojson"]
                _perf_extra["payload_cache_hit"] = True
            else:
                ctx = prepare_all_locations_map_context(work_df, full_df=df_full)
                loc_df = ctx["location_data"]
                work = ctx["df"]
                counts = work.groupby("Location ID")["Submission ID"].nunique()
                popup_visit_dates_ascending = str(popup_sort_order).strip().lower() != "descending"
                revision, geojson = build_all_locations_geojson_payload(
                    loc_df,
                    checklist_counts_by_location=counts.to_dict(),
                    records_by_location=ctx["records_by_loc"],
                    popup_visit_dates_ascending=popup_visit_dates_ascending,
                    visits_inline_max=visits_inline_max,
                    omit_pin_colour=True,
                    revision_extra=revision_extra_json,
                )
                st.session_state[EXPERIMENTAL_ALL_LOCATIONS_PAYLOAD_CACHE_KEY] = {
                    "payload_cache_key": payload_cache_key,
                    "revision": revision,
                    "geojson": geojson,
                }
    except ValueError as e:
        st.warning(str(e))
        return

    with perf_span(
        "map.experimental.component_embed",
        extra={
            "embed": "experimental_leaflet",
            "map_view_mode": map_view_mode,
            "revision_prefix": revision[:12],
            "n_features": len(geojson.get("features", [])),
            "cluster_enabled": cluster_opts.get("enabled"),
            "marker_preset": "scheme_1_eucalypt",
        },
    ):
        render_all_locations_map_component(
            revision=revision,
            geojson=geojson,
            height=map_height,
            cluster_options=cluster_opts,
            circle_marker_style=circle_style,
            key="explorer_all_locations_map_component_v1",
        )

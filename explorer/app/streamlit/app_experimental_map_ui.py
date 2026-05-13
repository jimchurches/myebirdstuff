"""Experimental All locations map tab — Streamlit custom component spike (#221)."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from explorer.app.streamlit.app_constants import (
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
    STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY,
)
from explorer.app.streamlit.defaults import (
    MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
    MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
    MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS,
    MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
    active_map_marker_colour_scheme,
)
from explorer.app.streamlit.perf_instrumentation import perf_span
from explorer.components.all_locations_map import render_all_locations_map_component
from explorer.core.all_locations_geojson import build_all_locations_geojson_payload
from explorer.core.map_prep import prepare_all_locations_map_context
from explorer.core.settings_schema_defaults import MAP_CLUSTER_ALL_LOCATIONS_DEFAULT


def render_map_experimental_tab(
    *,
    work_df: Any,
    df_full: Any,
    map_view_mode: str,
    map_height: int,
) -> None:
    st.caption(
        "**Map (experimental)** — Leaflet + marker clustering (#221 spike). Uses the same **cluster "
        "all locations** sidebar toggle as the classic Map. Open DevTools for revision-unchanged logs."
    )
    if map_view_mode != "all":
        st.info('Switch **Map view** in the sidebar to **All locations** to try this prototype.')
        return

    try:
        with perf_span(
            "map.experimental.payload",
            extra={"embed": "experimental_leaflet", "map_view_mode": map_view_mode},
        ):
            ctx = prepare_all_locations_map_context(work_df, full_df=df_full)
            loc_df = ctx["location_data"]
            work = ctx["df"]
            counts = work.groupby("Location ID")["Submission ID"].nunique()
            raw_ix = st.session_state.get(STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY)
            try:
                scheme_ix = int(raw_ix) if raw_ix is not None else None
            except (TypeError, ValueError):
                scheme_ix = None
            scheme = active_map_marker_colour_scheme(scheme_ix)
            pin_hex = str(scheme.global_defaults.fill_hex)

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
            revision, geojson = build_all_locations_geojson_payload(
                loc_df,
                checklist_counts_by_location=counts.to_dict(),
                pin_fill_hex=pin_hex,
                revision_extra=json.dumps(cluster_opts, sort_keys=True),
            )
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
        },
    ):
        render_all_locations_map_component(
            revision=revision,
            geojson=geojson,
            height=map_height,
            cluster_options=cluster_opts,
            key="explorer_all_locations_map_component_v1",
        )

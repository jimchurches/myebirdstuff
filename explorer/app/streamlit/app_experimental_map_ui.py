"""Experimental All locations map tab — Streamlit custom component spike (#221)."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from explorer.app.streamlit.app_constants import STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY
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
        "**Map (experimental)** — Leaflet + clustering (#221). Cluster toggle matches classic Map; "
        "**pin colours/radius** match preset **1** (Eucalypt) — sidebar marker scheme not applied here yet."
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
            revision, geojson = build_all_locations_geojson_payload(
                loc_df,
                checklist_counts_by_location=counts.to_dict(),
                omit_pin_colour=True,
                revision_extra=json.dumps(revision_bundle, sort_keys=True),
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

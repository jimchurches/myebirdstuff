"""Per-map-mode Leaflet GeoJSON payload prep (R13)."""

from __future__ import annotations

import hashlib
import importlib
import json
from typing import Any, Callable, Literal

import streamlit as st

from explorer.app.streamlit.app_caches import (
    cached_family_map_bundle,
    leaflet_payload_cache_key,
)
from explorer.app.streamlit.app_constants import (
    ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
    FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
    LIFER_LEAFLET_PAYLOAD_CACHE_KEY,
    SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
    STREAMLIT_ALL_LOCATIONS_SCOPE_KEY,
    STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
    STREAMLIT_MAP_DATE_FILTER_KEY,
    STREAMLIT_MAP_DATE_RANGE_KEY,
)
from explorer.app.streamlit.app_go_to_gps_ui import go_to_gps_pin_from_session
from explorer.app.streamlit.app_prep_map_leaflet_caches import (
    leaflet_payload_cache_lookup,
    leaflet_payload_cache_store,
)
from explorer.app.streamlit.app_prep_map_types import LeafletMapPrepBundle
from explorer.app.streamlit.defaults import (
    ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    FAMILY_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    LIFER_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    MAP_DEFAULT_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
    MAP_DEFAULT_LOCATION_CLUSTER_MAX_RADIUS_PX,
    MAP_DEFAULT_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS,
    MAP_DEFAULT_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
    MAP_LIFER_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
    MAP_LIFER_LOCATION_CLUSTER_MAX_RADIUS_PX,
    MAP_LIFER_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS,
    MAP_LIFER_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
    SPECIES_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    active_map_marker_colour_scheme,
)
from explorer.core.all_locations_geojson import build_all_locations_geojson_payload
from explorer.core.all_locations_marker_style import (
    circle_marker_style_for_all_locations_map,
    cluster_icon_style_for_all_locations_map,
)
from explorer.core.all_locations_viewport import (
    ALL_LOCATIONS_FRAMING_CENTRE_OF_GRAVITY,
    ALL_LOCATIONS_FRAMING_FIT_ALL,
    ALL_LOCATIONS_SCOPE_FOCUSED,
    location_id_to_country_map,
)
from explorer.core.family_locations_geojson import (
    build_family_locations_geojson_payload,
)
from explorer.core.family_map_compute import (
    build_common_name_to_species_url,
    build_family_location_pins,
    compute_family_map_banner_metrics,
    filter_work_to_family,
    selected_species_checklist_individual_counts,
)
from explorer.core.family_map_overlays import (
    build_family_map_banner_overlay_html,
    build_family_map_legend_overlay_html_for_pins,
)
from explorer.core.leaflet_geojson_build_metrics import (
    empty_leaflet_geojson_build_metrics,
    merge_leaflet_build_metrics_into,
)
from explorer.core.lifer_last_seen_prep import count_subspecies_lifer_taxa
from explorer.core.lifer_locations_geojson import build_lifer_locations_geojson_payload
from explorer.core.map_leaflet_viewport import (
    all_locations_leaflet_viewport_recipe,
    family_leaflet_viewport_recipe,
    lifer_leaflet_viewport_recipe,
    species_leaflet_viewport_recipe,
)
from explorer.core.map_marker_colour_resolve import (
    resolve_lifer_overlay_pin_params,
    resolve_species_visit_pin,
)
from explorer.core.settings_schema_defaults import MAP_CLUSTER_ALL_LOCATIONS_DEFAULT
from explorer.core.species_link_urls import species_banner_url
from explorer.core.species_locations_geojson import (
    build_species_locations_geojson_payload,
    compute_species_map_banner_fields,
)
from explorer.core.species_logic import base_species_for_lifer, filter_species
from explorer.presentation.map_renderer import (
    STREAMLIT_COMPONENT_MAP_LEGEND_STYLE,
    build_all_locations_banner_html,
    build_legend_html,
    build_lifer_locations_banner_html,
    build_species_banner_html,
    build_species_locations_awaiting_selection_banner_html,
)


def _prep_map_ui():
    return importlib.import_module("explorer.app.streamlit.app_prep_map_ui")


def prep_family_leaflet_mode(
    *,
    work_df: Any,
    df_full: Any,
    tax_locale_effective: str,
    date_filter_banner: str,
    map_style: str,
    map_height: int,
    map_view_mode: str,
    family_name: str,
    family_highlight_base: str,
    family_colour_scheme: int,
    blank_viewport_recipe: dict[str, Any],
    species_url_fn: Callable[..., str],
) -> tuple[LeafletMapPrepBundle, str | None]:
    """Build family-map Leaflet payload; returns bundle and optional map-tab hint text."""
    bundle = LeafletMapPrepBundle(use_family_leaflet=True)
    map_hint_text: str | None = None
    result_warning = None
    fam = (family_name or "").strip()
    hl = (family_highlight_base or "").strip().lower()

    with _prep_map_ui().perf_span("prep.cached_family_map_bundle"):
        fam_bundle = cached_family_map_bundle(df_full, tax_locale_effective)
    fams = set(fam_bundle.get("families") or ())
    work = fam_bundle.get("work")
    tax_merged = fam_bundle.get("tax_merged")

    _ck = leaflet_payload_cache_key(
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
    leaflet_circle_style: dict[str, Any] = {}
    leaflet_cluster_icon_style: dict[str, Any] = {}
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
    elif fam not in fams or work is None or getattr(work, "empty", True):
        map_hint_text = "No family data available (taxonomy may not have loaded)."
    else:
        map_hint_text = None

    _perf_family: dict[str, Any] = {
        "embed": "family_leaflet",
        "map_view_mode": map_view_mode,
        "payload_cache_hit": False,
        "family_selected": bool(fam),
    }
    leaflet_revision: str | None = None
    leaflet_geojson: dict[str, Any] | None = None
    all_locations_leaflet_banner_html = ""
    all_locations_leaflet_legend_html = ""

    with _prep_map_ui().perf_span("map.family_leaflet.payload", extra=_perf_family):
        cached_fam = leaflet_payload_cache_lookup(
            FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
            payload_cache_key,
        )
        if cached_fam is not None:
            leaflet_revision = str(cached_fam["revision"])
            leaflet_geojson = cached_fam["geojson"]
            family_framing_pairs = list(cached_fam.get("framing_pairs") or [])
            family_highlight_framed = bool(cached_fam.get("highlight_framed"))
            all_locations_leaflet_banner_html = str(
                cached_fam.get("banner_html") or ""
            )
            all_locations_leaflet_legend_html = str(
                cached_fam.get("legend_html") or ""
            )
            _perf_family["payload_cache_hit"] = True
        elif not fam or fam not in fams or work is None or getattr(work, "empty", True):
            family_framing_pairs = []
            family_highlight_framed = False
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
            merge_leaflet_build_metrics_into(
                _perf_family, empty_leaflet_geojson_build_metrics()
            )
            leaflet_payload_cache_store(
                FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
                payload_cache_key,
                {
                    "revision": leaflet_revision,
                    "geojson": leaflet_geojson,
                    "framing_pairs": family_framing_pairs,
                    "highlight_framed": family_highlight_framed,
                    "banner_html": "",
                    "legend_html": "",
                },
                max_entries=FAMILY_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
            )
        else:
            with _prep_map_ui().perf_span("prep.family_map_composition_with_pins"):
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
                family_species_url_by_common = (
                    build_common_name_to_species_url(
                        wf,
                        tax_merged,
                        fallback_fn=species_url_fn,
                    )
                    if tax_merged is not None
                    and not getattr(tax_merged, "empty", True)
                    else {}
                )
                base_to_common = fam_bundle.get("base_to_common") or {}
                hl_label = (base_to_common.get(hl) or hl) if hl else ""
                sel_counts = (
                    selected_species_checklist_individual_counts(wf, hl)
                    if hl and metrics
                    else None
                )
                hl_species_url = None
                if hl:
                    hl_species_url = species_banner_url(
                        base_species=hl,
                        taxonomy_locale=tax_locale_effective,
                        display_name=hl_label or "",
                        species_url_fn=species_url_fn,
                    )
                    if not hl_species_url and family_species_url_by_common:
                        _hl_rows = wf[
                            wf["_base"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            == hl
                        ]
                        for _cn in (
                            _hl_rows["Common Name"]
                            .fillna("")
                            .astype(str)
                            .str.strip()
                            .unique()
                        ):
                            if _cn:
                                _u = family_species_url_by_common.get(_cn)
                                if _u:
                                    hl_species_url = _u
                                    break
                all_locations_leaflet_banner_html = (
                    build_family_map_banner_overlay_html(
                        metrics,
                        selected_species_n_checklists=(
                            sel_counts[0] if sel_counts else None
                        ),
                        selected_species_n_individuals=(
                            sel_counts[1] if sel_counts else None
                        ),
                        selected_species_display_name=hl_label or None,
                        selected_species_url=hl_species_url,
                    )
                    if metrics
                    else ""
                )
                all_locations_leaflet_legend_html = (
                    build_family_map_legend_overlay_html_for_pins(
                        pins,
                        highlight_label=hl_label or None,
                        highlight_species_url=hl_species_url,
                        style=_visit_sch,
                    )
                )
            (
                leaflet_revision,
                leaflet_geojson,
                family_framing_pairs,
                family_highlight_framed,
                payload_build_metrics,
            ) = build_family_locations_geojson_payload(
                pins,
                visit_marker_scheme=_visit_sch,
                location_page_url_fn=lambda lid: (
                    f"https://ebird.org/lifelist/{lid}" if lid else None
                ),
                species_url_fn=species_url_fn,
                species_url_by_common=family_species_url_by_common or None,
                fit_bounds_highlight_only=bool(hl),
                revision_extra=revision_extra_json,
            )
            merge_leaflet_build_metrics_into(_perf_family, payload_build_metrics)
            leaflet_payload_cache_store(
                FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
                payload_cache_key,
                {
                    "revision": leaflet_revision,
                    "geojson": leaflet_geojson,
                    "framing_pairs": family_framing_pairs,
                    "highlight_framed": family_highlight_framed,
                    "banner_html": all_locations_leaflet_banner_html,
                    "legend_html": all_locations_leaflet_legend_html,
                },
                max_entries=FAMILY_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
            )

    leaflet_viewport: dict[str, Any] | None = None
    if leaflet_revision and leaflet_geojson is not None:
        leaflet_viewport = family_leaflet_viewport_recipe(
            family_framing_pairs,
            blank_viewport_recipe=blank_viewport_recipe,
            highlight_framed=family_highlight_framed,
        )

    bundle.leaflet_revision = leaflet_revision
    bundle.leaflet_geojson = leaflet_geojson
    bundle.leaflet_cluster_opts = leaflet_cluster_opts
    bundle.leaflet_circle_style = leaflet_circle_style
    bundle.leaflet_cluster_icon_style = leaflet_cluster_icon_style
    bundle.leaflet_viewport = leaflet_viewport
    bundle.all_locations_leaflet_banner_html = all_locations_leaflet_banner_html
    bundle.all_locations_leaflet_legend_html = all_locations_leaflet_legend_html
    bundle.result_warning = result_warning
    return bundle, map_hint_text


def prep_standard_map_leaflet_modes(
    *,
    ctx: dict[str, Any],
    work_df: Any,
    tax_locale_effective: str,
    map_view_mode: str,
    date_filter_banner: str,
    map_style: str,
    map_height: int,
    species_pick_common: str | None,
    species_pick_sci: str,
    hide_non_matching_locations: bool,
    popup_sort_order: Any,
    popup_scroll_hint: Any,
    mark_lifer: bool,
    mark_last_seen: bool,
    family_colour_scheme: int,
    blank_viewport_recipe: dict[str, Any],
    species_url_fn: Callable[..., str],
) -> tuple[LeafletMapPrepBundle, str | None]:
    """Build all-locations, lifer, or species Leaflet payload."""
    bundle = LeafletMapPrepBundle()
    map_hint_text: str | None = None
    result_warning: str | None = None

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
    bundle.use_all_locations_leaflet = capture_all_locations_view
    bundle.use_lifer_leaflet = map_view_mode == "lifers"
    bundle.use_species_leaflet = map_view_mode == "species"
    _go_pin = go_to_gps_pin_from_session()
    _visit_sch = active_map_marker_colour_scheme(int(family_colour_scheme))
    _scope = ALL_LOCATIONS_SCOPE_FOCUSED
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
    _ck = leaflet_payload_cache_key(
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

    leaflet_revision: str | None = None
    leaflet_geojson: dict[str, Any] | None = None
    leaflet_cluster_opts: dict[str, Any] | None = None
    leaflet_circle_style: dict[str, Any] | None = None
    leaflet_cluster_icon_style: dict[str, Any] | None = None
    leaflet_viewport: dict[str, Any] | None = None
    all_locations_leaflet_banner_html = ""
    all_locations_leaflet_legend_html = ""

    if bundle.use_all_locations_leaflet:
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
        payload_cache_key = (_ck, revision_extra_json)
        _perf_leaflet: dict[str, Any] = {
            "embed": "all_locations_leaflet",
            "map_view_mode": map_view_mode,
            "payload_cache_hit": False,
        }
        with _prep_map_ui().perf_span("map.all_locations_leaflet.payload", extra=_perf_leaflet):
            cached_pl = leaflet_payload_cache_lookup(
                ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
                payload_cache_key,
            )
            if cached_pl is not None:
                leaflet_revision = str(cached_pl["revision"])
                leaflet_geojson = cached_pl["geojson"]
                all_locations_leaflet_banner_html = str(
                    cached_pl.get("banner_html") or ""
                )
                all_locations_leaflet_legend_html = str(
                    cached_pl.get("legend_html") or ""
                )
                _perf_leaflet["payload_cache_hit"] = True
            else:
                loc_df = ctx["location_data"]
                work = ctx["df"]
                counts = work.groupby("Location ID")["Submission ID"].nunique()
                popup_visit_dates_ascending = (
                    str(popup_sort_order).strip().lower() != "descending"
                )
                (
                    leaflet_revision,
                    leaflet_geojson,
                    payload_build_metrics,
                ) = build_all_locations_geojson_payload(
                    loc_df,
                    checklist_counts_by_location=counts.to_dict(),
                    records_by_location=ctx["records_by_loc"],
                    popup_visit_dates_ascending=popup_visit_dates_ascending,
                    omit_pin_colour=True,
                    revision_extra=revision_extra_json,
                )
                merge_leaflet_build_metrics_into(_perf_leaflet, payload_build_metrics)
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
                leaflet_payload_cache_store(
                    ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
                    payload_cache_key,
                    {
                        "revision": leaflet_revision,
                        "geojson": leaflet_geojson,
                        "banner_html": all_locations_leaflet_banner_html,
                        "legend_html": all_locations_leaflet_legend_html,
                    },
                    max_entries=ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
                )
        result_warning = None
    elif bundle.use_lifer_leaflet:
        result_warning = None
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
            "max_cluster_radius": MAP_LIFER_LOCATION_CLUSTER_MAX_RADIUS_PX,
            "disable_clustering_at_zoom": MAP_LIFER_LOCATION_CLUSTER_DISABLE_AT_ZOOM,
            "spiderfy_on_max_zoom": MAP_LIFER_LOCATION_CLUSTER_SPIDERFY_ON_MAX_ZOOM,
            "remove_outside_visible_bounds": (
                MAP_LIFER_LOCATION_CLUSTER_REMOVE_OUTSIDE_VISIBLE_BOUNDS
            ),
        }
        leaflet_circle_style = {}
        subsp = bool(st.session_state.get(STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY, False))
        revision_bundle = {
            "lifer_leaflet": True,
            "map_style": map_style,
            "subspecies": subsp,
            "scheme": int(family_colour_scheme),
            "popup_sort": str(popup_sort_order),
            "cluster": leaflet_cluster_opts,
            "cluster_icon_style": leaflet_cluster_icon_style,
        }
        revision_extra_json = json.dumps(revision_bundle, sort_keys=True)
        payload_cache_key = (_ck, revision_extra_json)
        lifer_framing_pairs: list[list[float]] = []
        _perf_lifer: dict[str, Any] = {
            "embed": "lifer_leaflet",
            "map_view_mode": map_view_mode,
            "payload_cache_hit": False,
        }
        with _prep_map_ui().perf_span("map.lifer_leaflet.payload", extra=_perf_lifer):
            cached_lif = leaflet_payload_cache_lookup(
                LIFER_LEAFLET_PAYLOAD_CACHE_KEY,
                payload_cache_key,
            )
            if cached_lif is not None:
                leaflet_revision = str(cached_lif["revision"])
                leaflet_geojson = cached_lif["geojson"]
                lifer_framing_pairs = list(cached_lif.get("framing_pairs") or [])
                all_locations_leaflet_banner_html = str(
                    cached_lif.get("banner_html") or ""
                )
                all_locations_leaflet_legend_html = str(
                    cached_lif.get("legend_html") or ""
                )
                _perf_lifer["payload_cache_hit"] = True
            else:
                (
                    leaflet_revision,
                    leaflet_geojson,
                    lifer_warn,
                    lifer_framing_pairs,
                    payload_build_metrics,
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
                merge_leaflet_build_metrics_into(_perf_lifer, payload_build_metrics)
                if lifer_warn:
                    result_warning = lifer_warn
                    leaflet_revision = None
                    leaflet_geojson = None
                    lifer_framing_pairs = []
                else:
                    n_lifer_sp = len(ctx["true_lifer_locations"])
                    n_pin = len(leaflet_geojson.get("features") or [])
                    all_locations_leaflet_banner_html = (
                        build_lifer_locations_banner_html(
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
                    leaflet_payload_cache_store(
                        LIFER_LEAFLET_PAYLOAD_CACHE_KEY,
                        payload_cache_key,
                        {
                            "revision": leaflet_revision,
                            "geojson": leaflet_geojson,
                            "framing_pairs": lifer_framing_pairs,
                            "banner_html": all_locations_leaflet_banner_html,
                            "legend_html": all_locations_leaflet_legend_html,
                        },
                        max_entries=LIFER_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
                    )
            if leaflet_revision and leaflet_geojson is not None:
                leaflet_viewport = lifer_leaflet_viewport_recipe(lifer_framing_pairs)
    elif bundle.use_species_leaflet:
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
        with _prep_map_ui().perf_span("map.species_leaflet.payload", extra=_perf_species):
            cached_sp = leaflet_payload_cache_lookup(
                SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
                payload_cache_key,
            )
            if cached_sp is not None:
                leaflet_revision = str(cached_sp["revision"])
                leaflet_geojson = cached_sp["geojson"]
                species_framing_pairs = list(cached_sp.get("framing_pairs") or [])
                species_pin_roles = set(cached_sp.get("pin_roles") or [])
                all_locations_leaflet_banner_html = str(
                    cached_sp.get("banner_html") or ""
                )
                all_locations_leaflet_legend_html = str(
                    cached_sp.get("legend_html") or ""
                )
                _perf_species["payload_cache_hit"] = True
            elif not overlay_sci:
                species_framing_pairs = []
                species_pin_roles = set()
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
                all_locations_leaflet_banner_html = (
                    build_species_locations_awaiting_selection_banner_html()
                )
                all_locations_leaflet_legend_html = ""
                merge_leaflet_build_metrics_into(
                    _perf_species, empty_leaflet_geojson_build_metrics()
                )
                leaflet_payload_cache_store(
                    SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
                    payload_cache_key,
                    {
                        "revision": leaflet_revision,
                        "geojson": leaflet_geojson,
                        "framing_pairs": species_framing_pairs,
                        "pin_roles": [],
                        "banner_html": all_locations_leaflet_banner_html,
                        "legend_html": all_locations_leaflet_legend_html,
                    },
                    max_entries=SPECIES_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
                )
            else:
                popup_visit_dates_ascending = (
                    str(popup_sort_order).strip().lower() != "descending"
                )
                _species_filter_by_date = False
                _species_filter_start = ""
                _species_filter_end = ""
                if map_view_mode == "species" and bool(
                    st.session_state.get(STREAMLIT_MAP_DATE_FILTER_KEY, False)
                ):
                    _dr = st.session_state.get(STREAMLIT_MAP_DATE_RANGE_KEY)
                    if isinstance(_dr, tuple) and len(_dr) == 2:
                        _species_filter_by_date = True
                        _species_filter_start = _dr[0].isoformat()
                        _species_filter_end = _dr[1].isoformat()
                (
                    leaflet_revision,
                    leaflet_geojson,
                    sp_warn,
                    species_framing_pairs,
                    pin_roles,
                    payload_build_metrics,
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
                    lifer_lookup_df=ctx["lifer_lookup_df"],
                    filter_by_date=_species_filter_by_date,
                    filter_start_date=_species_filter_start,
                    filter_end_date=_species_filter_end,
                )
                merge_leaflet_build_metrics_into(_perf_species, payload_build_metrics)
                if sp_warn:
                    result_warning = sp_warn
                    leaflet_revision = None
                    leaflet_geojson = None
                    species_framing_pairs = []
                    pin_roles = set()
                else:
                    species_pin_roles = set(pin_roles)
                    _filtered_sp = filter_species(ctx["df"], overlay_sci)
                    _banner_fields = compute_species_map_banner_fields(
                        filtered=_filtered_sp,
                        selected_species=overlay_sci,
                        selected_common_name=overlay_common,
                        lifer_lookup_df=ctx["lifer_lookup_df"],
                        base_species_fn=base_species_for_lifer,
                    )
                    _sp_url = species_banner_url(
                        base_species=base_species_for_lifer(overlay_sci),
                        taxonomy_locale=tax_locale_effective,
                        display_name=_banner_fields["display_name"],
                        species_url_fn=species_url_fn,
                    )
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
                    leaflet_payload_cache_store(
                        SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
                        payload_cache_key,
                        {
                            "revision": leaflet_revision,
                            "geojson": leaflet_geojson,
                            "framing_pairs": species_framing_pairs,
                            "pin_roles": sorted(species_pin_roles),
                            "banner_html": all_locations_leaflet_banner_html,
                            "legend_html": all_locations_leaflet_legend_html,
                        },
                        max_entries=SPECIES_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
                    )
            if leaflet_revision and leaflet_geojson is not None:
                leaflet_viewport = species_leaflet_viewport_recipe(
                    species_framing_pairs,
                    go_to_gps_pin=_go_pin,
                    blank_viewport_recipe=blank_viewport_recipe
                    if not overlay_sci
                    else None,
                )

    bundle.leaflet_revision = leaflet_revision
    bundle.leaflet_geojson = leaflet_geojson
    bundle.leaflet_cluster_opts = leaflet_cluster_opts
    if leaflet_circle_style is not None:
        bundle.leaflet_circle_style = leaflet_circle_style
    if leaflet_cluster_icon_style is not None:
        bundle.leaflet_cluster_icon_style = leaflet_cluster_icon_style
    bundle.leaflet_viewport = leaflet_viewport
    bundle.all_locations_leaflet_banner_html = all_locations_leaflet_banner_html
    bundle.all_locations_leaflet_legend_html = all_locations_leaflet_legend_html
    bundle.result_warning = result_warning
    return bundle, map_hint_text

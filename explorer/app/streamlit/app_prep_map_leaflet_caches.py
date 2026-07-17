"""Leaflet map session LRU caches and HTML export helpers (extracted from ``app_prep_map_ui``).

Dataset-signature changes clear these caches via :func:`apply_dataset_signature_for_map_caches`.
Map mode payload builders in ``app_prep_map_ui`` use :func:`leaflet_payload_cache_lookup` /
:func:`leaflet_payload_cache_store`.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

import streamlit as st

from explorer.app.streamlit.app_constants import (
    ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
    EBIRD_DATA_SIG_KEY,
    EXPLORER_MAP_HTML_BYTES_KEY,
    EXPORT_MAP_HTML_AUTO_DOWNLOAD_KEY,
    EXPORT_MAP_HTML_BTN_KEY,
    EXPORT_MAP_HTML_DOWNLOAD_BTN_KEY,
    EXPORT_MAP_HTML_ERROR_KEY,
    FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
    LEAFLET_EXPORT_BUILT_CACHE_KEY,
    LEAFLET_EXPORT_HTML_CACHE_KEY,
    LEAFLET_EXPORT_RECIPE_KEY,
    LIFER_LEAFLET_PAYLOAD_CACHE_KEY,
    SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
)
from explorer.app.streamlit.app_map_ui import inject_auto_click_streamlit_download_js
from explorer.app.streamlit.defaults import LEAFLET_EXPORT_HTML_CACHE_MAX_ENTRIES
from explorer.app.streamlit.perf_instrumentation import perf_record_point, perf_span
from explorer.app.streamlit.streamlit_ui_constants import MAP_EXPORT_HTML_FILENAME
from explorer.core.map_prep import data_signature_for_caches
from explorer.presentation.leaflet_map_export_cache import leaflet_export_html_cache_key
from explorer.presentation.leaflet_map_html_export import leaflet_map_to_html_bytes
from explorer.presentation.map_renderer import map_overlay_theme_stylesheet


def leaflet_export_html_cache_lookup(cache_key: tuple[str, ...]) -> bytes | None:
    cached = st.session_state.get(LEAFLET_EXPORT_HTML_CACHE_KEY)
    if isinstance(cached, OrderedDict):
        entry = cached.get(cache_key)
        if isinstance(entry, (bytes, bytearray)):
            cached.move_to_end(cache_key)
            return bytes(entry)
    return None


def leaflet_export_html_cache_store(cache_key: tuple[str, ...], html_bytes: bytes) -> None:
    cached = st.session_state.get(LEAFLET_EXPORT_HTML_CACHE_KEY)
    if not isinstance(cached, OrderedDict):
        cached = OrderedDict()
    cached[cache_key] = html_bytes
    cached.move_to_end(cache_key)
    while len(cached) > LEAFLET_EXPORT_HTML_CACHE_MAX_ENTRIES:
        cached.popitem(last=False)
    st.session_state[LEAFLET_EXPORT_HTML_CACHE_KEY] = cached


def leaflet_export_cache_key_for_recipe(recipe: dict[str, Any]) -> tuple[str, ...]:
    return leaflet_export_html_cache_key(
        leaflet_revision=str(recipe["leaflet_revision"]),
        map_height=int(recipe["map_height"]),
        map_style=str(recipe.get("map_style") or "default"),
        cluster_options=recipe.get("cluster_options") or {},
        circle_marker_style=recipe.get("circle_marker_style") or {},
        cluster_icon_style=recipe.get("cluster_icon_style") or {},
        viewport=recipe.get("viewport") or {},
        map_theme_css=str(recipe.get("map_theme_css") or ""),
        banner_html=str(recipe.get("banner_html") or ""),
        legend_html=str(recipe.get("legend_html") or ""),
    )


def materialize_leaflet_export_html(recipe: dict[str, Any]) -> bytes:
    cache_key = leaflet_export_cache_key_for_recipe(recipe)
    cached = leaflet_export_html_cache_lookup(cache_key)
    if cached is not None:
        perf_record_point("prep.leaflet_map_html_cache_hit")
        return cached
    perf_record_point("prep.leaflet_map_html_cache_miss")
    with perf_span("prep.leaflet_map_to_html_bytes"):
        built = leaflet_map_to_html_bytes(
            geojson=recipe["geojson"],
            height=int(recipe["map_height"]),
            map_style=str(recipe.get("map_style") or "default"),
            cluster_options=recipe.get("cluster_options") or {},
            circle_marker_style=recipe.get("circle_marker_style") or {},
            cluster_icon_style=recipe.get("cluster_icon_style") or {},
            viewport=recipe.get("viewport") or {},
            map_theme_css=str(recipe.get("map_theme_css") or ""),
            banner_html=str(recipe.get("banner_html") or ""),
            legend_html=str(recipe.get("legend_html") or ""),
        )
    leaflet_export_html_cache_store(cache_key, built)
    return built


def sync_leaflet_export_recipe(
    *,
    leaflet_revision: str,
    leaflet_geojson: dict[str, Any],
    map_height: int,
    map_style: str,
    leaflet_cluster_opts: dict[str, Any],
    leaflet_circle_style: dict[str, Any],
    leaflet_cluster_icon_style: dict[str, Any] | None,
    leaflet_viewport: dict[str, Any] | None,
    banner_html: str,
    legend_html: str,
) -> None:
    """Store export inputs; clear stale download bytes when the recipe changes."""
    recipe = {
        "leaflet_revision": leaflet_revision,
        "geojson": leaflet_geojson,
        "map_height": int(map_height),
        "map_style": str(map_style or "default"),
        "cluster_options": leaflet_cluster_opts,
        "circle_marker_style": leaflet_circle_style,
        "cluster_icon_style": leaflet_cluster_icon_style or {},
        "viewport": leaflet_viewport or {},
        "map_theme_css": map_overlay_theme_stylesheet(),
        "banner_html": banner_html,
        "legend_html": legend_html,
    }
    st.session_state[LEAFLET_EXPORT_RECIPE_KEY] = recipe
    recipe_key = leaflet_export_cache_key_for_recipe(recipe)
    if st.session_state.get(LEAFLET_EXPORT_BUILT_CACHE_KEY) != recipe_key:
        st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
        st.session_state.pop(LEAFLET_EXPORT_BUILT_CACHE_KEY, None)
        st.session_state.pop(EXPORT_MAP_HTML_ERROR_KEY, None)


def leaflet_export_session_bytes(recipe: dict[str, Any]) -> bytes | None:
    """Session snapshot of export HTML when it matches the current recipe."""
    recipe_key = leaflet_export_cache_key_for_recipe(recipe)
    built_key = st.session_state.get(LEAFLET_EXPORT_BUILT_CACHE_KEY)
    raw = st.session_state.get(EXPLORER_MAP_HTML_BYTES_KEY)
    if isinstance(raw, (bytes, bytearray)) and built_key == recipe_key:
        return bytes(raw)
    return None


def leaflet_export_download_bytes(recipe: dict[str, Any]) -> bytes | None:
    """Bytes for the sidebar download control without building (session or LRU)."""
    ready = leaflet_export_session_bytes(recipe)
    if ready is not None:
        return ready
    return leaflet_export_html_cache_lookup(leaflet_export_cache_key_for_recipe(recipe))


def render_leaflet_export_map_html_download(recipe: dict[str, Any]) -> None:
    """One user click: build export HTML (spinner), rerun, auto-fire Streamlit download."""
    err = st.session_state.get(EXPORT_MAP_HTML_ERROR_KEY)
    if err:
        st.error(f"Could not build map export: {err}")

    if st.session_state.pop(EXPORT_MAP_HTML_AUTO_DOWNLOAD_KEY, False):
        export_bytes = leaflet_export_download_bytes(recipe)
        if export_bytes is None:
            st.error("Map export was prepared but bytes are missing. Try Export again.")
            return
        st.caption("Starting download…")
        st.download_button(
            "Export map HTML",
            data=export_bytes,
            file_name=MAP_EXPORT_HTML_FILENAME,
            mime="text/html",
            key=EXPORT_MAP_HTML_DOWNLOAD_BTN_KEY,
            use_container_width=True,
            type="secondary",
        )
        inject_auto_click_streamlit_download_js(button_label="Export map HTML")
        return

    if st.button(
        "Export map HTML",
        key=EXPORT_MAP_HTML_BTN_KEY,
        use_container_width=True,
        type="secondary",
    ):
        st.session_state.pop(EXPORT_MAP_HTML_ERROR_KEY, None)
        try:
            export_bytes = leaflet_export_download_bytes(recipe)
            if export_bytes is None:
                with st.spinner("Building map HTML…"):
                    export_bytes = materialize_leaflet_export_html(recipe)
            recipe_key = leaflet_export_cache_key_for_recipe(recipe)
            st.session_state[EXPLORER_MAP_HTML_BYTES_KEY] = export_bytes
            st.session_state[LEAFLET_EXPORT_BUILT_CACHE_KEY] = recipe_key
        except Exception as exc:
            st.session_state[EXPORT_MAP_HTML_ERROR_KEY] = str(exc)
            st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
            st.session_state.pop(LEAFLET_EXPORT_BUILT_CACHE_KEY, None)
            return
        st.session_state[EXPORT_MAP_HTML_AUTO_DOWNLOAD_KEY] = True
        st.rerun()


def leaflet_payload_cache_lookup(
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


def leaflet_payload_cache_store(
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


def apply_dataset_signature_for_map_caches(
    df_full: Any,
    provenance: str | None,
    *,
    data_abs_path: str | None = None,
) -> bool:
    """Update ``EBIRD_DATA_SIG_KEY`` and clear Leaflet map/export session caches when the dataset changes.

    Returns ``True`` when caches were cleared due to a signature change.
    """
    prov_plain = provenance or ""
    sig = data_signature_for_caches(df_full, prov_plain, data_abs_path=data_abs_path)
    _prev_sig = st.session_state.get(EBIRD_DATA_SIG_KEY)
    if _prev_sig == sig:
        return False
    perf_record_point(
        "prep.data_sig_change",
        extra={
            "prev_present": _prev_sig is not None,
            "prev_sig": list(_prev_sig) if isinstance(_prev_sig, tuple) else _prev_sig,
            "new_sig": list(sig) if isinstance(sig, tuple) else sig,
        },
    )
    st.session_state[EBIRD_DATA_SIG_KEY] = sig
    st.session_state.pop(ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY, None)
    st.session_state.pop(LIFER_LEAFLET_PAYLOAD_CACHE_KEY, None)
    st.session_state.pop(SPECIES_LEAFLET_PAYLOAD_CACHE_KEY, None)
    st.session_state.pop(FAMILY_LEAFLET_PAYLOAD_CACHE_KEY, None)
    st.session_state.pop(LEAFLET_EXPORT_HTML_CACHE_KEY, None)
    st.session_state.pop(LEAFLET_EXPORT_RECIPE_KEY, None)
    st.session_state.pop(LEAFLET_EXPORT_BUILT_CACHE_KEY, None)
    return True

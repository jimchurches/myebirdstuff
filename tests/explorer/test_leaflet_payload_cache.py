"""Unit tests for Leaflet GeoJSON session LRU helpers in ``app_prep_map_ui`` (#222 §13–§15)."""

from __future__ import annotations

import pytest

from tests.explorer.test_streamlit_ui_helpers import _install_streamlit_stub


@pytest.fixture
def streamlit_stub(monkeypatch: pytest.MonkeyPatch):
    _install_streamlit_stub(monkeypatch)
    import streamlit as st

    st.session_state.clear()
    return st


def test_leaflet_payload_cache_miss_returns_none(streamlit_stub) -> None:
    from explorer.app.streamlit.app_constants import ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY
    from explorer.app.streamlit.app_prep_map_ui import _leaflet_payload_cache_lookup

    assert (
        _leaflet_payload_cache_lookup(ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY, ("k",))
        is None
    )


def test_leaflet_payload_cache_store_and_hit_restores_fields(streamlit_stub) -> None:
    from explorer.app.streamlit.app_constants import ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY
    from explorer.app.streamlit.app_prep_map_ui import (
        _leaflet_payload_cache_lookup,
        _leaflet_payload_cache_store,
    )

    key = ("cache-key", "rev-extra")
    entry = {
        "revision": "abc",
        "geojson": {"type": "FeatureCollection", "features": []},
        "banner_html": "<span>banner</span>",
        "legend_html": "<span>legend</span>",
    }
    _leaflet_payload_cache_store(
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
        key,
        entry,
        max_entries=4,
    )
    hit = _leaflet_payload_cache_lookup(ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY, key)
    assert hit is not None
    assert hit["revision"] == "abc"
    assert hit["geojson"] == entry["geojson"]
    assert hit["banner_html"] == "<span>banner</span>"
    assert hit["legend_html"] == "<span>legend</span>"


def test_leaflet_payload_cache_lru_evicts_oldest_when_over_max(streamlit_stub) -> None:
    from explorer.app.streamlit.app_constants import ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY
    from explorer.app.streamlit.app_prep_map_ui import (
        _leaflet_payload_cache_lookup,
        _leaflet_payload_cache_store,
    )

    session_key = ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY
    _leaflet_payload_cache_store(
        session_key,
        ("a",),
        {"revision": "1", "geojson": {}},
        max_entries=2,
    )
    _leaflet_payload_cache_store(
        session_key,
        ("b",),
        {"revision": "2", "geojson": {}},
        max_entries=2,
    )
    _leaflet_payload_cache_store(
        session_key,
        ("c",),
        {"revision": "3", "geojson": {}},
        max_entries=2,
    )
    assert _leaflet_payload_cache_lookup(session_key, ("a",)) is None
    assert _leaflet_payload_cache_lookup(session_key, ("b",)) is not None
    assert _leaflet_payload_cache_lookup(session_key, ("c",)) is not None


def test_leaflet_payload_cache_hit_moves_entry_to_mru_end(streamlit_stub) -> None:
    from explorer.app.streamlit.app_constants import ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY
    from explorer.app.streamlit.app_prep_map_ui import (
        _leaflet_payload_cache_lookup,
        _leaflet_payload_cache_store,
    )

    session_key = ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY
    _leaflet_payload_cache_store(
        session_key,
        ("a",),
        {"revision": "1", "geojson": {}},
        max_entries=2,
    )
    _leaflet_payload_cache_store(
        session_key,
        ("b",),
        {"revision": "2", "geojson": {}},
        max_entries=2,
    )
    assert _leaflet_payload_cache_lookup(session_key, ("a",)) is not None
    _leaflet_payload_cache_store(
        session_key,
        ("c",),
        {"revision": "3", "geojson": {}},
        max_entries=2,
    )
    assert _leaflet_payload_cache_lookup(session_key, ("a",)) is not None
    assert _leaflet_payload_cache_lookup(session_key, ("b",)) is None


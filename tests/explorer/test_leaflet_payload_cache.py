"""Unit tests for Leaflet GeoJSON session LRU helpers in ``app_prep_map_leaflet_caches``."""

from __future__ import annotations

import pytest

from explorer.app.streamlit.app_constants import (
    ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
    FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
    LIFER_LEAFLET_PAYLOAD_CACHE_KEY,
    SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
)
from explorer.app.streamlit.app_prep_map_leaflet_caches import (
    leaflet_payload_cache_lookup,
    leaflet_payload_cache_store,
)
from explorer.app.streamlit.defaults import (
    ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    FAMILY_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    LIFER_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    SPECIES_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
)
from tests.explorer.test_streamlit_ui_helpers import _install_streamlit_stub

_MODE_CASES: list[tuple[str, int, dict, str]] = [
    (
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
        {
            "revision": "all-rev",
            "geojson": {"type": "FeatureCollection", "features": [{"type": "Feature"}]},
            "banner_html": "<span>all-banner</span>",
            "legend_html": "<span>all-legend</span>",
        },
        "all_locations",
    ),
    (
        LIFER_LEAFLET_PAYLOAD_CACHE_KEY,
        LIFER_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
        {
            "revision": "lifer-rev",
            "geojson": {"type": "FeatureCollection", "features": []},
            "framing_pairs": [[-35.28, 149.13]],
            "banner_html": "<span>lifer-banner</span>",
            "legend_html": "<span>lifer-legend</span>",
        },
        "lifer",
    ),
    (
        SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
        SPECIES_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
        {
            "revision": "species-rev",
            "geojson": {"type": "FeatureCollection", "features": []},
            "framing_pairs": [[-37.0, 145.0]],
            "pin_roles": ["species", "default"],
            "banner_html": "<span>species-banner</span>",
            "legend_html": "<span>species-legend</span>",
        },
        "species",
    ),
    (
        FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
        FAMILY_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
        {
            "revision": "family-rev",
            "geojson": {"type": "FeatureCollection", "features": []},
            "framing_pairs": [[-35.5, 149.5]],
            "highlight_framed": True,
            "banner_html": "<span>family-banner</span>",
            "legend_html": "<span>family-legend</span>",
        },
        "family",
    ),
]


@pytest.fixture
def streamlit_stub(monkeypatch: pytest.MonkeyPatch):
    _install_streamlit_stub(monkeypatch)
    import streamlit as st

    st.session_state.clear()
    return st


@pytest.mark.parametrize(
    ("session_key", "_max_entries", "entry", "mode_id"),
    _MODE_CASES,
    ids=[c[3] for c in _MODE_CASES],
)
def test_leaflet_payload_cache_miss_returns_none(
    streamlit_stub,
    session_key: str,
    _max_entries: int,
    entry: dict,
    mode_id: str,
) -> None:
    assert leaflet_payload_cache_lookup(session_key, ("k", mode_id)) is None


@pytest.mark.parametrize(
    ("session_key", "max_entries", "entry", "mode_id"),
    _MODE_CASES,
    ids=[c[3] for c in _MODE_CASES],
)
def test_leaflet_payload_cache_store_and_hit_restores_fields(
    streamlit_stub,
    session_key: str,
    max_entries: int,
    entry: dict,
    mode_id: str,
) -> None:
    key = ("cache-key", mode_id)
    leaflet_payload_cache_store(session_key, key, entry, max_entries=max_entries)
    hit = leaflet_payload_cache_lookup(session_key, key)
    assert hit is not None
    for field, expected in entry.items():
        assert hit[field] == expected


@pytest.mark.parametrize(
    ("session_key", "mode_id"),
    [(c[0], c[3]) for c in _MODE_CASES],
    ids=[c[3] for c in _MODE_CASES],
)
def test_leaflet_payload_cache_lru_evicts_oldest_when_over_max(
    streamlit_stub,
    session_key: str,
    mode_id: str,
) -> None:
    max_entries = 2
    leaflet_payload_cache_store(
        session_key,
        ("a", mode_id),
        {"revision": "1", "geojson": {}},
        max_entries=max_entries,
    )
    leaflet_payload_cache_store(
        session_key,
        ("b", mode_id),
        {"revision": "2", "geojson": {}},
        max_entries=max_entries,
    )
    leaflet_payload_cache_store(
        session_key,
        ("c", mode_id),
        {"revision": "3", "geojson": {}},
        max_entries=max_entries,
    )
    assert leaflet_payload_cache_lookup(session_key, ("a", mode_id)) is None
    assert leaflet_payload_cache_lookup(session_key, ("b", mode_id)) == {
        "revision": "2",
        "geojson": {},
    }
    assert leaflet_payload_cache_lookup(session_key, ("c", mode_id)) == {
        "revision": "3",
        "geojson": {},
    }


@pytest.mark.parametrize(
    ("session_key", "mode_id"),
    [(c[0], c[3]) for c in _MODE_CASES],
    ids=[c[3] for c in _MODE_CASES],
)
def test_leaflet_payload_cache_hit_moves_entry_to_mru_end(
    streamlit_stub,
    session_key: str,
    mode_id: str,
) -> None:
    max_entries = 2
    leaflet_payload_cache_store(
        session_key,
        ("a", mode_id),
        {"revision": "1", "geojson": {}},
        max_entries=max_entries,
    )
    leaflet_payload_cache_store(
        session_key,
        ("b", mode_id),
        {"revision": "2", "geojson": {}},
        max_entries=max_entries,
    )
    assert leaflet_payload_cache_lookup(session_key, ("a", mode_id))["revision"] == "1"
    leaflet_payload_cache_store(
        session_key,
        ("c", mode_id),
        {"revision": "3", "geojson": {}},
        max_entries=max_entries,
    )
    assert leaflet_payload_cache_lookup(session_key, ("a", mode_id))["revision"] == "1"
    assert leaflet_payload_cache_lookup(session_key, ("b", mode_id)) is None


def test_leaflet_payload_cache_store_migrates_legacy_single_entry(
    streamlit_stub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Other Streamlit tests may drop/reimport this module; bind and call the
    # live module object so ``st`` patching matches store/lookup globals.
    import explorer.app.streamlit.app_prep_map_leaflet_caches as cache_module

    monkeypatch.setattr(cache_module, "st", streamlit_stub)
    session_key = ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY
    legacy_key = ("legacy",)
    streamlit_stub.session_state[session_key] = {
        "payload_cache_key": legacy_key,
        "revision": "old",
        "geojson": {"features": []},
    }

    cache_module.leaflet_payload_cache_store(
        session_key,
        ("new",),
        {"revision": "new", "geojson": {"features": [{"id": 1}]}},
        max_entries=2,
    )

    assert cache_module.leaflet_payload_cache_lookup(session_key, legacy_key)[
        "revision"
    ] == "old"
    assert cache_module.leaflet_payload_cache_lookup(session_key, ("new",))[
        "revision"
    ] == "new"

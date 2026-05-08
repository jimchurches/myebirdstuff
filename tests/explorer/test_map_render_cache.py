"""Session Folium map LRU cache (#214).

Before #214, switching map view mode cleared the entire cache in ``app_map_working_ui``, so
``prep.map_cache_hit`` never fired when returning to a previously visited mode. These tests lock in
the intended LRU behaviour: distinct ``static_map_cache_key`` tuples (e.g. ``all`` vs ``lifers``)
can coexist in ``FOLIUM_STATIC_MAP_CACHE_KEY``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("streamlit", reason="map cache helpers use Streamlit session state")

from explorer.app.streamlit.app_caches import static_map_cache_key
from explorer.app.streamlit.app_constants import FOLIUM_STATIC_MAP_CACHE_KEY
from explorer.app.streamlit.app_prep_map_ui import _map_cache_lookup, _map_cache_store


@pytest.fixture
def fake_session_state(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch ``st.session_state`` used by ``app_prep_map_ui`` cache helpers."""
    session: dict = {}
    monkeypatch.setattr(
        "explorer.app.streamlit.app_prep_map_ui.st",
        SimpleNamespace(session_state=session),
    )
    return session


def test_map_render_cache_two_view_modes_remain_addressable(fake_session_state: dict) -> None:
    df = pd.DataFrame({"Submission ID": ["s1"]})
    render_opts: tuple = ()
    key_all = static_map_cache_key(
        df,
        "all",
        "",
        "default",
        render_opts,
        taxonomy_locale="en_AU",
    )
    key_lifers = static_map_cache_key(
        df,
        "lifers",
        "",
        "default",
        render_opts,
        taxonomy_locale="en_AU",
    )
    map_all = object()
    map_lifers = object()
    _map_cache_store(key_all, {"key": key_all, "map": map_all, "warning": None})
    _map_cache_store(key_lifers, {"key": key_lifers, "map": map_lifers, "warning": None})

    got_all = _map_cache_lookup(key_all)
    got_lifers = _map_cache_lookup(key_lifers)
    assert got_all is not None and got_all.get("map") is map_all
    assert got_lifers is not None and got_lifers.get("map") is map_lifers


def test_map_render_cache_legacy_single_entry_payload_upgraded(fake_session_state: dict) -> None:
    """Backward-compatible path: one dict-shaped entry is folded into the OrderedDict."""
    df = pd.DataFrame({"Submission ID": ["s2"]})
    key = static_map_cache_key(df, "all", "", "default", (), taxonomy_locale="en_AU")
    legacy = {"key": key, "map": object(), "warning": None}
    fake_session_state[FOLIUM_STATIC_MAP_CACHE_KEY] = legacy

    got = _map_cache_lookup(key)
    assert got is not None and got.get("key") == key

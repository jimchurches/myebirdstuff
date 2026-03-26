from __future__ import annotations

import importlib
import sys
import types

import pytest


class _StubSessionState(dict):
    """Minimal dict + attribute-access for ``st.session_state.*`` usage."""

    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name: str, value):
        self[name] = value


def _install_streamlit_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a minimal `streamlit` module so UI modules can import in unit tests.

    This keeps tests runnable even when `requirements-streamlit.txt` is not installed.
    """

    stub = types.ModuleType("streamlit")
    stub.session_state = _StubSessionState()

    def fragment(fn):
        return fn

    def cache_data(*_args, **_kwargs):
        def deco(fn):
            return fn

        return deco

    # Cache decorators can appear in some imports; treat as no-ops.
    stub.fragment = fragment
    stub.cache_data = cache_data
    stub.cache_resource = cache_data

    monkeypatch.setitem(sys.modules, "streamlit", stub)


@pytest.fixture()
def streamlit_stub(monkeypatch: pytest.MonkeyPatch):
    _install_streamlit_stub(monkeypatch)
    # Ensure we re-import UI modules under the stubbed `streamlit` (shims + explorer targets).
    for name in [
        "streamlit_app.streamlit_theme",
        "streamlit_app.yearly_summary_streamlit_html",
        "streamlit_app.country_stats_streamlit_html",
        "explorer.app.streamlit.streamlit_theme",
        "explorer.app.streamlit.yearly_summary_streamlit_html",
        "explorer.app.streamlit.country_stats_streamlit_html",
    ]:
        sys.modules.pop(name, None)
    return sys.modules["streamlit"]


def test_yearly_recent_column_count_clamps(streamlit_stub) -> None:
    yearly = importlib.import_module("streamlit_app.yearly_summary_streamlit_html")
    from streamlit_app.app_constants import STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY

    st = streamlit_stub
    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 2
    assert yearly.get_yearly_recent_column_count() == 3

    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 30
    assert yearly.get_yearly_recent_column_count() == 25

    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 10
    assert yearly.get_yearly_recent_column_count() == 10


def test_sync_yearly_summary_session_inputs_sets_payload(streamlit_stub) -> None:
    yearly = importlib.import_module("streamlit_app.yearly_summary_streamlit_html")
    from streamlit_app.app_constants import YEARLY_SUMMARY_TAB_CHECKLIST_PAYLOAD_KEY

    sentinel = object()
    yearly.sync_yearly_summary_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[YEARLY_SUMMARY_TAB_CHECKLIST_PAYLOAD_KEY] is sentinel


def test_sync_country_tab_session_inputs_sets_payload(streamlit_stub) -> None:
    country = importlib.import_module("streamlit_app.country_stats_streamlit_html")
    from streamlit_app.app_constants import COUNTRY_TAB_CHECKLIST_PAYLOAD_KEY

    sentinel = object()
    country.sync_country_tab_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[COUNTRY_TAB_CHECKLIST_PAYLOAD_KEY] is sentinel


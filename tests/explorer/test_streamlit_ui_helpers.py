from __future__ import annotations

import importlib
import sys
import types

import pandas as pd
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

    This keeps tests runnable even when Streamlit deps are not installed.
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
        "streamlit_app.checklist_stats_streamlit_html",
        "streamlit_app.rankings_streamlit_html",
        "streamlit_app.maintenance_streamlit_html",
        "explorer.app.streamlit.streamlit_theme",
        "explorer.app.streamlit.yearly_summary_streamlit_html",
        "explorer.app.streamlit.country_stats_streamlit_html",
        "explorer.app.streamlit.checklist_stats_streamlit_html",
        "explorer.app.streamlit.rankings_streamlit_html",
        "explorer.app.streamlit.maintenance_streamlit_html",
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


def test_sync_checklist_stats_tab_session_inputs_sets_payload(streamlit_stub) -> None:
    checklist = importlib.import_module("streamlit_app.checklist_stats_streamlit_html")
    from streamlit_app.app_constants import CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY

    sentinel = object()
    checklist.sync_checklist_stats_tab_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY] is sentinel


def test_sync_rankings_tab_session_inputs_sets_bundle(streamlit_stub) -> None:
    rankings = importlib.import_module("streamlit_app.rankings_streamlit_html")
    from streamlit_app.app_constants import RANKINGS_TAB_BUNDLE_KEY

    sentinel = {"rankings_sections_top_n": [("t", "<p>x</p>")], "rankings_sections_other": []}
    rankings.sync_rankings_tab_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[RANKINGS_TAB_BUNDLE_KEY] is sentinel


def test_sync_maintenance_tab_session_inputs_sets_sync_dict(streamlit_stub) -> None:
    maint = importlib.import_module("streamlit_app.maintenance_streamlit_html")
    from streamlit_app.app_constants import MAINTENANCE_TAB_SYNC_KEY

    loc_df = pd.DataFrame(columns=["Location ID", "Location", "Latitude", "Longitude"])
    inc: dict = {2024: []}
    sex: dict = {2023: []}

    maint.sync_maintenance_tab_session_inputs(
        loc_df,
        close_location_meters=250,
        incomplete_by_year=inc,
        sex_notation_by_year=sex,
    )

    st = streamlit_stub
    blob = st.session_state[MAINTENANCE_TAB_SYNC_KEY]
    assert blob["loc_df"] is loc_df
    assert blob["close_location_meters"] == 250
    assert blob["incomplete_by_year"] is inc
    assert blob["sex_notation_by_year"] is sex


def test_streamlit_tab_shims_import_without_runtime(streamlit_stub) -> None:
    """Catch regressions like missing constants or bad imports (refs fragment sync wiring)."""
    importlib.import_module("streamlit_app.checklist_stats_streamlit_html")
    importlib.import_module("streamlit_app.rankings_streamlit_html")
    importlib.import_module("streamlit_app.maintenance_streamlit_html")


def test_static_map_cache_key_includes_species_overlay() -> None:
    """Folium reuse for selected-species maps must not share a key with bare species mode."""
    from explorer.app.streamlit.app_caches import static_map_cache_key

    df = pd.DataFrame({"Submission ID": ["s0"]})
    ro: tuple = ()
    no_species = static_map_cache_key(df, "species", "", "default", ro, taxonomy_locale="en_AU")
    with_species = static_map_cache_key(
        df,
        "species",
        "",
        "default",
        ro,
        taxonomy_locale="en_AU",
        species_selected_sci="Turdus migratorius",
        species_selected_common="American Robin",
        hide_non_matching_locations=False,
    )
    hide_on = static_map_cache_key(
        df,
        "species",
        "",
        "default",
        ro,
        taxonomy_locale="en_AU",
        species_selected_sci="Turdus migratorius",
        hide_non_matching_locations=True,
    )
    assert no_species != with_species
    assert with_species != hide_on


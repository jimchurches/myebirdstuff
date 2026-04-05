from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

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


class _SidebarStub:
    """Capture ``st.sidebar`` divider/markdown used by map chrome tests."""

    def __init__(self) -> None:
        self.markdown_calls: list[tuple[tuple, dict]] = []

    def divider(self) -> None:
        return None

    def markdown(self, *args, **kwargs):
        self.markdown_calls.append((args, kwargs))


def _install_streamlit_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a minimal `streamlit` module so UI modules can import in unit tests.

    This keeps tests runnable even when Streamlit deps are not installed.
    """

    stub = types.ModuleType("streamlit")
    stub.session_state = _StubSessionState()

    stub.html_calls: list[str] = []

    def html(x: str) -> None:
        stub.html_calls.append(x)

    stub.html = html

    stub.markdown_calls: list[tuple[tuple, dict]] = []

    def markdown(*args, **kwargs):
        stub.markdown_calls.append((args, kwargs))

    stub.markdown = markdown

    stub.error_calls: list[str] = []

    def error(msg: str) -> None:
        stub.error_calls.append(msg)

    stub.error = error
    stub.sidebar = _SidebarStub()

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

    components_v1 = types.ModuleType("streamlit.components.v1")
    components_v1.html_calls: list[dict] = []

    def components_html(html: str, height=None, scrolling=False) -> None:
        components_v1.html_calls.append(
            {"html": html, "height": height, "scrolling": scrolling}
        )

    components_v1.html = components_html

    components_pkg = types.ModuleType("streamlit.components")
    components_pkg.v1 = components_v1
    stub.components = components_pkg

    monkeypatch.setitem(sys.modules, "streamlit", stub)
    monkeypatch.setitem(sys.modules, "streamlit.components", components_pkg)
    monkeypatch.setitem(sys.modules, "streamlit.components.v1", components_v1)


def _drop_submodule(name: str) -> None:
    """Remove *name* from ``sys.modules`` and uncache it from its parent package.

    ``sys.modules.pop`` alone is not enough: ``from pkg import sub`` can still return a
    stale submodule object held on the parent after a pop (refs Streamlit stub tests).
    """

    sys.modules.pop(name, None)
    parent_name, _, attr = name.rpartition(".")
    if not parent_name:
        return
    parent = sys.modules.get(parent_name)
    if parent is not None and hasattr(parent, attr):
        try:
            delattr(parent, attr)
        except AttributeError:
            pass


@pytest.fixture()
def streamlit_stub(monkeypatch: pytest.MonkeyPatch):
    _install_streamlit_stub(monkeypatch)
    # Ensure we re-import UI modules under the stubbed `streamlit`.
    for name in [
        "explorer.app.streamlit.streamlit_theme",
        "explorer.app.streamlit.app_data_loading",
        "explorer.app.streamlit.app_map_ui",
        "explorer.app.streamlit.yearly_summary_streamlit_html",
        "explorer.app.streamlit.country_stats_streamlit_html",
        "explorer.app.streamlit.checklist_stats_streamlit_html",
        "explorer.app.streamlit.rankings_streamlit_html",
        "explorer.app.streamlit.maintenance_streamlit_html",
    ]:
        _drop_submodule(name)
    return sys.modules["streamlit"]


def test_yearly_recent_column_count_clamps(streamlit_stub) -> None:
    yearly = importlib.import_module("explorer.app.streamlit.yearly_summary_streamlit_html")
    from explorer.app.streamlit.app_constants import STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY

    st = streamlit_stub
    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 2
    assert yearly.get_yearly_recent_column_count() == 3

    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 30
    assert yearly.get_yearly_recent_column_count() == 25

    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 10
    assert yearly.get_yearly_recent_column_count() == 10


def test_sync_yearly_summary_session_inputs_sets_payload(streamlit_stub) -> None:
    yearly = importlib.import_module("explorer.app.streamlit.yearly_summary_streamlit_html")
    from explorer.app.streamlit.app_constants import YEARLY_SUMMARY_TAB_CHECKLIST_PAYLOAD_KEY

    sentinel = object()
    yearly.sync_yearly_summary_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[YEARLY_SUMMARY_TAB_CHECKLIST_PAYLOAD_KEY] is sentinel


def test_sync_country_tab_session_inputs_sets_payload(streamlit_stub) -> None:
    country = importlib.import_module("explorer.app.streamlit.country_stats_streamlit_html")
    from explorer.app.streamlit.app_constants import COUNTRY_TAB_CHECKLIST_PAYLOAD_KEY

    sentinel = object()
    country.sync_country_tab_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[COUNTRY_TAB_CHECKLIST_PAYLOAD_KEY] is sentinel


def test_sync_checklist_stats_tab_session_inputs_sets_payload(streamlit_stub) -> None:
    checklist = importlib.import_module("explorer.app.streamlit.checklist_stats_streamlit_html")
    from explorer.app.streamlit.app_constants import CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY

    sentinel = object()
    checklist.sync_checklist_stats_tab_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY] is sentinel


def test_sync_rankings_tab_session_inputs_sets_bundle(streamlit_stub) -> None:
    rankings = importlib.import_module("explorer.app.streamlit.rankings_streamlit_html")
    from explorer.app.streamlit.app_constants import RANKINGS_TAB_BUNDLE_KEY

    sentinel = {"rankings_sections_top_n": [("t", "<p>x</p>")], "rankings_sections_other": []}
    rankings.sync_rankings_tab_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[RANKINGS_TAB_BUNDLE_KEY] is sentinel


def test_sync_maintenance_tab_session_inputs_sets_sync_dict(streamlit_stub) -> None:
    maint = importlib.import_module("explorer.app.streamlit.maintenance_streamlit_html")
    from explorer.app.streamlit.app_constants import MAINTENANCE_TAB_SYNC_KEY

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


def test_streamlit_tab_modules_import_without_runtime(streamlit_stub) -> None:
    """Catch regressions like missing constants or bad imports (refs fragment sync wiring)."""
    importlib.import_module("explorer.app.streamlit.checklist_stats_streamlit_html")
    importlib.import_module("explorer.app.streamlit.rankings_streamlit_html")
    importlib.import_module("explorer.app.streamlit.maintenance_streamlit_html")


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


# --- app_data_loading / app_map_ui / streamlit_theme (refs #98; UI-surface regressions) ---


def _fixture_csv_bytes() -> bytes:
    return (Path(__file__).resolve().parent.parent / "fixtures" / "ebird_integration_fixture.csv").read_bytes()


def test_load_dataframe_upload_happy_path(streamlit_stub) -> None:
    from explorer.app.streamlit import app_data_loading

    raw = _fixture_csv_bytes()

    class _Up:
        name = "ebird_integration_fixture.csv"

        def getvalue(self):
            return raw

    df, prov, src_label, data_path, base = app_data_loading.load_dataframe(uploaded=_Up())
    assert df is not None and len(df) > 0
    assert prov and "Upload:" in prov and _Up.name in prov
    assert src_label is None and data_path is None
    assert base == _Up.name


def test_load_dataframe_upload_error_surfaces_st_error(streamlit_stub, monkeypatch: pytest.MonkeyPatch) -> None:
    from explorer.app.streamlit import app_data_loading

    def _fail(_src):
        raise ValueError("forced load failure")

    monkeypatch.setattr(app_data_loading, "load_dataset", _fail)

    class _Bad:
        name = "bad.csv"

        def getvalue(self):
            return b"ignored"

    df, *_rest = app_data_loading.load_dataframe(uploaded=_Bad())
    assert df is None
    assert any("Could not load CSV" in msg for msg in streamlit_stub.error_calls)


def test_load_dataframe_disk_path_and_labels(streamlit_stub, monkeypatch: pytest.MonkeyPatch) -> None:
    from explorer.app.streamlit import app_data_loading

    def _fake_load(_src):
        return pd.DataFrame({"Submission ID": ["x"]})

    monkeypatch.setattr(app_data_loading, "load_dataset", _fake_load)
    monkeypatch.setattr(
        app_data_loading,
        "build_explorer_candidate_dirs",
        lambda repo_root, cwd: (["/tmp"], ["config_yaml"]),
    )
    monkeypatch.setattr(
        app_data_loading,
        "resolve_ebird_data_file",
        lambda fn, folders, sources: ("/data/MyEBirdData.csv", "/data", "config_yaml"),
    )

    df, prov, src_label, data_path, base = app_data_loading.load_dataframe()
    assert df is not None
    assert prov and "Disk:" in prov and "/data/MyEBirdData.csv" in prov
    assert src_label == "config_yaml"
    assert data_path == "/data/MyEBirdData.csv"
    assert base == "MyEBirdData.csv"


def test_load_dataframe_falls_back_to_upload_cache(streamlit_stub, monkeypatch: pytest.MonkeyPatch) -> None:
    from explorer.app.streamlit import app_data_loading

    def _fake_load(_src):
        return pd.DataFrame({"Submission ID": ["cache"]})

    monkeypatch.setattr(app_data_loading, "load_dataset", _fake_load)
    monkeypatch.setattr(
        app_data_loading,
        "build_explorer_candidate_dirs",
        lambda repo_root, cwd: (["/tmp"], ["x"]),
    )
    monkeypatch.setattr(
        app_data_loading,
        "resolve_ebird_data_file",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()),
    )

    raw = _fixture_csv_bytes()
    df, prov, *_rest = app_data_loading.load_dataframe(upload_cache=(raw, "cached.csv"))
    assert df is not None
    assert prov and "Upload:" in prov and "cached.csv" in prov


def test_ensure_streamlit_map_basemap_height_keys_seeds_and_repairs(streamlit_stub) -> None:
    from explorer.app.streamlit.app_map_ui import ensure_streamlit_map_basemap_height_keys
    from explorer.app.streamlit.defaults import MAP_BASEMAP_DEFAULT, MAP_HEIGHT_PX_DEFAULT

    st = streamlit_stub
    st.session_state.clear()
    ensure_streamlit_map_basemap_height_keys()
    assert st.session_state["streamlit_map_basemap"] == MAP_BASEMAP_DEFAULT
    assert st.session_state["streamlit_map_height_px"] == MAP_HEIGHT_PX_DEFAULT

    st.session_state["streamlit_map_basemap"] = "__not_a_real_basemap__"
    ensure_streamlit_map_basemap_height_keys()
    assert st.session_state["streamlit_map_basemap"] == MAP_BASEMAP_DEFAULT


def test_inject_spinner_theme_css_idempotent(streamlit_stub) -> None:
    from explorer.app.streamlit.app_constants import SPINNER_THEME_CSS, SPINNER_THEME_CSS_INJECTED_KEY
    from explorer.app.streamlit.app_map_ui import inject_spinner_theme_css

    st = streamlit_stub
    st.html_calls.clear()
    inject_spinner_theme_css()
    assert len(st.html_calls) == 1
    assert st.html_calls[0] == SPINNER_THEME_CSS.strip()
    assert st.session_state[SPINNER_THEME_CSS_INJECTED_KEY] is True
    st.html_calls.clear()
    inject_spinner_theme_css()
    assert st.html_calls == []


def test_inject_spinner_emoji_animation_html_includes_theme_and_emojis(streamlit_stub) -> None:
    import streamlit.components.v1 as components

    from explorer.app.streamlit.app_map_ui import inject_spinner_emoji_animation
    from explorer.app.streamlit.defaults import THEME_PRIMARY_HEX
    from explorer.app.streamlit.streamlit_ui_constants import CHECKLIST_STATS_SPINNER_EMOJIS

    inject_spinner_emoji_animation()
    assert len(components.html_calls) == 1
    payload = components.html_calls[0]["html"]
    assert THEME_PRIMARY_HEX in payload
    for emoji in CHECKLIST_STATS_SPINNER_EMOJIS:
        assert emoji in payload
    assert components.html_calls[0]["height"] == 52
    assert components.html_calls[0]["scrolling"] is False


def test_inject_streamlit_checklist_css_composes_table_and_surface(streamlit_stub) -> None:
    from explorer.presentation.checklist_stats_display import CHECKLIST_STATS_TABLE_CSS

    from explorer.app.streamlit import streamlit_theme

    streamlit_stub.markdown_calls.clear()
    streamlit_theme.inject_streamlit_checklist_css()
    assert streamlit_stub.markdown_calls
    style_blob = streamlit_stub.markdown_calls[-1][0][0]
    assert "<style>" in style_blob
    assert CHECKLIST_STATS_TABLE_CSS in style_blob
    assert streamlit_theme.CHECKLIST_STATS_HTML_TAB_SURFACE_CSS in style_blob

    if streamlit_theme.USE_EBIRD_BLUE_HTML_TAB_THEME:
        from explorer.presentation.checklist_stats_display import CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE

        assert streamlit_theme.CHECKLIST_STATS_HTML_TAB_SURFACE_CSS == CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    else:
        from explorer.presentation.checklist_stats_display import CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS

        assert streamlit_theme.CHECKLIST_STATS_HTML_TAB_SURFACE_CSS == CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS


def test_inject_streamlit_checklist_css_appends_extra_css(streamlit_stub) -> None:
    from explorer.app.streamlit import streamlit_theme

    streamlit_stub.markdown_calls.clear()
    streamlit_theme.inject_streamlit_checklist_css("/*extra-tab*/")
    style_blob = streamlit_stub.markdown_calls[-1][0][0]
    assert "/*extra-tab*/" in style_blob


def test_sidebar_footer_links_include_profile_urls(streamlit_stub) -> None:
    from explorer.app.streamlit.app_map_ui import sidebar_footer_links
    from explorer.app.streamlit.streamlit_ui_constants import (
        EBIRD_PROFILE_URL,
        EXPLORER_README_GITHUB_URL,
        GITHUB_REPO_URL,
        INSTAGRAM_PROFILE_URL,
    )

    streamlit_stub.sidebar.markdown_calls.clear()
    sidebar_footer_links()
    combined = " ".join(str(c[0][0]) for c in streamlit_stub.sidebar.markdown_calls)
    assert GITHUB_REPO_URL in combined
    assert EBIRD_PROFILE_URL in combined
    assert INSTAGRAM_PROFILE_URL in combined
    assert EXPLORER_README_GITHUB_URL in combined

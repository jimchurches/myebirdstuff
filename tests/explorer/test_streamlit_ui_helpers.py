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


class _SpinnerCtx:
    def __init__(self, stub, msg: str) -> None:
        self._stub = stub
        self._msg = msg

    def __enter__(self):
        self._stub.spinner_calls.append(self._msg)
        return self

    def __exit__(self, *_args) -> bool:
        return False


class _PlaceholderStub:
    def empty(self) -> None:
        return None

    def container(self):
        class _Ctx:
            def __enter__(self):
                return self

            def __exit__(self, *_args) -> bool:
                return False

        return _Ctx()


class _SidebarStub:
    """Capture ``st.sidebar`` divider/markdown used by map chrome tests."""

    def __init__(self, stub_session) -> None:
        self._stub_session = stub_session
        self.markdown_calls: list[tuple[tuple, dict]] = []
        self.caption_calls: list[str] = []
        self.radio_calls: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> bool:
        return False

    def divider(self) -> None:
        return None

    def caption(self, label: str) -> None:
        self.caption_calls.append(label)

    def markdown(self, *args, **kwargs):
        self.markdown_calls.append((args, kwargs))

    def radio(self, label: str, options, key=None, horizontal: bool = False, **kwargs):
        self.radio_calls.append((label, tuple(options), key, horizontal, kwargs))
        if key is not None and key in self._stub_session:
            v = self._stub_session[key]
            if v in options:
                return v
        return options[0] if options else None


def _install_streamlit_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a minimal `streamlit` module so UI modules can import in unit tests.

    This keeps tests runnable even when Streamlit deps are not installed.
    """

    stub = types.ModuleType("streamlit")
    stub.session_state = _StubSessionState()
    # Dict-like secrets for tests (e.g. hosted notice flag); matches ``key in st.secrets`` usage.
    stub.secrets: dict[str, str] = {}
    stub.spinner_calls: list[str] = []

    def spinner(msg: str):
        return _SpinnerCtx(stub, msg)

    stub.spinner = spinner

    def empty():
        return _PlaceholderStub()

    stub.empty = empty

    class _ContainerStub:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

        def empty(self):
            return _PlaceholderStub()

    def container(**_kwargs):
        return _ContainerStub()

    stub.container = container

    stub.html_calls: list[str] = []

    def html(x: str) -> None:
        stub.html_calls.append(x)

    stub.html = html

    stub.iframe_calls: list[dict] = []

    def iframe(src: str, *, width="stretch", height="content", tab_index=None) -> None:
        stub.iframe_calls.append(
            {"src": src, "width": width, "height": height, "tab_index": tab_index}
        )

    stub.iframe = iframe

    stub.markdown_calls: list[tuple[tuple, dict]] = []

    def markdown(*args, **kwargs):
        stub.markdown_calls.append((args, kwargs))

    stub.markdown = markdown

    stub.error_calls: list[str] = []

    def error(msg: str) -> None:
        stub.error_calls.append(msg)

    stub.error = error
    stub.sidebar = _SidebarStub(stub.session_state)

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

    class _ContextUrl:
        __slots__ = ("hostname",)

        def __init__(self, hostname: str = "localhost") -> None:
            self.hostname = hostname

    class _ContextStub:
        def __init__(self) -> None:
            self.url = _ContextUrl()

    stub.context = _ContextStub()

    stub.info_calls: list[tuple[tuple, dict]] = []

    def info(*args, **kwargs):
        stub.info_calls.append((args, kwargs))

    stub.info = info

    def divider() -> None:
        return None

    stub.divider = divider

    class _ColumnStub:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

    def columns(spec):
        return [_ColumnStub() for _ in spec]

    stub.columns = columns

    def download_button(*_args, **_kwargs) -> None:
        return None

    stub.download_button = download_button

    def button(*_args, **_kwargs) -> None:
        return None

    stub.button = button

    def warning(*_args, **_kwargs) -> None:
        return None

    stub.warning = warning

    components_v1 = types.ModuleType("streamlit.components.v1")
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
        "explorer.app.streamlit.bird_families_streamlit_html",
        "explorer.app.streamlit.maintenance_streamlit_html",
        "explorer.app.streamlit.app_landing_ui",
        "explorer.app.streamlit.explorer_update_notice",
        "explorer.app.streamlit.explorer_build_version",
        "explorer.app.streamlit.social_cards_streamlit_ui",
        "explorer.app.streamlit.social_cards_png_export_ui",
        "explorer.app.streamlit.social_cards_stat_picker_ui",
    ]:
        _drop_submodule(name)
    return sys.modules["streamlit"]


def test_yearly_recent_column_count_clamps(streamlit_stub) -> None:
    yearly = importlib.import_module("explorer.app.streamlit.yearly_summary_streamlit_html")
    from explorer.app.streamlit.app_constants import (
        STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY,
    )

    st = streamlit_stub
    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 2
    assert yearly.get_yearly_recent_column_count() == 3

    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 30
    assert yearly.get_yearly_recent_column_count() == 25

    st.session_state[STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY] = 10
    assert yearly.get_yearly_recent_column_count() == 10


def test_sync_yearly_summary_session_inputs_sets_payload(streamlit_stub) -> None:
    yearly = importlib.import_module("explorer.app.streamlit.yearly_summary_streamlit_html")
    from explorer.app.streamlit.app_constants import (
        YEARLY_SUMMARY_TAB_CHECKLIST_PAYLOAD_KEY,
    )

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
    from explorer.app.streamlit.app_constants import (
        CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY,
    )

    sentinel = object()
    checklist.sync_checklist_stats_tab_session_inputs(sentinel)

    st = streamlit_stub
    assert st.session_state[CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY] is sentinel


def test_sync_ranking_lists_families_bundle_sets_bundle(streamlit_stub) -> None:
    rankings = importlib.import_module("explorer.app.streamlit.rankings_streamlit_html")
    from explorer.app.streamlit.app_constants import RANKING_LISTS_FAMILIES_BUNDLE_KEY

    sentinel = {"rankings_sections_top_n": [("t", "<p>x</p>")], "rankings_sections_other": []}
    rankings.sync_ranking_lists_families_bundle(sentinel)

    st = streamlit_stub
    assert st.session_state[RANKING_LISTS_FAMILIES_BUNDLE_KEY] is sentinel


def test_run_families_fragment_load_message_without_bundle(streamlit_stub, monkeypatch) -> None:
    bird = importlib.import_module("explorer.app.streamlit.bird_families_streamlit_html")
    render_calls: list[dict] = []
    monkeypatch.setattr(
        bird,
        "render_families_streamlit_tab_from_bundle",
        lambda bundle: render_calls.append(bundle),
    )
    from explorer.app.streamlit.app_constants import RANKING_LISTS_FAMILIES_BUNDLE_KEY

    st = streamlit_stub
    st.session_state.pop(RANKING_LISTS_FAMILIES_BUNDLE_KEY, None)
    bird.run_families_streamlit_tab_fragment()
    assert render_calls == []
    assert any("Bird Families" in str(args[0]) for args, _ in st.info_calls)


def test_run_families_fragment_delegates_when_bundle_present(streamlit_stub, monkeypatch) -> None:
    bird = importlib.import_module("explorer.app.streamlit.bird_families_streamlit_html")
    render_calls: list[dict] = []
    monkeypatch.setattr(
        bird,
        "render_families_streamlit_tab_from_bundle",
        lambda bundle: render_calls.append(bundle),
    )
    from explorer.app.streamlit.app_constants import RANKING_LISTS_FAMILIES_BUNDLE_KEY
    from explorer.app.streamlit.bird_families_streamlit_html import (
        GROUP_COVERAGE_SUMMARY_KEY,
    )

    bundle = {
        "rankings_sections_top_n": [],
        GROUP_COVERAGE_SUMMARY_KEY: pd.DataFrame(),
    }
    st = streamlit_stub
    st.session_state[RANKING_LISTS_FAMILIES_BUNDLE_KEY] = bundle
    bird.run_families_streamlit_tab_fragment()
    assert len(render_calls) == 1
    assert render_calls[0] is bundle


def test_render_families_empty_summary_shows_taxonomy_unavailable(streamlit_stub) -> None:
    bird = importlib.import_module("explorer.app.streamlit.bird_families_streamlit_html")
    from explorer.app.streamlit.bird_families_streamlit_html import (
        GROUP_COVERAGE_SUMMARY_KEY,
    )

    st = streamlit_stub
    st.info_calls.clear()
    bird.render_families_streamlit_tab_from_bundle({GROUP_COVERAGE_SUMMARY_KEY: pd.DataFrame()})
    assert any("taxonomy" in str(args[0]).lower() for args, _ in st.info_calls)


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
    importlib.import_module("explorer.app.streamlit.bird_families_streamlit_html")
    importlib.import_module("explorer.app.streamlit.maintenance_streamlit_html")


def test_leaflet_payload_cache_key_includes_species_overlay() -> None:
    """Species map cache keys must differ for overlay vs awaiting-selection vs hide-non-matching toggles."""
    from explorer.app.streamlit.app_caches import leaflet_payload_cache_key

    df = pd.DataFrame({"Submission ID": ["s0"]})
    ro: tuple = ()
    no_species = leaflet_payload_cache_key(df, "species", "", "default", ro, taxonomy_locale="en_AU")
    with_species = leaflet_payload_cache_key(
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
    hide_on = leaflet_payload_cache_key(
        df,
        "species",
        "",
        "default",
        ro,
        taxonomy_locale="en_AU",
        species_selected_sci="Turdus migratorius",
        hide_non_matching_locations=True,
    )
    empty_awaiting_species = leaflet_payload_cache_key(
        df,
        "species",
        "",
        "default",
        ro,
        taxonomy_locale="en_AU",
        hide_non_matching_locations=True,
    )
    assert no_species != with_species
    assert with_species != hide_on
    assert empty_awaiting_species != no_species

    base_all = leaflet_payload_cache_key(df, "all", "", "default", ro, taxonomy_locale="en_AU")
    all_with_gps = leaflet_payload_cache_key(
        df,
        "all",
        "",
        "default",
        ro,
        taxonomy_locale="en_AU",
        go_to_gps_pin=(-33.0, 151.0),
    )
    assert base_all != all_with_gps


# --- app_data_loading / app_map_ui / streamlit_theme (UI-surface regressions) ---


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


def test_load_dataframe_upload_cache_error_surfaces_st_error(
    streamlit_stub, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session upload-cache replay uses the same error path as a fresh upload."""
    from explorer.app.streamlit import app_data_loading

    def _fail(_src):
        raise ValueError("forced cache load failure")

    monkeypatch.setattr(app_data_loading, "load_dataset", _fail)
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

    df, *_rest = app_data_loading.load_dataframe(upload_cache=(b"not-valid-csv", "cached.csv"))
    assert df is None
    assert any("Could not load CSV" in msg for msg in streamlit_stub.error_calls)


def test_ensure_streamlit_map_basemap_height_keys_seeds_and_repairs(streamlit_stub) -> None:
    from explorer.app.streamlit.app_map_ui import (
        ensure_streamlit_map_basemap_height_keys,
    )
    from explorer.app.streamlit.defaults import (
        MAP_BASEMAP_DEFAULT,
        MAP_HEIGHT_PX_DEFAULT,
    )

    st = streamlit_stub
    st.session_state.clear()
    ensure_streamlit_map_basemap_height_keys()
    assert st.session_state["streamlit_map_basemap_saved"] == MAP_BASEMAP_DEFAULT
    assert st.session_state["streamlit_map_basemap"] == MAP_BASEMAP_DEFAULT
    assert st.session_state["streamlit_map_height_px_saved"] == MAP_HEIGHT_PX_DEFAULT
    assert st.session_state["streamlit_map_height_px"] == MAP_HEIGHT_PX_DEFAULT

    st.session_state["streamlit_map_basemap"] = "__not_a_real_basemap__"
    ensure_streamlit_map_basemap_height_keys()
    assert st.session_state["streamlit_map_basemap"] == MAP_BASEMAP_DEFAULT


def test_inject_spinner_theme_css_emits_every_run(streamlit_stub) -> None:
    from explorer.app.streamlit.app_constants import SPINNER_THEME_CSS
    from explorer.app.streamlit.app_map_ui import inject_spinner_theme_css

    st = streamlit_stub
    st.html_calls.clear()
    inject_spinner_theme_css()
    assert len(st.html_calls) == 1
    assert "not(:last-of-type)" in SPINNER_THEME_CSS
    assert st.html_calls[0] == SPINNER_THEME_CSS.strip()
    st.html_calls.clear()
    inject_spinner_theme_css()
    assert len(st.html_calls) == 1
    assert st.html_calls[0] == SPINNER_THEME_CSS.strip()


def test_inject_spinner_emoji_animation_html_includes_theme_and_emojis(streamlit_stub) -> None:
    from explorer.app.streamlit.app_map_ui import inject_spinner_emoji_animation
    from explorer.app.streamlit.defaults import THEME_PRIMARY_HEX
    from explorer.app.streamlit.streamlit_ui_constants import (
        CHECKLIST_STATS_SPINNER_EMOJIS,
    )

    inject_spinner_emoji_animation()
    assert len(streamlit_stub.iframe_calls) == 1
    payload = streamlit_stub.iframe_calls[0]["src"]
    assert THEME_PRIMARY_HEX in payload
    for emoji in CHECKLIST_STATS_SPINNER_EMOJIS:
        assert emoji in payload
    assert streamlit_stub.iframe_calls[0]["height"] == 52


def test_place_spinner_emoji_strip_uses_keyed_container(streamlit_stub, monkeypatch) -> None:
    from explorer.app.streamlit import app_map_ui
    from explorer.app.streamlit.app_constants import PREP_SPINNER_EMOJI_CONTAINER_KEY

    seen: list[str | None] = []

    class _Host:
        def empty(self):
            return streamlit_stub.empty()

    def _container(*, key=None, **_kwargs):
        seen.append(key)
        return _Host()

    monkeypatch.setattr(streamlit_stub, "container", _container)
    monkeypatch.setattr(app_map_ui, "inject_spinner_emoji_animation", lambda: None)

    placeholder = app_map_ui.place_spinner_emoji_strip()
    assert seen == [PREP_SPINNER_EMOJI_CONTAINER_KEY]
    assert placeholder is not None
    placeholder.empty()


def test_inject_auto_click_streamlit_download_js_uses_iframe_with_label_and_parent_click(
    streamlit_stub,
) -> None:
    from explorer.app.streamlit.app_map_ui import (
        inject_auto_click_streamlit_download_js,
    )

    label = "Export map HTML"
    streamlit_stub.iframe_calls.clear()
    inject_auto_click_streamlit_download_js(button_label=label)
    assert len(streamlit_stub.iframe_calls) == 1
    payload = streamlit_stub.iframe_calls[0]["src"]
    assert label in payload
    assert "window.parent.document" in payload
    assert 'data-testid="stDownloadButton"' in payload
    assert streamlit_stub.iframe_calls[0]["height"] == 1


def test_lazy_png_export_cache_clears_stale_bytes(streamlit_stub) -> None:
    ui = importlib.import_module("explorer.app.streamlit.social_cards_png_export_ui")
    st = streamlit_stub
    old_fingerprint = ("old",)
    new_fingerprint = ("new",)

    st.session_state[ui.SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY] = b"png"
    st.session_state[ui.SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY] = old_fingerprint
    st.session_state[ui.SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY] = True

    assert ui._lazy_png_export_ready(old_fingerprint) == b"png"
    assert ui._lazy_png_export_ready(new_fingerprint) is None

    ui._clear_stale_png_export(new_fingerprint)

    assert ui.SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY not in st.session_state
    assert ui.SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY not in st.session_state
    assert ui.SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY not in st.session_state


def test_inject_streamlit_checklist_css_composes_table_and_surface(streamlit_stub) -> None:
    from explorer.app.streamlit import streamlit_theme
    from explorer.presentation.checklist_stats_display import CHECKLIST_STATS_TABLE_CSS

    streamlit_stub.html_calls.clear()
    streamlit_theme.inject_streamlit_checklist_css()
    assert streamlit_stub.html_calls
    style_blob = streamlit_stub.html_calls[-1]
    assert "<style>" in style_blob
    assert CHECKLIST_STATS_TABLE_CSS in style_blob
    assert streamlit_theme.CHECKLIST_STATS_HTML_TAB_SURFACE_CSS in style_blob

    if streamlit_theme.USE_EBIRD_BLUE_HTML_TAB_THEME:
        from explorer.presentation.checklist_stats_display import (
            CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE,
        )

        assert streamlit_theme.CHECKLIST_STATS_HTML_TAB_SURFACE_CSS == CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    else:
        from explorer.presentation.checklist_stats_display import (
            CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS,
        )

        assert streamlit_theme.CHECKLIST_STATS_HTML_TAB_SURFACE_CSS == CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS


def test_inject_streamlit_checklist_css_appends_extra_css(streamlit_stub) -> None:
    from explorer.app.streamlit import streamlit_theme

    streamlit_stub.html_calls.clear()
    streamlit_theme.inject_streamlit_checklist_css("/*extra-tab*/")
    style_blob = streamlit_stub.html_calls[-1]
    assert "/*extra-tab*/" in style_blob


def test_inject_main_tab_panel_top_compact_css_emits_selectors(streamlit_stub) -> None:
    from explorer.app.streamlit import streamlit_theme

    streamlit_stub.html_calls.clear()
    streamlit_theme.inject_main_tab_panel_top_compact_css()
    assert streamlit_stub.html_calls
    blob = streamlit_stub.html_calls[-1]
    assert "<style>" in blob and "</style>" in blob
    assert '[data-baseweb="tab-panel"]' in blob
    assert 'div[role="tabpanel"]' in blob
    assert "padding-top:" in blob


def test_inject_app_header_css_emits_pebird_header(streamlit_stub) -> None:
    from explorer.app.streamlit import streamlit_theme

    streamlit_stub.html_calls.clear()
    streamlit_theme.inject_app_header_css()
    blob = streamlit_stub.html_calls[-1]
    assert ".pebird-app-header" in blob
    assert "h1" in blob and "p" in blob
    assert "margin-bottom" in blob and "padding-bottom" in blob


def test_sidebar_footer_links_include_profile_urls(streamlit_stub, monkeypatch) -> None:
    from explorer.app.streamlit.app_map_ui import sidebar_footer_links
    from explorer.app.streamlit.streamlit_ui_constants import (
        BUY_ME_A_COFFEE_URL,
        EBIRD_PROFILE_URL,
        GITHUB_REPO_URL,
        INSTAGRAM_PROFILE_URL,
    )

    fixed_docs = f"{GITHUB_REPO_URL}/blob/main/docs/explorer/README.md"
    monkeypatch.setattr(
        "explorer.app.streamlit.app_map_ui.explorer_readme_github_url",
        lambda: fixed_docs,
    )

    streamlit_stub.sidebar.markdown_calls.clear()
    sidebar_footer_links()
    combined = " ".join(str(c[0][0]) for c in streamlit_stub.sidebar.markdown_calls)
    assert GITHUB_REPO_URL in combined
    assert EBIRD_PROFILE_URL in combined
    assert INSTAGRAM_PROFILE_URL in combined
    assert fixed_docs in combined
    assert BUY_ME_A_COFFEE_URL in combined
    assert "Buy me a coffee</a>" in combined


_HOSTED_NOTICE_ENV_KEY = "STREAMLIT_SHOW_HOSTED_PERFORMANCE_NOTICE"


def _reload_app_landing_ui() -> types.ModuleType:
    _drop_submodule("explorer.app.streamlit.app_landing_ui")
    return importlib.import_module("explorer.app.streamlit.app_landing_ui")


def _landing_ui_with_clean_flag(streamlit_stub, monkeypatch: pytest.MonkeyPatch):
    """Fresh ``app_landing_ui`` import with no secret/env flag set."""
    monkeypatch.delenv(_HOSTED_NOTICE_ENV_KEY, raising=False)
    streamlit_stub.secrets = {}
    return _reload_app_landing_ui()


def test_hosted_notice_flag_off_when_unset(streamlit_stub, monkeypatch) -> None:
    landing = _landing_ui_with_clean_flag(streamlit_stub, monkeypatch)
    assert landing._env_flag_true(_HOSTED_NOTICE_ENV_KEY) is False
    assert landing.show_hosted_performance_notice() is False


@pytest.mark.parametrize("value", ("1", "true", "TRUE", "yes", "YES", "on", "ON", "  true  "))
def test_hosted_notice_flag_on_from_env(streamlit_stub, monkeypatch, value: str) -> None:
    landing = _landing_ui_with_clean_flag(streamlit_stub, monkeypatch)
    monkeypatch.setenv(_HOSTED_NOTICE_ENV_KEY, value)
    assert landing._env_flag_true(_HOSTED_NOTICE_ENV_KEY) is True
    assert landing.show_hosted_performance_notice() is True


@pytest.mark.parametrize("value", ("0", "false", "FALSE", "no", "off", "maybe", ""))
def test_hosted_notice_flag_off_from_env(streamlit_stub, monkeypatch, value: str) -> None:
    landing = _landing_ui_with_clean_flag(streamlit_stub, monkeypatch)
    monkeypatch.setenv(_HOSTED_NOTICE_ENV_KEY, value)
    assert landing._env_flag_true(_HOSTED_NOTICE_ENV_KEY) is False


def test_hosted_notice_flag_on_from_secrets(streamlit_stub, monkeypatch) -> None:
    landing = _landing_ui_with_clean_flag(streamlit_stub, monkeypatch)
    streamlit_stub.secrets[_HOSTED_NOTICE_ENV_KEY] = "true"
    assert landing._env_flag_true(_HOSTED_NOTICE_ENV_KEY) is True
    assert landing.show_hosted_performance_notice() is True


def test_hosted_notice_secrets_take_precedence_over_env(streamlit_stub, monkeypatch) -> None:
    landing = _landing_ui_with_clean_flag(streamlit_stub, monkeypatch)
    streamlit_stub.secrets[_HOSTED_NOTICE_ENV_KEY] = "false"
    monkeypatch.setenv(_HOSTED_NOTICE_ENV_KEY, "true")
    assert landing._env_flag_true(_HOSTED_NOTICE_ENV_KEY) is False


def test_hosted_notice_env_fallback_when_secrets_unavailable(streamlit_stub, monkeypatch) -> None:
    class _SecretsUnavailable:
        def __contains__(self, item: object) -> bool:
            raise OSError("secrets backend unavailable")

        def __getitem__(self, item: object) -> str:
            raise OSError("secrets backend unavailable")

    landing = _landing_ui_with_clean_flag(streamlit_stub, monkeypatch)
    monkeypatch.setattr(streamlit_stub, "secrets", _SecretsUnavailable(), raising=False)
    monkeypatch.setenv(_HOSTED_NOTICE_ENV_KEY, "true")
    assert landing._env_flag_true(_HOSTED_NOTICE_ENV_KEY) is True


def _reload_explorer_update_notice() -> types.ModuleType:
    _drop_submodule("explorer.app.streamlit.explorer_update_notice")
    _drop_submodule("explorer.app.streamlit.explorer_build_version")
    return importlib.import_module("explorer.app.streamlit.explorer_update_notice")


def test_should_offer_update_check_false_on_streamlit_cloud_host(
    streamlit_stub, monkeypatch, tmp_path: Path
) -> None:
    un = _reload_explorer_update_notice()
    streamlit_stub.context.url.hostname = "personal-ebird-explorer.streamlit.app"
    monkeypatch.delenv("EXPLORER_UPDATE_CHECK", raising=False)
    root = str(tmp_path)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    assert un.should_offer_explorer_update_check(root) is False


def test_should_offer_update_check_force_on_overrides_cloud_host(
    streamlit_stub, monkeypatch, tmp_path: Path
) -> None:
    un = _reload_explorer_update_notice()
    streamlit_stub.context.url.hostname = "x.streamlit.app"
    monkeypatch.setenv("EXPLORER_UPDATE_CHECK", "1")
    root = str(tmp_path)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    assert un.should_offer_explorer_update_check(root) is True


def test_should_offer_update_check_yaml_opt_out(streamlit_stub, monkeypatch, tmp_path: Path) -> None:
    un = _reload_explorer_update_notice()
    streamlit_stub.context.url.hostname = "localhost"
    monkeypatch.delenv("EXPLORER_UPDATE_CHECK", raising=False)
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text("check_for_updates: false\n", encoding="utf-8")
    assert un.should_offer_explorer_update_check(str(tmp_path)) is False


def test_sidebar_footer_links_shows_update_notice_when_remote_newer(
    streamlit_stub, monkeypatch, tmp_path: Path
) -> None:
    _drop_submodule("explorer.app.streamlit.explorer_update_notice")
    _drop_submodule("explorer.app.streamlit.explorer_build_version")
    _drop_submodule("explorer.app.streamlit.app_map_ui")
    un = importlib.import_module("explorer.app.streamlit.explorer_update_notice")
    monkeypatch.setattr(
        un,
        "_fetch_github_latest_release_uncached",
        lambda: (
            "2099-12-31",
            "https://github.com/jimchurches/myebirdstuff/releases/tag/2099-12-31",
        ),
    )
    monkeypatch.setattr(un, "EXPLORER_BUILD_VERSION", "2020-01-01")
    streamlit_stub.context.url.hostname = "localhost"
    monkeypatch.delenv("EXPLORER_UPDATE_CHECK", raising=False)
    from explorer.app.streamlit.app_map_ui import sidebar_footer_links

    streamlit_stub.sidebar.markdown_calls.clear()
    sidebar_footer_links()
    combined = " ".join(str(c[0][0]) for c in streamlit_stub.sidebar.markdown_calls)
    assert "New version available" in combined
    assert "2099-12-31" in combined

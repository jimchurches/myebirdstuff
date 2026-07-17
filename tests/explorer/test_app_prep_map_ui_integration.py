"""Integration tests for map prep spinners and Leaflet payload cache wiring."""

from __future__ import annotations

import json
from collections import OrderedDict
from contextlib import contextmanager
from typing import Any

import pandas as pd
import pytest

from tests.explorer.test_streamlit_map_prep import _tiny_df
from tests.explorer.test_streamlit_ui_helpers import (
    _drop_submodule,
    _install_streamlit_stub,
)


@pytest.fixture
def streamlit_stub(monkeypatch: pytest.MonkeyPatch):
    _install_streamlit_stub(monkeypatch)
    import streamlit as st

    st.session_state.clear()
    _drop_submodule("explorer.app.streamlit.app_prep_map_ui")
    _drop_submodule("explorer.app.streamlit.app_prep_map_tab_prep")
    _drop_submodule("explorer.app.streamlit.app_prep_map_leaflet_caches")
    return st


def _patch_tab_prep_caches(monkeypatch: pytest.MonkeyPatch, app_prep_map_tab_prep) -> None:
    monkeypatch.setattr(app_prep_map_tab_prep, "cached_checklist_stats_payload", lambda *_a, **_k: {})
    monkeypatch.setattr(
        app_prep_map_tab_prep, "cached_full_export_checklist_stats_payload", lambda *_a, **_k: None
    )
    monkeypatch.setattr(app_prep_map_tab_prep, "build_ranking_lists_families_bundle", lambda *_a, **_k: {})
    monkeypatch.setattr(app_prep_map_tab_prep, "cached_sex_notation_by_year", lambda *_a: {})
    monkeypatch.setattr(
        app_prep_map_tab_prep, "full_location_data_for_maintenance", lambda *_a: pd.DataFrame()
    )


def _seed_prep_session_defaults(st) -> None:
    from explorer.app.streamlit.app_constants import (
        STREAMLIT_CLOSE_LOCATION_METERS_KEY,
        STREAMLIT_COUNTRY_TAB_SORT_KEY,
        STREAMLIT_HIGH_COUNT_SORT_KEY,
        STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY,
        STREAMLIT_RANKINGS_TOP_N_KEY,
    )
    from explorer.core.settings_schema_defaults import (
        MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT,
        TABLES_HIGH_COUNT_SORT_DEFAULT,
        TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT,
        TABLES_RANKINGS_TOP_N_DEFAULT,
    )

    st.session_state.setdefault(STREAMLIT_RANKINGS_TOP_N_KEY, TABLES_RANKINGS_TOP_N_DEFAULT)
    st.session_state.setdefault(STREAMLIT_HIGH_COUNT_SORT_KEY, TABLES_HIGH_COUNT_SORT_DEFAULT)
    st.session_state.setdefault(STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY, TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT)
    st.session_state.setdefault(STREAMLIT_COUNTRY_TAB_SORT_KEY, "")
    st.session_state.setdefault(
        STREAMLIT_CLOSE_LOCATION_METERS_KEY, MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT
    )


def test_apply_dataset_signature_change_clears_leaflet_caches(
    streamlit_stub,
) -> None:
    from explorer.app.streamlit.app_constants import (
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
        EBIRD_DATA_SIG_KEY,
        FAMILY_LEAFLET_PAYLOAD_CACHE_KEY,
        LEAFLET_EXPORT_HTML_CACHE_KEY,
        LIFER_LEAFLET_PAYLOAD_CACHE_KEY,
        SPECIES_LEAFLET_PAYLOAD_CACHE_KEY,
    )
    from explorer.app.streamlit.app_prep_map_ui import (
        apply_dataset_signature_for_map_caches,
    )

    st = streamlit_stub
    df_a = _tiny_df()
    df_b = df_a.copy()
    df_b.loc[0, "Submission ID"] = "S2"

    from explorer.core.map_prep import data_signature_for_caches

    st.session_state[EBIRD_DATA_SIG_KEY] = data_signature_for_caches(df_a, "disk")
    st.session_state[ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY] = OrderedDict(
        [(("ck",), {"revision": "1"})]
    )
    st.session_state[LIFER_LEAFLET_PAYLOAD_CACHE_KEY] = OrderedDict()
    st.session_state[SPECIES_LEAFLET_PAYLOAD_CACHE_KEY] = OrderedDict()
    st.session_state[FAMILY_LEAFLET_PAYLOAD_CACHE_KEY] = OrderedDict(
        [(("family",), {"revision": "family-old"})]
    )
    st.session_state[LEAFLET_EXPORT_HTML_CACHE_KEY] = OrderedDict()

    assert apply_dataset_signature_for_map_caches(df_b, "disk") is True
    assert st.session_state[EBIRD_DATA_SIG_KEY] == data_signature_for_caches(df_b, "disk")
    assert ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY not in st.session_state
    assert LIFER_LEAFLET_PAYLOAD_CACHE_KEY not in st.session_state
    assert SPECIES_LEAFLET_PAYLOAD_CACHE_KEY not in st.session_state
    assert FAMILY_LEAFLET_PAYLOAD_CACHE_KEY not in st.session_state
    assert LEAFLET_EXPORT_HTML_CACHE_KEY not in st.session_state


def test_apply_dataset_signature_unchanged_preserves_leaflet_cache(
    streamlit_stub,
) -> None:
    from explorer.app.streamlit.app_constants import (
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
        EBIRD_DATA_SIG_KEY,
    )
    from explorer.app.streamlit.app_prep_map_ui import (
        apply_dataset_signature_for_map_caches,
    )
    from explorer.core.map_prep import data_signature_for_caches

    st = streamlit_stub
    df = _tiny_df()
    sig = data_signature_for_caches(df, "disk")
    st.session_state[EBIRD_DATA_SIG_KEY] = sig
    cache = OrderedDict([(("ck",), {"revision": "keep"})])
    st.session_state[ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY] = cache

    assert apply_dataset_signature_for_map_caches(df, "disk") is False
    assert st.session_state[ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY] is cache


def test_leaflet_payload_cache_miss_when_revision_extra_changes(streamlit_stub) -> None:
    from explorer.app.streamlit.app_caches import leaflet_payload_cache_key
    from explorer.app.streamlit.app_constants import (
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
    )
    from explorer.app.streamlit.app_prep_map_leaflet_caches import (
        leaflet_payload_cache_lookup,
        leaflet_payload_cache_store,
    )
    from explorer.app.streamlit.defaults import (
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    )

    df = _tiny_df()
    payload_ck = leaflet_payload_cache_key(
        df,
        "all",
        "",
        "default",
        (),
        taxonomy_locale="en",
    )
    rev_cluster_off = json.dumps({"cluster": {"enabled": False}}, sort_keys=True)
    rev_cluster_on = json.dumps({"cluster": {"enabled": True}}, sort_keys=True)
    key_off = (payload_ck, rev_cluster_off, None)
    key_on = (payload_ck, rev_cluster_on, None)

    leaflet_payload_cache_store(
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
        key_off,
        {"revision": "off", "geojson": {"type": "FeatureCollection", "features": []}},
        max_entries=ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    )
    assert leaflet_payload_cache_lookup(
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY, key_off
    )["revision"] == "off"
    assert leaflet_payload_cache_lookup(ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY, key_on) is None


def test_all_locations_payload_cache_hit_flips_false_then_true(streamlit_stub) -> None:
    from explorer.app.streamlit.app_constants import (
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
    )
    from explorer.app.streamlit.app_prep_map_leaflet_caches import (
        leaflet_payload_cache_lookup,
        leaflet_payload_cache_store,
    )
    from explorer.app.streamlit.defaults import (
        ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
    )

    key = ("integration", "rev")
    entry = {
        "revision": "abc",
        "geojson": {"type": "FeatureCollection", "features": []},
        "banner_html": "",
        "legend_html": "",
    }
    hits: list[bool] = []

    def record_hit() -> None:
        hits.append(
            leaflet_payload_cache_lookup(ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY, key)
            is not None
        )

    record_hit()
    if not hits[-1]:
        leaflet_payload_cache_store(
            ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_KEY,
            key,
            entry,
            max_entries=ALL_LOCATIONS_LEAFLET_PAYLOAD_CACHE_MAX_ENTRIES,
        )
    record_hit()

    assert hits == [False, True]


def test_render_prep_uses_map_then_tab_spinners_and_payload_cache_warm_hit(
    streamlit_stub, monkeypatch: pytest.MonkeyPatch
) -> None:
    from explorer.app.streamlit import app_map_ui, app_prep_map_ui
    from explorer.app.streamlit.streamlit_ui_constants import (
        MAP_PREP_SPINNER_TEXT,
        TAB_PREP_SPINNER_TEXT,
    )
    st = streamlit_stub
    _seed_prep_session_defaults(st)
    payload_hits: list[bool | None] = []

    @contextmanager
    def _capturing_perf_span(stage: str, *, extra: dict[str, Any] | None = None):
        yield
        if stage == "map.all_locations_leaflet.payload" and extra is not None:
            payload_hits.append(extra.get("payload_cache_hit"))

    monkeypatch.setattr(app_prep_map_ui, "perf_span", _capturing_perf_span)
    import explorer.app.streamlit.app_prep_map_leaflet_caches as app_prep_map_leaflet_caches
    import explorer.app.streamlit.app_prep_map_tab_prep as app_prep_map_tab_prep

    monkeypatch.setattr(app_prep_map_leaflet_caches, "perf_record_point", lambda *_a, **_k: None)

    _patch_tab_prep_caches(monkeypatch, app_prep_map_tab_prep)
    monkeypatch.setattr(app_prep_map_ui, "render_all_locations_map_component", lambda **_k: None)
    monkeypatch.setattr(app_map_ui, "sidebar_bottom_slot_start", lambda: None)
    monkeypatch.setattr(app_map_ui, "sidebar_bottom_slot_end", lambda: None)
    monkeypatch.setattr(app_map_ui, "place_spinner_emoji_strip", lambda: st.empty())
    monkeypatch.setattr(app_map_ui, "inject_map_iframe_min_height_css", lambda _h: None)
    monkeypatch.setattr(app_map_ui, "inject_sidebar_outline_download_button_css", lambda _h: None)
    monkeypatch.setattr(app_map_ui, "sidebar_footer_links", lambda **_k: None)

    class _TabCtx:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

    df = _tiny_df()
    kwargs = dict(
        tab_map=_TabCtx(),
        work_df=df,
        df_full=df,
        provenance="disk",
        tax_locale_effective="en",
        map_height=400,
        map_style="default",
        map_view_mode="all",
        is_lifer_view=False,
        date_filter_banner="",
        species_pick_common=None,
        species_pick_sci="",
        family_name="",
        family_highlight_base="",
        family_colour_scheme=0,
        hide_non_matching_locations=False,
        popup_sort_order="date_desc",
        popup_scroll_hint="",
        mark_lifer=False,
        mark_last_seen=False,
        species_url_fn=lambda *_a, **_k: "",
    )

    app_prep_map_ui.render_prep_spinner_and_map_tab(**kwargs)
    app_prep_map_ui.render_prep_spinner_and_map_tab(**kwargs)

    assert MAP_PREP_SPINNER_TEXT in st.spinner_calls
    assert TAB_PREP_SPINNER_TEXT in st.spinner_calls
    assert payload_hits == [False, True]


def test_render_prep_with_explorer_perf_off_does_not_break(streamlit_stub, monkeypatch: pytest.MonkeyPatch) -> None:
    from explorer.app.streamlit import app_map_ui, app_prep_map_ui
    from explorer.app.streamlit.perf_instrumentation import explorer_perf_enabled
    monkeypatch.delenv("EXPLORER_PERF", raising=False)
    assert explorer_perf_enabled() is False

    st = streamlit_stub
    _seed_prep_session_defaults(st)
    import explorer.app.streamlit.app_prep_map_tab_prep as app_prep_map_tab_prep

    _patch_tab_prep_caches(monkeypatch, app_prep_map_tab_prep)
    monkeypatch.setattr(app_prep_map_ui, "render_all_locations_map_component", lambda **_k: None)
    monkeypatch.setattr(app_map_ui, "sidebar_bottom_slot_start", lambda: None)
    monkeypatch.setattr(app_map_ui, "sidebar_bottom_slot_end", lambda: None)
    monkeypatch.setattr(app_map_ui, "place_spinner_emoji_strip", lambda: st.empty())
    monkeypatch.setattr(app_map_ui, "inject_map_iframe_min_height_css", lambda _h: None)
    monkeypatch.setattr(app_map_ui, "inject_sidebar_outline_download_button_css", lambda _h: None)
    monkeypatch.setattr(app_map_ui, "sidebar_footer_links", lambda **_k: None)

    class _TabCtx:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

    df = _tiny_df()
    app_prep_map_ui.render_prep_spinner_and_map_tab(
        tab_map=_TabCtx(),
        work_df=df,
        df_full=df,
        provenance="disk",
        tax_locale_effective="en",
        map_height=400,
        map_style="default",
        map_view_mode="all",
        is_lifer_view=False,
        date_filter_banner="",
        species_pick_common=None,
        species_pick_sci="",
        family_name="",
        family_highlight_base="",
        family_colour_scheme=0,
        hide_non_matching_locations=False,
        popup_sort_order="date_desc",
        popup_scroll_hint="",
        mark_lifer=False,
        mark_last_seen=False,
        species_url_fn=lambda *_a, **_k: "",
    )
    from explorer.app.streamlit.streamlit_ui_constants import MAP_PREP_SPINNER_TEXT

    assert MAP_PREP_SPINNER_TEXT in st.spinner_calls


def test_social_cards_prep_uses_single_interesting_spinner(
    streamlit_stub, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Social Cards skips map prep and must not nest a second st.spinner (#328)."""
    from explorer.app.streamlit import app_map_ui, app_prep_map_ui
    from explorer.app.streamlit.streamlit_ui_constants import (
        SOCIAL_CARDS_TAB_PREP_SPINNER_TEXT,
        TAB_PREP_SPINNER_TEXT,
    )

    st = streamlit_stub
    _seed_prep_session_defaults(st)
    monkeypatch.setattr(app_prep_map_ui, "is_social_cards_main_tab", lambda: True)
    monkeypatch.setattr(
        app_prep_map_ui,
        "prepare_all_locations_map_context",
        lambda *_args, **_kwargs: pytest.fail("Social Cards must skip Leaflet map prep"),
    )

    import explorer.app.streamlit.app_prep_map_tab_prep as app_prep_map_tab_prep

    _patch_tab_prep_caches(monkeypatch, app_prep_map_tab_prep)
    monkeypatch.setattr(app_map_ui, "sidebar_bottom_slot_start", lambda: None)
    monkeypatch.setattr(app_map_ui, "sidebar_bottom_slot_end", lambda: None)
    monkeypatch.setattr(app_map_ui, "place_spinner_emoji_strip", lambda: st.empty())
    monkeypatch.setattr(app_map_ui, "sidebar_footer_links", lambda **_k: None)

    class _TabCtx:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

    df = _tiny_df()
    app_prep_map_ui.render_prep_spinner_and_map_tab(
        tab_map=_TabCtx(),
        work_df=df,
        df_full=df,
        provenance="disk",
        tax_locale_effective="en",
        map_height=400,
        map_style="default",
        map_view_mode="all",
        is_lifer_view=False,
        date_filter_banner="",
        species_pick_common=None,
        species_pick_sci="",
        family_name="",
        family_highlight_base="",
        family_colour_scheme=0,
        hide_non_matching_locations=False,
        popup_sort_order="date_desc",
        popup_scroll_hint="",
        mark_lifer=False,
        mark_last_seen=False,
        species_url_fn=lambda *_a, **_k: "",
    )

    assert st.spinner_calls == [SOCIAL_CARDS_TAB_PREP_SPINNER_TEXT]
    assert SOCIAL_CARDS_TAB_PREP_SPINNER_TEXT == "Doing interesting things with your eBird data"
    assert TAB_PREP_SPINNER_TEXT not in st.spinner_calls

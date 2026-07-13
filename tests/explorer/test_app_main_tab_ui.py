"""Tests for main dashboard tab selection helpers."""

from datetime import date
from types import SimpleNamespace

import pandas as pd

from explorer.app.streamlit import app_map_working_ui
from explorer.app.streamlit.app_constants import (
    STREAMLIT_MAIN_TAB_KEY,
    STREAMLIT_MAP_HEIGHT_PX_KEY,
    STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY,
    STREAMLIT_MAP_VIEW_LABEL_KEY,
)
from explorer.app.streamlit.app_main_tab_ui import (
    active_main_tab_label,
    is_social_cards_main_tab,
)
from explorer.app.streamlit.app_social_cards_sidebar_ui import (
    resolve_social_cards_period_from_session,
)
from explorer.app.streamlit.social_cards_session_keys import (
    APP_SOCIAL_CARDS_KEYS,
    DESIGN_SOCIAL_CARDS_KEYS,
)
from explorer.app.streamlit.streamlit_ui_constants import (
    NOTEBOOK_MAIN_TAB_LABELS,
    SOCIAL_CARDS_TAB_LABEL,
)


class _SessionState(dict):
    def __getattr__(self, name: str):
        return self[name]

    def __setattr__(self, name: str, value) -> None:
        self[name] = value


def _install_session_state(monkeypatch, state: _SessionState) -> None:
    import streamlit as st

    monkeypatch.setattr(st, "session_state", state)


def test_active_main_tab_label_defaults_to_map():
    state = _SessionState()
    import streamlit as st

    original = st.session_state
    try:
        st.session_state = state  # type: ignore[misc]
        assert active_main_tab_label() == "Map"
    finally:
        st.session_state = original  # type: ignore[misc]


def test_active_main_tab_label_reads_keyed_tab_widget():
    state = _SessionState({STREAMLIT_MAIN_TAB_KEY: SOCIAL_CARDS_TAB_LABEL})
    import streamlit as st

    original = st.session_state
    try:
        st.session_state = state  # type: ignore[misc]
        assert active_main_tab_label() == SOCIAL_CARDS_TAB_LABEL
        assert is_social_cards_main_tab() is True
    finally:
        st.session_state = original  # type: ignore[misc]


def test_social_cards_tab_is_before_maintenance_and_settings():
    labels = list(NOTEBOOK_MAIN_TAB_LABELS)
    assert labels.index(SOCIAL_CARDS_TAB_LABEL) < labels.index("Maintenance")
    assert labels[-1] == "Settings"


def test_social_cards_tab_renders_scope_sidebar_without_losing_map_working_set(monkeypatch):
    state = _SessionState(
        {
            STREAMLIT_MAIN_TAB_KEY: SOCIAL_CARDS_TAB_LABEL,
            STREAMLIT_MAP_VIEW_LABEL_KEY: "All locations",
            STREAMLIT_MAP_HEIGHT_PX_KEY: 777,
            STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY: 2,
        }
    )
    _install_session_state(monkeypatch, state)
    calls: list[str] = []
    work_df = pd.DataFrame({"Date": ["2025-01-01"], "Common Name": ["Apostlebird"]})

    monkeypatch.setattr(
        app_map_working_ui, "ensure_streamlit_map_basemap_height_keys", lambda: None
    )
    monkeypatch.setattr(
        app_map_working_ui, "ensure_streamlit_map_marker_colour_scheme_keys", lambda: None
    )
    monkeypatch.setattr(app_map_working_ui, "apply_pending_map_cluster_toggle", lambda _state: None)
    monkeypatch.setattr(app_map_working_ui, "apply_pending_map_basemap_override", lambda _state: None)
    monkeypatch.setattr(app_map_working_ui, "apply_pending_map_height_override", lambda _state: None)
    monkeypatch.setattr(app_map_working_ui, "apply_pending_map_marker_colour_scheme", lambda _state: None)
    monkeypatch.setattr(
        app_map_working_ui, "inject_spinner_theme_css", lambda: calls.append("spinner_css")
    )
    monkeypatch.setattr(
        app_map_working_ui,
        "render_social_cards_main_sidebar",
        lambda _df: calls.append("social_sidebar"),
    )
    monkeypatch.setattr(
        app_map_working_ui,
        "render_map_sidebar",
        lambda _df, *, work_df: calls.append("map_sidebar"),
    )
    monkeypatch.setattr(
        app_map_working_ui,
        "streamlit_working_set_and_status",
        lambda _df, **_kwargs: (
            SimpleNamespace(df=work_df, species_list=[], name_map={}),
            "all-time",
        ),
    )

    context = app_map_working_ui.render_map_sidebar_and_working_set(work_df)

    assert calls == ["spinner_css", "social_sidebar"]
    assert context.work_df is work_df
    assert context.map_view_mode == "all"
    assert context.map_height == 777
    assert state[STREAMLIT_MAP_VIEW_LABEL_KEY] == "All locations"


def test_map_tab_renders_map_sidebar(monkeypatch):
    state = _SessionState(
        {
            STREAMLIT_MAIN_TAB_KEY: "Map",
            STREAMLIT_MAP_VIEW_LABEL_KEY: "All locations",
            STREAMLIT_MAP_HEIGHT_PX_KEY: 640,
            STREAMLIT_MAP_MARKER_COLOUR_SCHEME_KEY: 1,
        }
    )
    _install_session_state(monkeypatch, state)
    calls: list[str] = []
    work_df = pd.DataFrame({"Date": ["2025-01-01"], "Common Name": ["Apostlebird"]})

    monkeypatch.setattr(
        app_map_working_ui, "ensure_streamlit_map_basemap_height_keys", lambda: None
    )
    monkeypatch.setattr(
        app_map_working_ui, "ensure_streamlit_map_marker_colour_scheme_keys", lambda: None
    )
    monkeypatch.setattr(app_map_working_ui, "apply_pending_map_cluster_toggle", lambda _state: None)
    monkeypatch.setattr(app_map_working_ui, "apply_pending_map_basemap_override", lambda _state: None)
    monkeypatch.setattr(app_map_working_ui, "apply_pending_map_height_override", lambda _state: None)
    monkeypatch.setattr(app_map_working_ui, "apply_pending_map_marker_colour_scheme", lambda _state: None)
    monkeypatch.setattr(
        app_map_working_ui, "inject_spinner_theme_css", lambda: calls.append("spinner_css")
    )
    monkeypatch.setattr(
        app_map_working_ui,
        "render_social_cards_main_sidebar",
        lambda _df: calls.append("social_sidebar"),
    )
    monkeypatch.setattr(
        app_map_working_ui,
        "render_map_sidebar",
        lambda _df, *, work_df: calls.append("map_sidebar"),
    )
    monkeypatch.setattr(
        app_map_working_ui,
        "streamlit_working_set_and_status",
        lambda _df, **_kwargs: (
            SimpleNamespace(df=work_df, species_list=[], name_map={}),
            "all-time",
        ),
    )

    app_map_working_ui.render_map_sidebar_and_working_set(work_df)

    assert calls == ["spinner_css", "map_sidebar"]


def test_app_social_cards_period_keys_do_not_collide_with_design_keys():
    app_period_keys = {
        APP_SOCIAL_CARDS_KEYS.period_mode,
        APP_SOCIAL_CARDS_KEYS.period_year,
        APP_SOCIAL_CARDS_KEYS.period_anchor,
        APP_SOCIAL_CARDS_KEYS.custom_start,
        APP_SOCIAL_CARDS_KEYS.custom_end,
        APP_SOCIAL_CARDS_KEYS.custom_card_heading,
    }
    design_period_keys = {
        DESIGN_SOCIAL_CARDS_KEYS.period_mode,
        DESIGN_SOCIAL_CARDS_KEYS.period_year,
        DESIGN_SOCIAL_CARDS_KEYS.period_anchor,
        DESIGN_SOCIAL_CARDS_KEYS.custom_start,
        DESIGN_SOCIAL_CARDS_KEYS.custom_end,
        DESIGN_SOCIAL_CARDS_KEYS.custom_card_heading,
    }

    assert app_period_keys.isdisjoint(design_period_keys)
    assert all(key.startswith("social_cards_") for key in app_period_keys)


def test_resolve_social_cards_period_from_app_session_custom_range(monkeypatch):
    state = _SessionState(
        {
            APP_SOCIAL_CARDS_KEYS.period_mode: "custom",
            APP_SOCIAL_CARDS_KEYS.custom_start: date(2025, 6, 7),
            APP_SOCIAL_CARDS_KEYS.custom_end: date(2025, 6, 1),
            APP_SOCIAL_CARDS_KEYS.custom_card_heading: "  North Coast trip  ",
        }
    )
    _install_session_state(monkeypatch, state)
    df = pd.DataFrame({"Date": ["2025-06-01", "2025-06-07"]})

    period = resolve_social_cards_period_from_session(df)

    assert period is not None
    assert period.kind == "custom"
    assert period.start == date(2025, 6, 1)
    assert period.end == date(2025, 6, 7)
    assert period.trip_title == "North Coast trip"


def test_resolve_social_cards_period_from_app_session_lifetime(monkeypatch):
    state = _SessionState({APP_SOCIAL_CARDS_KEYS.period_mode: "lifetime"})
    _install_session_state(monkeypatch, state)
    df = pd.DataFrame({"Date": ["2023-03-15", "not a date", "2025-07-20"]})

    period = resolve_social_cards_period_from_session(df)

    assert period is not None
    assert period.kind == "lifetime"
    assert period.start == date(2023, 3, 15)
    assert period.end == date(2025, 7, 20)

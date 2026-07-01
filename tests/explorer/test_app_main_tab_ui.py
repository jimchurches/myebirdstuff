"""Tests for main dashboard tab selection helpers."""

from explorer.app.streamlit.app_constants import STREAMLIT_MAIN_TAB_KEY
from explorer.app.streamlit.app_main_tab_ui import (
    active_main_tab_label,
    is_social_cards_main_tab,
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

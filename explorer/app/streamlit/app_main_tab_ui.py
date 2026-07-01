"""Main dashboard tab selection helpers (keyed ``st.tabs``)."""

from __future__ import annotations

import streamlit as st

from explorer.app.streamlit.app_constants import STREAMLIT_MAIN_TAB_KEY
from explorer.app.streamlit.streamlit_ui_constants import (
    NOTEBOOK_MAIN_TAB_LABELS,
    SOCIAL_CARDS_TAB_LABEL,
)


def active_main_tab_label() -> str:
    """Return the active main-tab label from the keyed tab widget, with a safe default."""
    raw = st.session_state.get(STREAMLIT_MAIN_TAB_KEY)
    if isinstance(raw, str) and raw in NOTEBOOK_MAIN_TAB_LABELS:
        return raw
    return NOTEBOOK_MAIN_TAB_LABELS[0]


def is_social_cards_main_tab() -> bool:
    """True when the Social Cards main tab is selected."""
    return active_main_tab_label() == SOCIAL_CARDS_TAB_LABEL


def notebook_main_tabs(
    *,
    on_change: str = "rerun",
) -> tuple:
    """Keyed main tab row; active label stored in ``STREAMLIT_MAIN_TAB_KEY``."""
    return st.tabs(
        list(NOTEBOOK_MAIN_TAB_LABELS),
        key=STREAMLIT_MAIN_TAB_KEY,
        on_change=on_change,
    )

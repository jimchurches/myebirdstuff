"""Sidebar map chrome, spinner CSS, and species search fragment (refs #98)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from personal_ebird_explorer.species_search import whoosh_species_suggestions
from explorer.app.streamlit.app_constants import (
    PERSIST_SPECIES_COMMON_KEY,
    SESSION_SPECIES_IX_KEY,
    SESSION_SPECIES_PICK_KEY,
    SESSION_SPECIES_SEARCH_KEY,
    SPINNER_THEME_CSS,
    SPINNER_THEME_CSS_INJECTED_KEY,
)
from explorer.app.streamlit.defaults import (
    EBIRD_PROFILE_URL,
    GITHUB_REPO_URL,
    INSTAGRAM_PROFILE_URL,
    MAP_BASEMAP_DEFAULT,
    MAP_BASEMAP_OPTIONS,
    MAP_HEIGHT_PX_DEFAULT,
    SPECIES_SEARCH_DEBOUNCE_MS,
    SPECIES_SEARCH_EDIT_AFTER_SUBMIT,
    SPECIES_SEARCH_MAX_OPTIONS,
    SPECIES_SEARCH_MIN_QUERY_LEN,
    SPECIES_SEARCH_PLACEHOLDER,
    SPECIES_SEARCH_RERUN_SCOPE,
)


def inject_spinner_theme_css() -> None:
    """Tweak hoisted checklist-stats spinner to match our theme (refs #70).

    Use :func:`streamlit.html` for **style-only** blocks: ``st.markdown(..., unsafe_allow_html)``
    sanitizes or scopes HTML so global ``<style>`` may not affect the spinner; style-only
    ``st.html`` is applied via Streamlit’s event container (see Streamlit ``HtmlMixin.html``).
    """
    if st.session_state.get(SPINNER_THEME_CSS_INJECTED_KEY):
        return
    st.html(SPINNER_THEME_CSS.strip())
    st.session_state[SPINNER_THEME_CSS_INJECTED_KEY] = True


def ensure_streamlit_map_basemap_height_keys() -> None:
    """Seed basemap + map height in session state (keyed widgets; refs #70)."""
    if "streamlit_map_basemap" not in st.session_state:
        st.session_state.streamlit_map_basemap = MAP_BASEMAP_DEFAULT
    elif st.session_state.streamlit_map_basemap not in MAP_BASEMAP_OPTIONS:
        st.session_state.streamlit_map_basemap = MAP_BASEMAP_DEFAULT
    if "streamlit_map_height_px" not in st.session_state:
        st.session_state.streamlit_map_height_px = MAP_HEIGHT_PX_DEFAULT


def sidebar_footer_links() -> None:
    """Small centred sidebar footer: GitHub, eBird, Instagram — text links only (icons dropped; narrow sidebar)."""
    st.sidebar.divider()
    link_style = "color:#868e96;text-decoration:none;"
    sep = '<span style="opacity:0.45;margin:0 0.55em;" aria-hidden="true">·</span>'
    st.sidebar.markdown(
        f'<div style="text-align:center;font-size:0.8rem;">'
        f'<a href="{GITHUB_REPO_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="{link_style}" title="View source on GitHub">GitHub</a>'
        f"{sep}"
        f'<a href="{EBIRD_PROFILE_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="{link_style}" title="eBird profile">eBird</a>'
        f"{sep}"
        f'<a href="{INSTAGRAM_PROFILE_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="{link_style}" title="Instagram">Instagram</a>'
        "</div>",
        unsafe_allow_html=True,
    )


@st.fragment
def species_searchbox_fragment() -> None:
    """Whoosh-backed search; fragment-scoped reruns avoid greying the whole app (refs #70)."""
    try:
        from streamlit_searchbox import st_searchbox
    except ImportError:
        st.error(
            "Missing **streamlit-searchbox**. Install with: "
            "`pip install -r requirements-streamlit.txt` (refs #70)."
        )
        return
    ix = st.session_state.get(SESSION_SPECIES_IX_KEY)
    if ix is None:
        return
    persisted = st.session_state.get(PERSIST_SPECIES_COMMON_KEY)

    def _search(term: str) -> list:
        return whoosh_species_suggestions(
            ix,
            term,
            max_options=SPECIES_SEARCH_MAX_OPTIONS,
            min_query_len=SPECIES_SEARCH_MIN_QUERY_LEN,
        )

    def _on_species_submit(selected: Any) -> None:
        st.session_state[SESSION_SPECIES_PICK_KEY] = selected
        st.rerun()

    def _on_species_reset() -> None:
        st.session_state.pop(SESSION_SPECIES_PICK_KEY, None)
        st.rerun()

    pick = st_searchbox(
        _search,
        key=SESSION_SPECIES_SEARCH_KEY,
        placeholder=SPECIES_SEARCH_PLACEHOLDER,
        label="Species",
        default=persisted,
        default_searchterm=persisted or "",
        debounce=SPECIES_SEARCH_DEBOUNCE_MS,
        edit_after_submit=SPECIES_SEARCH_EDIT_AFTER_SUBMIT,
        rerun_scope=SPECIES_SEARCH_RERUN_SCOPE,
        submit_function=_on_species_submit,
        reset_function=_on_species_reset,
    )
    st.session_state[SESSION_SPECIES_PICK_KEY] = pick

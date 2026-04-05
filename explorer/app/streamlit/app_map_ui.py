"""Map sidebar chrome, spinner theme/emoji helpers, and species search fragment (refs #98)."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from explorer.core.species_search import whoosh_species_suggestions
from explorer.app.streamlit.app_constants import (
    PERSIST_SPECIES_COMMON_KEY,
    SESSION_SPECIES_IX_KEY,
    SESSION_SPECIES_PICK_KEY,
    SESSION_SPECIES_SEARCH_KEY,
    SPINNER_THEME_CSS,
    SPINNER_THEME_CSS_INJECTED_KEY,
)
from explorer.app.streamlit.defaults import (
    MAP_BASEMAP_DEFAULT,
    MAP_BASEMAP_OPTIONS,
    MAP_HEIGHT_PX_DEFAULT,
    THEME_PRIMARY_HEX,
)
from explorer.app.streamlit.streamlit_ui_constants import (
    CHECKLIST_STATS_SPINNER_EMOJI_BATCH_MS,
    CHECKLIST_STATS_SPINNER_EMOJI_BATCH_SIZE,
    CHECKLIST_STATS_SPINNER_EMOJI_INDENT_REM,
    CHECKLIST_STATS_SPINNER_EMOJIS,
    EBIRD_PROFILE_URL,
    GITHUB_REPO_URL,
    INSTAGRAM_PROFILE_URL,
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


def inject_spinner_emoji_animation() -> None:
    """Animate bird emoji in batches below the checklist-stats spinner (refs #74).

    ``st.spinner`` cannot update its label mid-run; this uses a small ``components.html`` iframe and
    client-side ``setInterval`` to advance non-overlapping batches while Python is blocked.
    """
    emojis = list(CHECKLIST_STATS_SPINNER_EMOJIS)
    batch = max(1, int(CHECKLIST_STATS_SPINNER_EMOJI_BATCH_SIZE))
    ms = max(100, int(CHECKLIST_STATS_SPINNER_EMOJI_BATCH_MS))
    indent = float(CHECKLIST_STATS_SPINNER_EMOJI_INDENT_REM)
    emojis_js = json.dumps(emojis, ensure_ascii=False)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;overflow:hidden;background:transparent;font-family:system-ui,sans-serif;}}
#row{{display:flex;align-items:center;justify-content:flex-start;flex-wrap:wrap;gap:0.35em 0.5em;
box-sizing:border-box;width:100%;padding-left:{indent}rem;min-height:2.25rem;font-size:1.35rem;line-height:1.2;
letter-spacing:0.02em;color:{THEME_PRIMARY_HEX};}}
</style></head><body><div id="row" aria-hidden="true"></div>
<script>
(function() {{
  const EMOJIS = {emojis_js};
  const BATCH = {batch};
  const MS = {ms};
  const el = document.getElementById("row");
  let start = 0;
  function tick() {{
    const out = [];
    for (let i = 0; i < BATCH; i++) {{
      out.push(EMOJIS[(start + i) % EMOJIS.length]);
    }}
    el.textContent = out.join(" ");
    start = (start + BATCH) % EMOJIS.length;
  }}
  tick();
  setInterval(tick, MS);
}})();
</script></body></html>"""
    components.html(html, height=52, scrolling=False)


def place_spinner_emoji_strip() -> Any:
    """Show the animated bird-emoji strip under the current ``st.spinner`` (refs #74).

    Uses ``st.empty()`` + ``container()`` + :func:`inject_spinner_emoji_animation`. Returns the
    placeholder; call ``.empty()`` on it when the spinner phase ends so the iframe is dropped.
    """
    placeholder = st.empty()
    with placeholder.container():
        inject_spinner_emoji_animation()
    return placeholder


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
            "`pip install -r requirements.txt` (refs #70)."
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

"""Map sidebar chrome, spinner theme/emoji helpers, and species search fragment (refs #98)."""

from __future__ import annotations

import html as html_module
import json
import os
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from explorer.core.species_search import whoosh_species_suggestions
from explorer.app.streamlit.app_constants import (
    EXPLORER_MAP_HTML_BYTES_KEY,
    FOLIUM_MAP_MOUNT_NONCE_KEY,
    FOLIUM_STATIC_MAP_CACHE_KEY,
    STREAMLIT_MAP_BASEMAP_KEY,
    STREAMLIT_MAP_BASEMAP_SAVED_KEY,
    STREAMLIT_MAP_HEIGHT_PX_KEY,
    STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY,
    PERSIST_SPECIES_COMMON_KEY,
    PERSIST_SPECIES_SCI_KEY,
    SESSION_SPECIES_IX_KEY,
    SESSION_SPECIES_PICK_KEY,
    SESSION_SPECIES_SEARCH_KEY,
    SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY,
    SESSION_SPECIES_WS_KEY,
    SPINNER_THEME_CSS,
)
from explorer.app.streamlit.defaults import (
    MAP_BASEMAP_DEFAULT,
    MAP_BASEMAP_OPTIONS,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_DEFAULT,
    THEME_PRIMARY_HEX,
)
from explorer.app.streamlit.streamlit_ui_constants import (
    BUY_ME_A_COFFEE_URL,
    CHECKLIST_STATS_SPINNER_EMOJI_BATCH_MS,
    CHECKLIST_STATS_SPINNER_EMOJI_BATCH_SIZE,
    CHECKLIST_STATS_SPINNER_EMOJIS,
    EBIRD_PROFILE_URL,
    GITHUB_REPO_URL,
    explorer_readme_github_url,
    INSTAGRAM_PROFILE_URL,
    SIDEBAR_FOOTER_LINK_HEX,
    SPECIES_SEARCH_DEBOUNCE_MS,
    SPECIES_SEARCH_EDIT_AFTER_SUBMIT,
    SPECIES_SEARCH_MAX_OPTIONS,
    SPECIES_SEARCH_MIN_QUERY_LEN,
    SPECIES_SEARCH_PLACEHOLDER,
    SPECIES_SEARCH_RERUN_SCOPE,
)


def _species_searchbox_widget_key() -> str:
    """Stable Streamlit widget id; nonce bumps on reset so the field remounts empty (refs #73)."""
    n = int(st.session_state.get(SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY, 0))
    return f"{SESSION_SPECIES_SEARCH_KEY}__v{n}"


def inject_map_folium_iframe_min_height_css(height_px: int) -> None:
    """Reduce streamlit-folium letterboxing when the iframe gets a near-zero height on some reruns.

    Targets iframes in the **main** column only (not the sidebar). Emit from the Map tab each full run
    so height tracks the sidebar **Map height (px)** slider.
    """
    h = max(240, int(height_px))
    st.html(
        f"""<style>
section[data-testid="stMain"] iframe {{
  min-height: {h}px !important;
}}
</style>"""
    )


def inject_spinner_theme_css() -> None:
    """Tweak ``st.spinner`` (text-style, theme greens, emoji iframe layout) to match our theme (refs #70, #124).

    Use :func:`streamlit.html` for **style-only** blocks: ``st.markdown(..., unsafe_allow_html)``
    sanitizes or scopes HTML so global ``<style>`` may not affect the spinner; style-only
    ``st.html`` is applied via Streamlit’s event container (see Streamlit ``HtmlMixin.html``).

    **Must run on every rerun:** if injection is skipped after the first run, the ``<style>`` node is
    omitted from Streamlit output and spinners revert to default styling.
    """
    st.html(SPINNER_THEME_CSS.strip())


def inject_spinner_emoji_animation() -> None:
    """Animate bird emoji in batches under the checklist-stats spinner text (refs #74).

    ``st.spinner`` cannot update its label mid-run; this uses a small ``components.html`` iframe and
    client-side ``setInterval`` to advance non-overlapping batches while Python is blocked.
    Theme CSS centers this iframe under the spinner row in normal document flow (refs #124).
    """
    emojis = list(CHECKLIST_STATS_SPINNER_EMOJIS)
    batch = max(1, int(CHECKLIST_STATS_SPINNER_EMOJI_BATCH_SIZE))
    ms = max(100, int(CHECKLIST_STATS_SPINNER_EMOJI_BATCH_MS))
    emojis_js = json.dumps(emojis, ensure_ascii=False)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;overflow:hidden;background:transparent;font-family:system-ui,sans-serif;}}
#row{{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:0.35em 0.5em;
box-sizing:border-box;width:100%;padding:0 0.35rem;min-height:2.25rem;font-size:1.35rem;line-height:1.2;
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
    """Show the animated bird-emoji strip for the current ``st.spinner`` (refs #74, #124).

    Uses ``st.empty()`` + ``container()`` + :func:`inject_spinner_emoji_animation`. Returns the
    placeholder; call ``.empty()`` on it when the spinner phase ends so the iframe is dropped.
    """
    placeholder = st.empty()
    with placeholder.container():
        inject_spinner_emoji_animation()
    return placeholder


def sidebar_bottom_slot_start() -> None:
    """Open the bottom sidebar region (spinner + emoji, export, footer).

    Wrapper is ``position: sticky`` with a transparent background so it does not look like a separate
    empty panel when idle (refs #124).
    """
    st.markdown(
        '<div class="ebird-sidebar-bottom-slot" aria-live="polite">',
        unsafe_allow_html=True,
    )


def sidebar_bottom_slot_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def inject_sidebar_outline_download_button_css(outline_hex: str) -> None:
    """Style the map **Export HTML** ``st.download_button`` like the outline support link (refs #127).

    Streamlit widgets are not plain ``<a>`` tags; we align them visually with scoped CSS on
    ``.ebird-sidebar-bottom-slot`` (see :func:`sidebar_bottom_slot_start`).
    Uses the same colour as the footer text links (see :data:`SIDEBAR_FOOTER_LINK_HEX`).
    """
    h = outline_hex.strip()
    if not h.startswith("#") or len(h) not in (4, 7, 9):
        h = SIDEBAR_FOOTER_LINK_HEX
    st.html(
        f"""<style>
.ebird-sidebar-bottom-slot [data-testid="stDownloadButton"] button {{
  background: transparent !important;
  color: {h} !important;
  border: 1px solid {h} !important;
  border-radius: 6px !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}}
.ebird-sidebar-bottom-slot [data-testid="stDownloadButton"] button:hover {{
  background: color-mix(in srgb, {h} 14%, transparent) !important;
}}
@supports not (color: color-mix(in srgb, black 50%, transparent)) {{
  .ebird-sidebar-bottom-slot [data-testid="stDownloadButton"] button:hover {{
    background: rgba(134, 142, 150, 0.12) !important;
  }}
}}
</style>"""
    )


def _support_project_url() -> str | None:
    """Buy Me a Coffee (or other) URL.

    If env ``STREAMLIT_BUYMEACOFFEE_URL`` is **set** (including to empty), it wins: use the trimmed
    value, or hide the block when empty. If unset, use :data:`~explorer.app.streamlit.streamlit_ui_constants.BUY_ME_A_COFFEE_URL`.
    """
    raw = os.environ.get("STREAMLIT_BUYMEACOFFEE_URL")
    if raw is not None:
        u = raw.strip()
        return u or None
    u2 = (BUY_ME_A_COFFEE_URL or "").strip()
    return u2 or None


def _support_buy_me_a_coffee_outline_html(url: str, *, outline_hex: str) -> str:
    """Outline pill using the same colour as the footer text links (:data:`SIDEBAR_FOOTER_LINK_HEX`)."""
    esc = html_module.escape(url, quote=True)
    return (
        '<div style="text-align:center;margin-top:0.45rem;">'
        f'<a href="{esc}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-block;padding:0.26rem 0.6rem;background:transparent;'
        f'color:{outline_hex};border:1px solid {outline_hex};border-radius:6px;'
        f'font-size:0.78rem;text-decoration:none;font-weight:500;" '
        'title="Optional — helps with hosting">Buy me a coffee</a></div>'
    )


def ensure_streamlit_map_basemap_height_keys() -> None:
    """Seed basemap + map height in session state (keyed widgets; refs #70)."""
    if STREAMLIT_MAP_BASEMAP_SAVED_KEY not in st.session_state:
        st.session_state[STREAMLIT_MAP_BASEMAP_SAVED_KEY] = MAP_BASEMAP_DEFAULT
    elif st.session_state.get(STREAMLIT_MAP_BASEMAP_SAVED_KEY) not in MAP_BASEMAP_OPTIONS:
        st.session_state[STREAMLIT_MAP_BASEMAP_SAVED_KEY] = MAP_BASEMAP_DEFAULT

    # Sidebar override (session-only): sentinel means "use default from Settings".
    if STREAMLIT_MAP_BASEMAP_KEY not in st.session_state:
        st.session_state[STREAMLIT_MAP_BASEMAP_KEY] = "__default__"
    elif (
        st.session_state.get(STREAMLIT_MAP_BASEMAP_KEY) not in MAP_BASEMAP_OPTIONS
        and st.session_state.get(STREAMLIT_MAP_BASEMAP_KEY) != "__default__"
    ):
        st.session_state[STREAMLIT_MAP_BASEMAP_KEY] = "__default__"
    if STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY not in st.session_state:
        st.session_state[STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY] = MAP_HEIGHT_PX_DEFAULT
    else:
        st.session_state[STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY] = max(
            MAP_HEIGHT_PX_MIN,
            min(MAP_HEIGHT_PX_MAX, int(st.session_state[STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY])),
        )
    if STREAMLIT_MAP_HEIGHT_PX_KEY not in st.session_state:
        st.session_state[STREAMLIT_MAP_HEIGHT_PX_KEY] = int(
            st.session_state[STREAMLIT_MAP_HEIGHT_PX_SAVED_KEY]
        )


def sidebar_footer_links(*, leading_divider: bool = True) -> None:
    """Small centred sidebar footer: GitHub, eBird, Instagram + Explorer README + optional support (refs #127)."""
    if leading_divider:
        st.sidebar.divider()
    link_style = f"color:{SIDEBAR_FOOTER_LINK_HEX};text-decoration:none;"
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
        "</div>"
        f'<div style="text-align:center;font-size:0.8rem;margin-top:0.4em;">'
        f'<a href="{explorer_readme_github_url()}" target="_blank" rel="noopener noreferrer" '
        f'style="{link_style}" title="Personal eBird Explorer — documentation (README on GitHub)">'
        f"Explorer docs</a>"
        "</div>",
        unsafe_allow_html=True,
    )
    support_url = _support_project_url()
    if support_url:
        st.sidebar.markdown(
            _support_buy_me_a_coffee_outline_html(support_url, outline_hex=SIDEBAR_FOOTER_LINK_HEX),
            unsafe_allow_html=True,
        )


@st.fragment
def species_searchbox_fragment() -> None:
    """Whoosh-backed species search with weighted common/scientific/group matching (refs #73)."""
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
    search_default = persisted
    # Always use an empty initial search term for the widget props. Passing the persisted species
    # here on every fragment rerun re-injected that string into the control and fought backspace /
    # edits (focus jumped; map state flickered). Selection stays in session via ``default`` and
    # ``SESSION_SPECIES_PICK_KEY``; only the reset (×) clears those (refs #73).

    def _search(term: str) -> list:
        return whoosh_species_suggestions(
            ix,
            term,
            max_options=SPECIES_SEARCH_MAX_OPTIONS,
            min_query_len=SPECIES_SEARCH_MIN_QUERY_LEN,
        )

    def _on_species_submit(selected: Any) -> None:
        # Submit can fire while editing; only commit a real species and rerun when it changes (refs #73).
        ws = st.session_state.get(SESSION_SPECIES_WS_KEY)
        valid_common = frozenset(ws.species_list) if ws is not None else frozenset()
        raw = selected if isinstance(selected, str) else str(selected)
        s = raw.strip()
        if s not in valid_common:
            return
        prev = st.session_state.get(SESSION_SPECIES_PICK_KEY)
        st.session_state[SESSION_SPECIES_PICK_KEY] = s
        if prev != s:
            st.rerun()

    def _on_species_reset() -> None:
        st.session_state.pop(SESSION_SPECIES_PICK_KEY, None)
        st.session_state.pop(PERSIST_SPECIES_COMMON_KEY, None)
        st.session_state.pop(PERSIST_SPECIES_SCI_KEY, None)
        st.session_state[SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY] = int(
            st.session_state.get(SESSION_SPECIES_SEARCH_REMOUNT_NONCE_KEY, 0)
        ) + 1
        # Remount Folium + drop cached HTML so the map returns to the all-locations view cleanly.
        st.session_state[FOLIUM_MAP_MOUNT_NONCE_KEY] = int(
            st.session_state.get(FOLIUM_MAP_MOUNT_NONCE_KEY, 0)
        ) + 1
        st.session_state.pop(FOLIUM_STATIC_MAP_CACHE_KEY, None)
        st.session_state.pop(EXPLORER_MAP_HTML_BYTES_KEY, None)
        st.rerun()

    pick = st_searchbox(
        _search,
        key=_species_searchbox_widget_key(),
        placeholder=SPECIES_SEARCH_PLACEHOLDER,
        label="Species",
        default=search_default,
        default_searchterm="",
        debounce=SPECIES_SEARCH_DEBOUNCE_MS,
        edit_after_submit=SPECIES_SEARCH_EDIT_AFTER_SUBMIT,
        rerun_scope=SPECIES_SEARCH_RERUN_SCOPE,
        submit_function=_on_species_submit,
        reset_function=_on_species_reset,
    )
    ws = st.session_state.get(SESSION_SPECIES_WS_KEY)
    valid_common = frozenset(ws.species_list) if ws is not None else frozenset()

    if pick is not None:
        raw = pick if isinstance(pick, str) else str(pick)
        p = raw.strip()
        # Empty field while typing / backspacing must not clear the map species — only choosing a
        # valid species updates PICK; reset (×) clears via ``_on_species_reset`` (refs #73).
        if p in valid_common:
            st.session_state[SESSION_SPECIES_PICK_KEY] = p
        # Partial / invalid typing: do not assign PICK (avoids empty filter → blank map) (refs #73).

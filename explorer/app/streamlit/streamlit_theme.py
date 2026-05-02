"""
Single source for checklist-style Streamlit HTML tab surface theme (green vs eBird blue) (refs #95).

Tab modules use :func:`inject_streamlit_checklist_css` (refs #96) for table + tab-surface injection, or
compose ``CHECKLIST_STATS_TABLE_CSS`` + :data:`CHECKLIST_STATS_HTML_TAB_SURFACE_CSS` plus any tab-specific
rules. Changing only the surface CSS here rethemes every tab; local extra CSS blocks remain additive overlays.

Primary ``st.tabs`` in the main column (Map, Checklist Statistics, …) are styled via
:data:`MAIN_TAB_STRIP_NAV_CSS` (refs #149): muted inactive grey-green, primary green when selected,
``0.9375rem`` labels, weight 500/400. Tab **labels** render inside ``stMarkdownContainer``; **size** and
**colour** need rules on that node with ``!important``. The moving **tab underline** uses Base Web’s
``tab-highlight`` node; :func:`inject_streamlit_chrome_theme_tokens_css` sets ``--st-primary-color`` and
that highlight so sidebar toggles/sliders and main tabs stay green when ``.streamlit/config.toml`` is not
loaded (Streamlit’s fallback primary is red). Nested tabs inside a panel use the same rules.

The app title + tagline (``pebird-app-header`` in :mod:`~explorer.app.streamlit.app_landing_ui`) use
:data:`MAIN_APP_HEADER_CSS`: dark green title and muted tagline aligned with the tab palette (#149).
"""

from __future__ import annotations

import streamlit as st

from explorer.app.streamlit.defaults import THEME_PRIMARY_HEX
from explorer.presentation.checklist_stats_display import (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS,
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE,
    CHECKLIST_STATS_TABLE_CSS,
)

# Flip this one flag to theme all checklist-style HTML tabs at once.
USE_EBIRD_BLUE_HTML_TAB_THEME = False

CHECKLIST_STATS_HTML_TAB_SURFACE_CSS = (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    if USE_EBIRD_BLUE_HTML_TAB_THEME
    else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
)

# Main notebook tabs: Streamlit applies generous top padding inside each tab panel. A modest reduction
# brings Country / data tabs closer to the tab strip (#132). Scoped to main column only; if Streamlit
# changes tab DOM in a major release, revisit selectors.
MAIN_TAB_PANEL_TOP_COMPACT_CSS = """
section[data-testid="stMain"] [data-baseweb="tab-panel"],
section[data-testid="stMain"] div[role="tabpanel"] {
  padding-top: 0.45rem !important;
}
"""

# Main tab strip: “calm” palette — softer inactive grey-green; primary on selected (refs #149).
_MAIN_TAB_INACTIVE_MUTED_HEX = "#6b7f77"
_MAIN_TAB_HOVER_HEX = "#156248"
_MAIN_TAB_LABEL_REM = "0.9375rem"
# Match Streamlit app chrome + checklist HTML (``app_constants`` / ``map_renderer.EXPLORER_UI_FONT_STACK``).
_MAIN_TAB_LABEL_FONT_STACK = (
    '"Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
)

MAIN_TAB_STRIP_NAV_CSS = f"""
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"] {{
  color: {_MAIN_TAB_INACTIVE_MUTED_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
  color: {THEME_PRIMARY_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"]:hover,
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"]:hover {{
  color: {_MAIN_TAB_HOVER_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"]:hover,
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"]:hover {{
  color: {THEME_PRIMARY_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"] [data-testid="stMarkdownContainer"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"] [data-testid="stMarkdownContainer"] {{
  font-family: {_MAIN_TAB_LABEL_FONT_STACK} !important;
  font-size: {_MAIN_TAB_LABEL_REM} !important;
  font-weight: 400 !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"]:not([aria-selected="true"]) [data-testid="stMarkdownContainer"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"]:not([aria-selected="true"]) [data-testid="stMarkdownContainer"] {{
  color: {_MAIN_TAB_INACTIVE_MUTED_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] [data-testid="stMarkdownContainer"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"] [data-testid="stMarkdownContainer"] {{
  color: {THEME_PRIMARY_HEX} !important;
  font-weight: 500 !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"]:not([aria-selected="true"]):hover [data-testid="stMarkdownContainer"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"]:not([aria-selected="true"]):hover [data-testid="stMarkdownContainer"] {{
  color: {_MAIN_TAB_HOVER_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-testid="stMarkdownContainer"] p {{
  color: inherit !important;
}}
"""

# App shell heading (``title_with_logo``): same green family as tabs — strong structure, not near-black.
_MAIN_APP_HEADER_TITLE_HEX = "#1f3d2b"
# Align tagline with tab inactive muted so title → subtitle → tabs read as one system.
_MAIN_APP_HEADER_TAGLINE_HEX = _MAIN_TAB_INACTIVE_MUTED_HEX

# One-shot session key so reruns do not stack duplicate ``<style>`` nodes.
_STREAMLIT_CHROME_THEME_TOKENS_SESSION_KEY = "_explorer_streamlit_chrome_theme_tokens_v1"

STREAMLIT_CHROME_THEME_TOKENS_CSS = f"""
/* When ``streamlit run`` cwd omits ``.streamlit/config.toml``, Streamlit uses a red default primary.
   Re-assert CSS variables so toggles, sliders, links, and tab chrome match ``THEME_PRIMARY_HEX``. */
.stApp,
[data-testid="stAppViewContainer"],
section[data-testid="stSidebar"],
section[data-testid="stMain"] {{
  --st-primary-color: {THEME_PRIMARY_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
  background-color: {THEME_PRIMARY_HEX} !important;
}}
"""

MAIN_APP_HEADER_CSS = f"""
section[data-testid="stMain"] .pebird-app-header {{
  /* Tuck primary tab strip closer to tagline; logo row unchanged (flex, no vertical shift of image). */
  padding-bottom: 0.2rem !important;
  margin-bottom: -0.45rem !important;
}}
section[data-testid="stMain"] .pebird-app-header h1 {{
  color: {_MAIN_APP_HEADER_TITLE_HEX} !important;
  font-weight: 600 !important;
}}
section[data-testid="stMain"] .pebird-app-header p {{
  color: {_MAIN_APP_HEADER_TAGLINE_HEX} !important;
}}
"""


def inject_streamlit_chrome_theme_tokens_css() -> None:
    """Set ``--st-primary-color`` and tab highlight so chrome matches theme when config.toml is missing."""
    if st.session_state.get(_STREAMLIT_CHROME_THEME_TOKENS_SESSION_KEY):
        return
    st.session_state[_STREAMLIT_CHROME_THEME_TOKENS_SESSION_KEY] = True
    st.html(f"<style>{STREAMLIT_CHROME_THEME_TOKENS_CSS}</style>")


def inject_main_tab_panel_top_compact_css() -> None:
    """Tighten tab panel inset and main tab strip (refs #132, #149).

    App title/tagline colours are injected from :func:`~explorer.app.streamlit.app_landing_ui.title_with_logo`
    via :func:`inject_app_header_css` so the landing page (no tabs) still gets the same header treatment.
    """
    st.html(f"<style>{MAIN_TAB_PANEL_TOP_COMPACT_CSS}{MAIN_TAB_STRIP_NAV_CSS}</style>")


def inject_app_header_css() -> None:
    """Apply ``MAIN_APP_HEADER_CSS`` (call from ``title_with_logo`` after the header HTML)."""
    st.html(f"<style>{MAIN_APP_HEADER_CSS}</style>")


def inject_streamlit_checklist_css(extra_css: str = "") -> None:
    """Inject scoped checklist table + Streamlit tab-surface CSS via ``st.html`` (refs #96, #132).

    Style-only blocks use ``st.html`` (not ``st.markdown``) so Streamlit does not reserve a tall
    markdown block above tab content — reduces the gap under the main tab strip on Country / Yearly / etc.

    Uses :data:`CHECKLIST_STATS_HTML_TAB_SURFACE_CSS` (see ``USE_EBIRD_BLUE_HTML_TAB_THEME``). Append
    *extra_css* for tab-specific rules (e.g. Country link row, Rankings max-width).
    """
    st.html(
        "<style>"
        f"{CHECKLIST_STATS_TABLE_CSS}"
        f"{CHECKLIST_STATS_HTML_TAB_SURFACE_CSS}"
        f"{extra_css}"
        "</style>"
    )

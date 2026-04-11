"""
Single source for checklist-style Streamlit HTML tab surface theme (green vs eBird blue) (refs #95).

Tab modules use :func:`inject_streamlit_checklist_css` (refs #96) for table + tab-surface injection, or
compose ``CHECKLIST_STATS_TABLE_CSS`` + :data:`CHECKLIST_STATS_HTML_TAB_SURFACE_CSS` plus any tab-specific
rules. Changing only the surface CSS here rethemes every tab; local extra CSS blocks remain additive overlays.

Primary ``st.tabs`` in the main column (Map, Checklist Statistics, …) are styled via
:data:`MAIN_TAB_STRIP_NAV_CSS` (refs #149). Tab **labels** render inside ``stMarkdownContainer``; **size**
needs rules on that node (theme ``fontSize`` on the label). **Colour** is also set there with
``!important`` so nested markdown does not keep Streamlit ``bodyText`` instead of the tab strip palette.
Nested tabs inside a panel use the same rules for consistency.
"""

from __future__ import annotations

import streamlit as st

from explorer.app.streamlit.defaults import THEME_PRIMARY_HEX, THEME_TEXT_HEX
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

# Main tab strip: inactive uses theme body text (``config.toml`` / :data:`THEME_TEXT_HEX`); hover stays green.
_MAIN_TAB_HOVER_HEX = "#156248"
# Match Streamlit app chrome + checklist HTML (``app_constants`` / ``map_renderer.EXPLORER_UI_FONT_STACK``).
_MAIN_TAB_LABEL_FONT_STACK = (
    '"Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
)

MAIN_TAB_STRIP_NAV_CSS = f"""
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"] {{
  color: {THEME_TEXT_HEX} !important;
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
  font-size: 1rem !important;
  font-weight: 400 !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"]:not([aria-selected="true"]) [data-testid="stMarkdownContainer"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"]:not([aria-selected="true"]) [data-testid="stMarkdownContainer"] {{
  color: {THEME_TEXT_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] [data-testid="stMarkdownContainer"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"][aria-selected="true"] [data-testid="stMarkdownContainer"] {{
  color: {THEME_PRIMARY_HEX} !important;
  font-weight: 600 !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"]:not([aria-selected="true"]):hover [data-testid="stMarkdownContainer"],
section[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"]:not([aria-selected="true"]):hover [data-testid="stMarkdownContainer"] {{
  color: {_MAIN_TAB_HOVER_HEX} !important;
}}
section[data-testid="stMain"] [data-testid="stTabs"] [data-testid="stMarkdownContainer"] p {{
  color: inherit !important;
}}
"""


def inject_main_tab_panel_top_compact_css() -> None:
    """Tighten tab panel inset and improve main tab strip visibility (refs #132, #149)."""
    st.html(f"<style>{MAIN_TAB_PANEL_TOP_COMPACT_CSS}{MAIN_TAB_STRIP_NAV_CSS}</style>")


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

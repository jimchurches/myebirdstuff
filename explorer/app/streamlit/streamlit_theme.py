"""
Single source for checklist-style Streamlit HTML tab surface theme (green vs eBird blue) (refs #95).

Tab modules use :func:`inject_streamlit_checklist_css` (refs #96) for table + tab-surface injection, or
compose ``CHECKLIST_STATS_TABLE_CSS`` + :data:`CHECKLIST_STATS_HTML_TAB_SURFACE_CSS` plus any tab-specific
rules. Changing only the surface CSS here rethemes every tab; local extra CSS blocks remain additive overlays.
"""

from __future__ import annotations

import streamlit as st

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


def inject_main_tab_panel_top_compact_css() -> None:
    """Tighten default top inset for primary ``st.tabs`` panels in the main column (refs #132)."""
    st.html(f"<style>{MAIN_TAB_PANEL_TOP_COMPACT_CSS}</style>")


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

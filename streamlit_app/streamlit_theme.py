"""
Single source for checklist-style Streamlit HTML tab surface theme (green vs eBird blue) (refs #95).

Tab modules compose ``CHECKLIST_STATS_TABLE_CSS`` + :data:`CHECKLIST_STATS_HTML_TAB_SURFACE_CSS` plus any
tab-specific rules (Country link bar, Rankings width, etc.). Changing only the surface CSS here rethemes
every tab; local extra CSS blocks remain additive overlays.
"""

from __future__ import annotations

from personal_ebird_explorer.checklist_stats_display import (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS,
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE,
)

# Flip this one flag to theme all checklist-style HTML tabs at once.
USE_EBIRD_BLUE_HTML_TAB_THEME = False

CHECKLIST_STATS_HTML_TAB_SURFACE_CSS = (
    CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS_BLUE
    if USE_EBIRD_BLUE_HTML_TAB_THEME
    else CHECKLIST_STATS_STREAMLIT_HTML_TAB_CSS
)

"""
Shared literals for the Streamlit app: repo path, session-state key strings, and injected CSS (refs #98).

``app.py`` adds the repo root to ``sys.path`` before importing the explorer package; this module only
computes ``REPO_ROOT`` for disk resolution and settings paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from personal_ebird_explorer.checklist_stats_display import (
    COUNTRY_TAB_SORT_ALPHABETICAL,
    COUNTRY_TAB_SORT_LIFERS_WORLD,
    COUNTRY_TAB_SORT_TOTAL_SPECIES,
)
from streamlit_app.defaults import (
    DEFAULT_EBIRD_DATA_FILENAME,
    MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT,
    SETTINGS_PANEL_MAX_WIDTH_REM,
    SPINNER_THEME_CSS_CACHE_KEY_SUFFIX,
    TAXONOMY_LOCALE_DEFAULT,
    THEME_PRIMARY_HEX,
    THEME_SECONDARY_BG_HEX,
    THEME_TEXT_HEX,
)

STREAMLIT_APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = str(STREAMLIT_APP_DIR.parent)

DEFAULT_EBIRD_FILENAME = os.environ.get("STREAMLIT_EBIRD_DATA_FILE", DEFAULT_EBIRD_DATA_FILENAME)

MAP_VIEW_LABEL_TO_MODE = {
    "All locations": "all",
    "Selected species": "species",
    "Lifer locations": "lifers",
}

SETTINGS_PANEL_CSS = f"""
<style>
/* Cap slider/track width on wide screens; stays full width when the block is narrow (refs #70). */
div[data-testid="stVerticalBlockBorderWrapper"].st-key-ebird_settings_panel,
div.st-key-ebird_settings_panel {{
    max-width: min(100%, {SETTINGS_PANEL_MAX_WIDTH_REM}rem);
}}
/* Save / Reset feedback: full width, theme greens (not default Streamlit info blue). */
.ebird-settings-persistence-banner {{
    width: 100%;
    box-sizing: border-box;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0 0.75rem 0;
    border-radius: 0.35rem;
    border-left: 4px solid {THEME_PRIMARY_HEX};
    background: {THEME_SECONDARY_BG_HEX};
    color: {THEME_TEXT_HEX};
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.875rem;
    line-height: 1.5;
}}
.ebird-settings-persistence-banner strong {{
    font-weight: 600;
}}
/* Settings → Data & path (read-only troubleshooting block). */
.ebird-data-path-block {{
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.875rem;
    line-height: 1.45;
    color: {THEME_TEXT_HEX};
    margin: 0.35rem 0 0.5rem 0;
}}
.ebird-data-path-block p {{
    margin: 0.4rem 0;
}}
.ebird-data-path-block strong {{
    color: {THEME_PRIMARY_HEX};
    font-weight: 600;
}}
.ebird-data-path-block code {{
    font-size: 0.8125rem;
    font-weight: 400;
    word-break: break-all;
    background: {THEME_SECONDARY_BG_HEX};
    padding: 0.12em 0.4em;
    border-radius: 0.2rem;
    color: {THEME_TEXT_HEX};
}}
/* Settings → Taxonomy (body copy; matches Data & path typography). */
.ebird-settings-section-copy {{
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.875rem;
    line-height: 1.5;
    color: {THEME_TEXT_HEX};
    margin: 0.35rem 0 0.75rem 0;
}}
.ebird-settings-section-copy a {{
    color: {THEME_PRIMARY_HEX};
    text-decoration: underline;
    text-underline-offset: 2px;
}}
.ebird-settings-section-copy code {{
    font-size: 0.8125rem;
    font-weight: 400;
    background: {THEME_SECONDARY_BG_HEX};
    padding: 0.12em 0.35em;
    border-radius: 0.2rem;
    color: {THEME_TEXT_HEX};
}}
</style>
"""

DEFAULT_CLOSE_LOCATION_METERS = MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT
DEFAULT_TAXONOMY_LOCALE = TAXONOMY_LOCALE_DEFAULT

SESSION_UPLOAD_CACHE_KEY = "_ebird_streamlit_upload_csv_cache"
PERSIST_MAP_DATE_FILTER_KEY = "_preserve_map_date_filter"
PERSIST_MAP_DATE_RANGE_KEY = "_preserve_map_date_range"
PERSIST_SPECIES_COMMON_KEY = "_preserve_streamlit_species_common"
PERSIST_SPECIES_SCI_KEY = "_preserve_streamlit_species_sci"
SESSION_PREV_MAP_VIEW_KEY = "_streamlit_prev_map_view_mode"
SESSION_SPECIES_SEARCH_KEY = "streamlit_species_searchbox"
SESSION_SPECIES_WS_KEY = "_ws_for_species_search_fragment"
SESSION_SPECIES_IX_KEY = "_streamlit_species_whoosh_ix"
SESSION_SPECIES_IX_SIG_KEY = "_streamlit_species_whoosh_ix_sig"
SESSION_SPECIES_PICK_KEY = "_streamlit_species_pick_common"
FOLIUM_STATIC_MAP_CACHE_KEY = "_folium_static_all_lifer_cache"
SETTINGS_CONFIG_PATH_KEY = "_streamlit_settings_yaml_path"
SETTINGS_CONFIG_SOURCE_KEY = "_streamlit_settings_source_label"
SETTINGS_LOADED_FROM_KEY = "_streamlit_settings_loaded_from_path"
SETTINGS_BASELINE_KEY = "_streamlit_settings_saved_baseline"
SETTINGS_WARNED_KEY = "_streamlit_settings_warned"
SETTINGS_FLASH_SAVE_KEY = "_streamlit_settings_flash_save"
SETTINGS_FLASH_RESET_KEY = "_streamlit_settings_flash_reset"

COUNTRY_SORT_LABELS = {
    COUNTRY_TAB_SORT_ALPHABETICAL: "Alphabetical",
    COUNTRY_TAB_SORT_LIFERS_WORLD: "By lifers (world)",
    COUNTRY_TAB_SORT_TOTAL_SPECIES: "By total species",
}

SETTINGS_SESSION_KEYS = (
    "streamlit_popup_sort_order",
    "streamlit_popup_scroll_hint",
    "streamlit_mark_lifer",
    "streamlit_mark_last_seen",
    "streamlit_default_color",
    "streamlit_default_fill",
    "streamlit_species_color",
    "streamlit_species_fill",
    "streamlit_lifer_color",
    "streamlit_lifer_fill",
    "streamlit_last_seen_color",
    "streamlit_last_seen_fill",
    "streamlit_taxonomy_locale",
    "streamlit_rankings_top_n",
    "streamlit_rankings_visible_rows",
    "streamlit_yearly_recent_column_count",
    "streamlit_country_tab_sort",
    "streamlit_close_location_meters",
)

SPINNER_THEME_CSS_INJECTED_KEY = f"_ebird_spinner_theme_css_injected_{SPINNER_THEME_CSS_CACHE_KEY_SUFFIX}"

SPINNER_THEME_CSS = f"""
<style>
/* Hoisted ``st.spinner`` — align with [theme] in .streamlit/config.toml */
/* Modern Streamlit uses an icon spinner (``iconValue: spinner``), not a CSS border ring. */
div[data-testid="stSpinner"],
div[data-testid="stSpinner"].stSpinner {{
  color: {THEME_TEXT_HEX};
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
/* Graphic: ``currentColor`` on the SVG so the arc tracks primary (not default grey). */
div[data-testid="stSpinner"] svg {{
  color: {THEME_PRIMARY_HEX} !important;
}}
div[data-testid="stSpinner"] svg path,
div[data-testid="stSpinner"] svg circle {{
  fill: currentColor !important;
  stroke: currentColor !important;
}}
/* Spinner message is rendered as Streamlit markdown — target container + descendants. */
div[data-testid="stSpinner"] [data-testid="stMarkdownContainer"],
div[data-testid="stSpinner"] [data-testid="stMarkdownContainer"] * {{
  color: {THEME_TEXT_HEX} !important;
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}}
div[data-testid="stSpinner"] p,
div[data-testid="stSpinner"] span,
div[data-testid="stSpinner"] label {{
  color: {THEME_TEXT_HEX} !important;
}}
/* Older border-based spinner (harmless if unused) */
div[data-testid="stSpinner"] div[class*="Spinner"] {{
  border-color: {THEME_SECONDARY_BG_HEX} !important;
  border-top-color: {THEME_PRIMARY_HEX} !important;
}}
</style>
"""

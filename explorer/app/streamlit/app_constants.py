"""
Shared literals for the Streamlit app: repo path, session-state key strings, and injected CSS (refs #98).

``REPO_ROOT`` is resolved from this package path (`explorer/app/streamlit`) for disk resolution and settings paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from explorer.presentation.checklist_stats_display import (
    COUNTRY_TAB_SORT_ALPHABETICAL,
    COUNTRY_TAB_SORT_LIFERS_WORLD,
    COUNTRY_TAB_SORT_TOTAL_SPECIES,
)
from explorer.core.settings_schema_defaults import (
    MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT,
    TAXONOMY_LOCALE_DEFAULT,
)
from explorer.app.streamlit.defaults import (
    SETTINGS_PANEL_MAX_WIDTH_REM,
    SPINNER_THEME_CSS_CACHE_KEY_SUFFIX,
    THEME_PRIMARY_HEX,
    THEME_SECONDARY_BG_HEX,
    THEME_TEXT_HEX,
)
from explorer.app.streamlit.streamlit_ui_constants import DEFAULT_EBIRD_DATA_FILENAME

STREAMLIT_APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = str(STREAMLIT_APP_DIR.parent.parent.parent)

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
</style>
"""

DEFAULT_CLOSE_LOCATION_METERS = MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT
DEFAULT_TAXONOMY_LOCALE = TAXONOMY_LOCALE_DEFAULT

# ---------------------------------------------------------------------------
# Streamlit session-state key names (refs #99)
# ---------------------------------------------------------------------------
# Keep session-state keys (especially ``streamlit_*`` and internal ``_streamlit_*``)
# in one place to avoid typos and hard-to-find mismatches during refactors.

# App-wide misc/internal session keys used in ``explorer.app.streamlit.app``.
EBIRD_DATA_SIG_KEY = "ebird_data_sig"
EXPLORER_MAP_HTML_BYTES_KEY = "_explorer_map_html_bytes"
POPUP_HTML_CACHE_KEY = "popup_html_cache"
FILTERED_BY_LOC_CACHE_KEY = "filtered_by_loc_cache"

# Landing page container/widget keys.
EBIRD_LANDING_MAIN_CONTAINER_KEY = "ebird_landing_main"
EBIRD_LANDING_CSV_UPLOADER_KEY = "ebird_landing_csv_uploader"

# Map view widget keys.
STREAMLIT_MAP_VIEW_LABEL_KEY = "streamlit_map_view_label"
STREAMLIT_MAP_DATE_FILTER_KEY = "streamlit_map_date_filter"
STREAMLIT_MAP_DATE_RANGE_KEY = "streamlit_map_date_range"
STREAMLIT_SPECIES_HIDE_ONLY_KEY = "streamlit_species_hide_only"
STREAMLIT_LIFER_SHOW_SUBSPECIES_KEY = "streamlit_lifer_show_subspecies"
STREAMLIT_MAP_BASEMAP_KEY = "streamlit_map_basemap"
STREAMLIT_MAP_HEIGHT_PX_KEY = "streamlit_map_height_px"

# Settings button keys.
STREAMLIT_SAVE_SETTINGS_BTN_KEY = "streamlit_save_settings_btn"
STREAMLIT_RESET_SETTINGS_BTN_KEY = "streamlit_reset_settings_btn"

# Download/export button keys.
EXPORT_MAP_HTML_BTN_KEY = "export_map_html_btn"

# Checklist stats payload keys (used by fragments).
YEARLY_SUMMARY_TAB_CHECKLIST_PAYLOAD_KEY = "_streamlit_yearly_summary_checklist_payload"
COUNTRY_TAB_CHECKLIST_PAYLOAD_KEY = "_streamlit_country_tab_checklist_payload"
CHECKLIST_STATS_TAB_WORK_PAYLOAD_KEY = "_streamlit_checklist_stats_work_payload"
RANKINGS_TAB_BUNDLE_KEY = "_streamlit_rankings_tab_bundle"
MAINTENANCE_TAB_SYNC_KEY = "_streamlit_maintenance_tab_sync"

# "Show full history" toggles.
STREAMLIT_YEARLY_SUMMARY_SHOW_FULL_KEY = "streamlit_yearly_summary_show_full"
STREAMLIT_COUNTRY_YEARLY_SHOW_FULL_KEY = "streamlit_country_yearly_show_full"

# Country selectbox key.
STREAMLIT_COUNTRY_TAB_COUNTRY_KEY = "streamlit_country_tab_country"

# Settings/table/list/toggle keys (all used as ``key=...`` or ``st.session_state[...]``).
STREAMLIT_POPUP_SORT_ORDER_KEY = "streamlit_popup_sort_order"
STREAMLIT_POPUP_SCROLL_HINT_KEY = "streamlit_popup_scroll_hint"
STREAMLIT_MARK_LIFER_KEY = "streamlit_mark_lifer"
STREAMLIT_MARK_LAST_SEEN_KEY = "streamlit_mark_last_seen"
# All-locations map only (species / lifer maps never cluster).
# Runtime: sidebar toggle; map build + cache signature.
STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY = "streamlit_map_cluster_all_locations"
# Settings → Apply map settings: defer syncing this key until next run (before sidebar widget; refs Streamlit widget rules).
STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_APPLY_PENDING_KEY = "_streamlit_map_cluster_apply_from_settings_pending"
# Persisted default: Settings form + Save settings / YAML (may differ from runtime after sidebar).
STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_SAVED_KEY = "streamlit_map_cluster_all_locations_saved"

STREAMLIT_DEFAULT_COLOR_KEY = "streamlit_default_color"
STREAMLIT_SPECIES_COLOR_KEY = "streamlit_species_color"
STREAMLIT_LIFER_COLOR_KEY = "streamlit_lifer_color"
STREAMLIT_LAST_SEEN_COLOR_KEY = "streamlit_last_seen_color"

STREAMLIT_DEFAULT_FILL_KEY = "streamlit_default_fill"
STREAMLIT_SPECIES_FILL_KEY = "streamlit_species_fill"
STREAMLIT_LIFER_FILL_KEY = "streamlit_lifer_fill"
STREAMLIT_LAST_SEEN_FILL_KEY = "streamlit_last_seen_fill"

STREAMLIT_TAXONOMY_LOCALE_KEY = "streamlit_taxonomy_locale"
STREAMLIT_RANKINGS_TOP_N_KEY = "streamlit_rankings_top_n"
STREAMLIT_RANKINGS_VISIBLE_ROWS_KEY = "streamlit_rankings_visible_rows"
STREAMLIT_HIGH_COUNT_SORT_KEY = "streamlit_high_count_sort"
STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY = "streamlit_high_count_tie_break"
STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY = "streamlit_yearly_recent_column_count"
STREAMLIT_COUNTRY_TAB_SORT_KEY = "streamlit_country_tab_sort"
STREAMLIT_CLOSE_LOCATION_METERS_KEY = "streamlit_close_location_meters"

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
# Bumped when toggling Map view All locations <-> Selected species so streamlit-folium remounts cleanly.
FOLIUM_MAP_MOUNT_NONCE_KEY = "_folium_map_mount_nonce"
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
    STREAMLIT_POPUP_SORT_ORDER_KEY,
    STREAMLIT_POPUP_SCROLL_HINT_KEY,
    STREAMLIT_MARK_LIFER_KEY,
    STREAMLIT_MARK_LAST_SEEN_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_KEY,
    STREAMLIT_MAP_CLUSTER_ALL_LOCATIONS_SAVED_KEY,
    STREAMLIT_DEFAULT_COLOR_KEY,
    STREAMLIT_DEFAULT_FILL_KEY,
    STREAMLIT_SPECIES_COLOR_KEY,
    STREAMLIT_SPECIES_FILL_KEY,
    STREAMLIT_LIFER_COLOR_KEY,
    STREAMLIT_LIFER_FILL_KEY,
    STREAMLIT_LAST_SEEN_COLOR_KEY,
    STREAMLIT_LAST_SEEN_FILL_KEY,
    STREAMLIT_TAXONOMY_LOCALE_KEY,
    STREAMLIT_RANKINGS_TOP_N_KEY,
    STREAMLIT_RANKINGS_VISIBLE_ROWS_KEY,
    STREAMLIT_HIGH_COUNT_SORT_KEY,
    STREAMLIT_HIGH_COUNT_TIE_BREAK_KEY,
    STREAMLIT_YEARLY_RECENT_COLUMN_COUNT_KEY,
    STREAMLIT_COUNTRY_TAB_SORT_KEY,
    STREAMLIT_CLOSE_LOCATION_METERS_KEY,
)

SPINNER_THEME_CSS_INJECTED_KEY = f"_ebird_spinner_theme_css_injected_{SPINNER_THEME_CSS_CACHE_KEY_SUFFIX}"

SPINNER_THEME_CSS = f"""
<style>
/* Hoisted ``st.spinner`` — theme greens (refs #74); bump SPINNER_THEME_CSS_CACHE_KEY_SUFFIX when CSS changes. */
/* In-flow pill (no position:fixed): avoids covering the title; spinner sits in script order after the subtitle. */
/* Modern Streamlit uses an icon spinner (``iconValue: spinner``), not a CSS border ring. */
div[data-testid="stSpinner"],
div[data-testid="stSpinner"].stSpinner {{
  color: {THEME_PRIMARY_HEX};
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  display: inline-flex !important;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.4rem 0.95rem !important;
  margin: 0.15rem 0 0.35rem 0 !important;
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
  border: 1px solid rgba(31, 111, 84, 0.14);
  max-width: min(96vw, 42rem);
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
/* Spinner message: markdown — slightly smaller type, primary green (matches palette). */
div[data-testid="stSpinner"] [data-testid="stMarkdownContainer"],
div[data-testid="stSpinner"] [data-testid="stMarkdownContainer"] * {{
  color: {THEME_PRIMARY_HEX} !important;
  font-size: 0.875rem !important;
  line-height: 1.45 !important;
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}}
div[data-testid="stSpinner"] p,
div[data-testid="stSpinner"] span,
div[data-testid="stSpinner"] label {{
  color: {THEME_PRIMARY_HEX} !important;
  font-size: 0.875rem !important;
}}
/* Older border-based spinner (harmless if unused) */
div[data-testid="stSpinner"] div[class*="Spinner"] {{
  border-color: {THEME_SECONDARY_BG_HEX} !important;
  border-top-color: {THEME_PRIMARY_HEX} !important;
}}

/* Bird-emoji strip (only ``components.html`` in Explorer uses height 52): tuck under spinner, centered. */
[data-testid="stAppViewContainer"] main iframe[height="52"],
[data-testid="stSidebar"] iframe[height="52"] {{
  display: block !important;
  margin: 0.1rem auto 0.4rem auto !important;
  border: none !important;
  max-width: 100%;
}}
[data-testid="stSidebar"] div[data-testid="stSpinner"],
[data-testid="stSidebar"] div[data-testid="stSpinner"].stSpinner {{
  max-width: 100%;
  box-sizing: border-box;
  /* Keep spinner in normal sidebar flow (no viewport-fixed “floating pill” glitches). */
  position: relative !important;
  left: auto !important;
  top: auto !important;
  transform: none !important;
  display: flex !important;
  width: 100%;
}}
/* Reserve a stable bottom band: spinner + emoji share the same footprint as the footer links. */
[data-testid="stSidebar"] .ebird-sidebar-bottom-slot {{
  min-height: 7.5rem;
  padding-top: 0.35rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}}
</style>
"""

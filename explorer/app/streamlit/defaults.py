"""
Developer reference: default values for the Streamlit explorer (refs #70).

Embedded settings schema and map geometry live under ``personal_ebird_explorer`` so the
core package does not depend on this module (refs #89). This file re-exports those
symbols for the Streamlit app and keeps UI-only literals here.
"""

from __future__ import annotations

# Re-export schema + map UI constants (single source in ``personal_ebird_explorer``).
from personal_ebird_explorer.map_ui_constants import (  # noqa: F401
    MAP_CIRCLE_MARKER_RADIUS_PX,
    MAP_CIRCLE_MARKER_STROKE_WEIGHT,
    MAP_LEGEND_PIN_BORDER_PX,
    MAP_LEGEND_PIN_DOT_PX,
    MAP_PIN_FILL_OPACITY_ALL_LOCATIONS,
    MAP_PIN_FILL_OPACITY_EMPHASIS,
    MAP_POPUP_MAX_WIDTH_PX,
)
from personal_ebird_explorer.settings_schema_defaults import (  # noqa: F401
    MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT,
    MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
    MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
    MAP_DEFAULT_COLOR_DEFAULT,
    MAP_DEFAULT_FILL_DEFAULT,
    MAP_LAST_SEEN_COLOR_DEFAULT,
    MAP_LAST_SEEN_FILL_DEFAULT,
    MAP_LIFER_COLOR_DEFAULT,
    MAP_LIFER_FILL_DEFAULT,
    MAP_MARK_LAST_SEEN_DEFAULT,
    MAP_MARK_LIFER_DEFAULT,
    MAP_PIN_COLOUR_ALLOWLIST,
    MAP_POPUP_SCROLL_HINT_DEFAULT,
    MAP_POPUP_SORT_ORDER_DEFAULT,
    MAP_SPECIES_COLOR_DEFAULT,
    MAP_SPECIES_FILL_DEFAULT,
    SETTINGS_SCHEMA_VERSION,
    TABLES_RANKINGS_TOP_N_DEFAULT,
    TABLES_RANKINGS_TOP_N_MAX,
    TABLES_RANKINGS_TOP_N_MIN,
    TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT,
    TABLES_RANKINGS_VISIBLE_ROWS_MAX,
    TABLES_RANKINGS_VISIBLE_ROWS_MIN,
    TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT,
    TABLES_HIGH_COUNT_SORT_DEFAULT,
    TAXONOMY_LOCALE_DEFAULT,
    YEARLY_RECENT_COLUMN_COUNT_DEFAULT,
    YEARLY_RECENT_COLUMN_COUNT_MAX,
    YEARLY_RECENT_COLUMN_COUNT_MIN,
    build_persisted_settings_defaults_dict,
)


# ---------------------------------------------------------------------------
# Data resolution & exports
# ---------------------------------------------------------------------------

DEFAULT_EBIRD_DATA_FILENAME = "MyEBirdData.csv"
# Env overrides (see ``app.py``): ``STREAMLIT_EBIRD_DATA_FILE`` (CSV basename),
# ``STREAMLIT_EBIRD_TAXONOMY_LOCALE``, ``EBIRD_TAXONOMY_LOCALE``. Data folder: ``scripts/config_*.py``
# or process working directory — not an env var (see ``explorer_paths`` / ``streamlit_app/README.md``).

MAP_EXPORT_HTML_FILENAME = "ebird_map.html"

# Checklist Statistics tab payload (not the same slider as Rankings Top N).
CHECKLIST_STATS_TOP_N_TABLE_LIMIT = 200

# ---------------------------------------------------------------------------
# Map UI (session-only; not persisted in embedded YAML)
# ---------------------------------------------------------------------------

# ``carto`` = Folium/xyzservices ``CartoDB Positron``. No API keys.
MAP_BASEMAP_OPTIONS: tuple[str, ...] = ("default", "google", "carto")
MAP_BASEMAP_LABELS: dict[str, str] = {
    "default": "Default",
    "google": "Google (hybrid)",
    "carto": "CartoDB Positron",
}
MAP_BASEMAP_DEFAULT = "default"

MAP_HEIGHT_PX_DEFAULT = 720
MAP_HEIGHT_PX_MIN = 440
MAP_HEIGHT_PX_MAX = 1200
MAP_HEIGHT_PX_STEP = 20

# First-run date filter: off unless restored from Lifer view (see ``app.py``).
MAP_DATE_FILTER_DEFAULT = False

MAP_VIEW_LABELS: tuple[str, ...] = ("All locations", "Selected species", "Lifer locations")

# ---------------------------------------------------------------------------
# Species search (``streamlit-searchbox`` fragment)
# ---------------------------------------------------------------------------

SPECIES_SEARCH_MAX_OPTIONS = 12
SPECIES_SEARCH_MIN_QUERY_LEN = 3
SPECIES_SEARCH_DEBOUNCE_MS = 400
SPECIES_SEARCH_PLACEHOLDER = "Type species name…"
SPECIES_SEARCH_CAPTION = (
    "Type at least three letters. Searches common and scientific names."
)
SPECIES_SEARCH_EDIT_AFTER_SUBMIT = "option"
SPECIES_SEARCH_RERUN_SCOPE = "fragment"

# ---------------------------------------------------------------------------
# Layout / theme (Streamlit-only)
# ---------------------------------------------------------------------------

SETTINGS_PANEL_MAX_WIDTH_REM = 40

# Match ``.streamlit/config.toml`` [theme] (forest / eBird-adjacent greens).
THEME_TEXT_HEX = "#1A2E22"
THEME_PRIMARY_HEX = "#1F6F54"
THEME_SECONDARY_BG_HEX = "#EEF4F0"

# Bump suffix in ``app_map_ui.inject_spinner_theme_css`` when spinner CSS changes.
SPINNER_THEME_CSS_CACHE_KEY_SUFFIX = "v4"

# ---------------------------------------------------------------------------
# Ranking & Lists HTML (``rankings_streamlit_html``)
# ---------------------------------------------------------------------------

RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX = 1400
RANKINGS_BUNDLE_SCROLL_HINT_DEFAULT = "shading"

# ---------------------------------------------------------------------------
# Main chrome
# ---------------------------------------------------------------------------

NOTEBOOK_MAIN_TAB_LABELS: tuple[str, ...] = (
    "Map",
    "Checklist Statistics",
    "Ranking & Lists",
    "Yearly Summary",
    "Country",
    "Maintenance",
    "Settings",
)

# Bird emoji (Unicode order in message: legacy sequence first, then missing taxa; Dodo last — refs #74).
CHECKLIST_STATS_SPINNER_MESSAGE = (
    "Doing interesting things with your eBird data  "
    "🐣 🐥 🐧 🦆 🦉 🦢 🦅 "
    "🦃 🐔 🐓 🐤 🐦 🕊️ 🪶 🦩 🦚 🦜 🐦‍⬛ 🪿 🦤"
)

GITHUB_REPO_URL = "https://github.com/jimchurches/myebirdstuff"
EBIRD_PROFILE_URL = "https://ebird.org/profile/MjkxNDYyNQ"
INSTAGRAM_PROFILE_URL = "https://www.instagram.com/jimchurches/"

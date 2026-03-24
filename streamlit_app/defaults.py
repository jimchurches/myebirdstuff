"""
Developer reference: default values for the Streamlit explorer (refs #70).

Single place to discover literals that would otherwise be scattered across ``app.py``,
settings models, and HTML helpers. Persisted settings (embedded YAML) are built with
:func:`build_persisted_settings_defaults_dict`; UI-only defaults are module-level constants.
"""

from __future__ import annotations

from typing import Any

from personal_ebird_explorer.checklist_stats_display import COUNTRY_TAB_SORT_ALPHABETICAL

# ---------------------------------------------------------------------------
# Embedded settings schema (``personal_ebird_explorer.streamlit_settings_config``)
# ---------------------------------------------------------------------------

SETTINGS_SCHEMA_VERSION = 1

MAP_POPUP_SORT_ORDER_DEFAULT = "ascending"
MAP_POPUP_SCROLL_HINT_DEFAULT = "shading"
MAP_MARK_LIFER_DEFAULT = True
MAP_MARK_LAST_SEEN_DEFAULT = True
MAP_DEFAULT_COLOR_DEFAULT = "green"
MAP_DEFAULT_FILL_DEFAULT = "lightgreen"
MAP_SPECIES_COLOR_DEFAULT = "purple"
MAP_SPECIES_FILL_DEFAULT = "red"
MAP_LIFER_COLOR_DEFAULT = "purple"
MAP_LIFER_FILL_DEFAULT = "yellow"
MAP_LAST_SEEN_COLOR_DEFAULT = "purple"
MAP_LAST_SEEN_FILL_DEFAULT = "lightgreen"

TABLES_RANKINGS_TOP_N_DEFAULT = 200
TABLES_RANKINGS_TOP_N_MIN = 10
TABLES_RANKINGS_TOP_N_MAX = 500

TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT = 16
TABLES_RANKINGS_VISIBLE_ROWS_MIN = 10
TABLES_RANKINGS_VISIBLE_ROWS_MAX = 50

YEARLY_RECENT_COLUMN_COUNT_DEFAULT = 10
YEARLY_RECENT_COLUMN_COUNT_MIN = 3
YEARLY_RECENT_COLUMN_COUNT_MAX = 25

MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT = 10
MAINTENANCE_CLOSE_LOCATION_METERS_MIN = 0
MAINTENANCE_CLOSE_LOCATION_METERS_MAX = 250

TAXONOMY_LOCALE_DEFAULT = "en_AU"

# Allowed pin / selectbox colours (settings + session clamping).
MAP_PIN_COLOUR_ALLOWLIST: tuple[str, ...] = (
    "white",
    "black",
    "red",
    "lime",
    "blue",
    "yellow",
    "cyan",
    "magenta",
    "orange",
    "purple",
    "pink",
    "lightgreen",
    "lightblue",
    "gray",
    "lightgray",
    "darkgray",
    "coral",
    "gold",
    "green",
)


def build_persisted_settings_defaults_dict() -> dict[str, Any]:
    """Full default payload matching :class:`StreamlitSettingsConfig` (embedded YAML)."""
    return {
        "version": SETTINGS_SCHEMA_VERSION,
        "map_display": {
            "popup_sort_order": MAP_POPUP_SORT_ORDER_DEFAULT,
            "popup_scroll_hint": MAP_POPUP_SCROLL_HINT_DEFAULT,
            "mark_lifer": MAP_MARK_LIFER_DEFAULT,
            "mark_last_seen": MAP_MARK_LAST_SEEN_DEFAULT,
            "default_color": MAP_DEFAULT_COLOR_DEFAULT,
            "default_fill": MAP_DEFAULT_FILL_DEFAULT,
            "species_color": MAP_SPECIES_COLOR_DEFAULT,
            "species_fill": MAP_SPECIES_FILL_DEFAULT,
            "lifer_color": MAP_LIFER_COLOR_DEFAULT,
            "lifer_fill": MAP_LIFER_FILL_DEFAULT,
            "last_seen_color": MAP_LAST_SEEN_COLOR_DEFAULT,
            "last_seen_fill": MAP_LAST_SEEN_FILL_DEFAULT,
        },
        "tables_lists": {
            "rankings_top_n": TABLES_RANKINGS_TOP_N_DEFAULT,
            "rankings_visible_rows": TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT,
        },
        "yearly_summary": {
            "recent_column_count": YEARLY_RECENT_COLUMN_COUNT_DEFAULT,
        },
        "country": {
            "sort": COUNTRY_TAB_SORT_ALPHABETICAL,
        },
        "maintenance": {
            "close_location_meters": MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT,
        },
        "taxonomy": {
            "locale": TAXONOMY_LOCALE_DEFAULT,
        },
    }


# ---------------------------------------------------------------------------
# Data resolution & exports
# ---------------------------------------------------------------------------

DEFAULT_EBIRD_DATA_FILENAME = "MyEBirdData.csv"
# Env overrides (see ``app.py`` / ``explorer_paths``): ``STREAMLIT_EBIRD_DATA_FILE`` (filename),
# ``STREAMLIT_EBIRD_DATA_FOLDER``, ``STREAMLIT_EBIRD_TAXONOMY_LOCALE``, ``EBIRD_TAXONOMY_LOCALE``.

MAP_EXPORT_HTML_FILENAME = "ebird_map.html"

# Checklist Statistics tab payload (not the same slider as Rankings Top N).
CHECKLIST_STATS_TOP_N_TABLE_LIMIT = 200

# ---------------------------------------------------------------------------
# Map UI (session-only; not persisted in embedded YAML)
# ---------------------------------------------------------------------------

MAP_BASEMAP_OPTIONS: tuple[str, ...] = ("default", "satellite", "google", "carto")
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

# Bump suffix in ``app.py`` when spinner CSS changes.
SPINNER_THEME_CSS_CACHE_KEY_SUFFIX = "v3"

# ---------------------------------------------------------------------------
# Rankings & lists HTML (``rankings_streamlit_html``)
# ---------------------------------------------------------------------------

RANKINGS_TABLE_LAYOUT_MAX_WIDTH_PX = 1400
RANKINGS_BUNDLE_SCROLL_HINT_DEFAULT = "shading"

# ---------------------------------------------------------------------------
# Main chrome
# ---------------------------------------------------------------------------

NOTEBOOK_MAIN_TAB_LABELS: tuple[str, ...] = (
    "Map",
    "Checklist Statistics",
    "Rankings & lists",
    "Yearly Summary",
    "Country",
    "Maintenance",
    "Settings",
)

CHECKLIST_STATS_SPINNER_MESSAGE = (
    "Doing interesting things with your eBird data  🐣  🐥  🐧  🦆  🦉  🦢  🦅  …"
)

GITHUB_REPO_URL = "https://github.com/jimchurches/myebirdstuff"
EBIRD_PROFILE_URL = "https://ebird.org/profile/MjkxNDYyNQ"
INSTAGRAM_PROFILE_URL = "https://www.instagram.com/jimchurches/"

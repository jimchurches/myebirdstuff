"""
Default values for the embedded Streamlit settings schema (YAML in ``config_*.py``).

Framework-neutral: no Streamlit imports. Used by :mod:`explorer.core.settings_config`
and re-exported from ``explorer.app.streamlit.defaults`` for the Streamlit UI (refs #89).
"""

from __future__ import annotations

from typing import Any

from explorer.core.constants import COUNTRY_TAB_SORT_ALPHABETICAL

SETTINGS_SCHEMA_VERSION = 1

MAP_POPUP_SORT_ORDER_DEFAULT = "ascending"
MAP_POPUP_SCROLL_HINT_DEFAULT = "shading"
MAP_MARK_LIFER_DEFAULT = True
MAP_MARK_LAST_SEEN_DEFAULT = True
MAP_DEFAULT_COLOR_DEFAULT = "green"
MAP_DEFAULT_FILL_DEFAULT = "lightgray"
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

TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT = "last"
TABLES_HIGH_COUNT_SORT_DEFAULT = "total_count"

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
            "high_count_sort": TABLES_HIGH_COUNT_SORT_DEFAULT,
            "high_count_tie_break": TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT,
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

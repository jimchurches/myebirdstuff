"""
Personal eBird Explorer — Streamlit prototype (Folium map + notebook-style popups).

Planning and phased migration notes: https://github.com/jimchurches/myebirdstuff/issues/70 (refs #70).

Run locally from repo root::

    pip install -r requirements-streamlit.txt
    streamlit run streamlit_app/app.py

Disk resolution when no file is uploaded: ``scripts/config_secret.py`` and
``scripts/config.py`` (``DATA_FOLDER``), then the **process working directory**
(where you ran ``streamlit run``). See ``streamlit_app/README.md`` — *Data loading*.

Streamlit Cloud: CSV upload on the **landing** main area when disk resolution finds no file; session
state keeps upload bytes for reruns (no data picker on the dashboard). After a successful pick we
``st.rerun()`` so the next run loads from cache and **does not** emit landing widgets (title/uploader)
in the same pass as the dashboard — otherwise Streamlit’s top-to-bottom execution leaves landing + tabs
on screen together. If Streamlit Cloud still shows a stray upload blurb under tabs, treat as a
separate delta/orphan issue (e.g. container boundaries, Streamlit version); same-run load traded that
for a worse duplicate layout locally.

**No-data landing:** No disk file and no cached upload → title, copy, uploader in the main column.
Disk path takes precedence over a stale session upload when both exist.

**Taxonomy:** After CSV load, the app fetches the eBird taxonomy once per session (cached) so species
names in popups can link to eBird species pages. Default locale is **en_AU**; override with
``STREAMLIT_EBIRD_TAXONOMY_LOCALE`` / ``EBIRD_TAXONOMY_LOCALE`` or **Settings → Taxonomy**.
Streamlit does not expose the browser language to Python.

**Checklist Statistics:** Shared HTML sections (nested ``st.tabs`` + formatted tables from
``checklist_stats_streamlit_tab_sections_html``). ``_cached_checklist_stats_payload`` runs **once** immediately
under the main tab bar (inside ``st.spinner("Doing interesting things with your eBird data...")``) so the loading message shows
no matter which tab is selected (refs #70).

**Country:** Per-country yearly table uses the same ``CHECKLIST_STATS_*`` HTML/CSS as Checklist Statistics
(``country_stats_streamlit_html``). The tab runs inside ``@st.fragment`` so changing the country selectbox
triggers a **partial rerun** (not the whole map/checklist pipeline) (refs #75).

**Maintenance:** Location duplicates / close locations, incomplete checklists, and sex-notation scan use
``maintenance_streamlit_html`` (nested tabs + expanders + shared HTML builders). Incomplete lists and sex
notation use the **full** export (``df_full``), not the date-filtered working set. **Close location (m)** is
configurable under **Settings → Maintenance** (refs #79).

**Rankings & lists:** ``rankings_streamlit_html`` — nested **Top Lists** / **Interesting Lists** tabs,
expanders per list, HTML from ``format_checklist_stats_bundle`` on ``df_full``. **Top N** and **visible rows**
are configured under **Settings → Tables & lists** (refs `#81`).

**Yearly Summary:** ``yearly_summary_streamlit_html`` — nested **All** / **Travelling** / **Stationary** tabs inside
``@st.fragment``; ``st.toggle`` switches recent vs full year columns when count exceeds **Settings → Yearly tables:
recent year columns** (default 10). ``sync_yearly_summary_session_inputs`` + ``run_yearly_summary_streamlit_fragment``
match the Country tab fragment pattern (refs #85).

**Main tabs + sidebar:** All tab bodies run each rerun (instant tab switching), with one always-on sidebar that
contains map controls plus footer links (refs #70). Settings sliders use a keyed container with
``max-width: min(100%, 40rem)`` on wide viewports.
"""

from __future__ import annotations

import html
import io
import os
import sys
from collections import OrderedDict
from typing import Any, Callable

import pandas as pd
import streamlit as st

# Repo root (parent of streamlit_app/)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_APP_DIR, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from personal_ebird_explorer.checklist_stats_compute import (  # noqa: E402
    ChecklistStatsPayload,
    compute_checklist_stats_payload,
)
from personal_ebird_explorer.data_loader import load_dataset  # noqa: E402
from personal_ebird_explorer.explorer_paths import (  # noqa: E402
    build_explorer_candidate_dirs,
    resolve_ebird_data_file,
    settings_yaml_path_for_source,
)
from personal_ebird_explorer.map_controller import build_species_overlay_map  # noqa: E402
from personal_ebird_explorer.species_search import (  # noqa: E402
    build_ram_species_whoosh_index,
    whoosh_species_suggestions,
)
from personal_ebird_explorer.species_logic import base_species_for_lifer  # noqa: E402
from personal_ebird_explorer.streamlit_map_prep import (  # noqa: E402
    data_signature_for_caches,
    prepare_all_locations_map_context,
)
from checklist_stats_streamlit_html import render_checklist_stats_streamlit_html  # noqa: E402
from rankings_streamlit_html import render_rankings_streamlit_tab  # noqa: E402
from personal_ebird_explorer.checklist_stats_display import (  # noqa: E402
    COUNTRY_TAB_SORT_ALPHABETICAL,
    COUNTRY_TAB_SORT_LIFERS_WORLD,
    COUNTRY_TAB_SORT_TOTAL_SPECIES,
)
from country_stats_streamlit_html import (  # noqa: E402
    run_country_tab_streamlit_fragment,
    sync_country_tab_session_inputs,
)
from maintenance_streamlit_html import render_maintenance_streamlit_tab  # noqa: E402
from yearly_summary_streamlit_html import (  # noqa: E402
    run_yearly_summary_streamlit_fragment,
    sync_yearly_summary_session_inputs,
)
from map_working import (  # noqa: E402
    date_inception_to_today_default,
    folium_map_to_html_bytes,
    streamlit_working_set_and_status,
)
from streamlit_app.defaults import (  # noqa: E402
    CHECKLIST_STATS_SPINNER_MESSAGE,
    CHECKLIST_STATS_TOP_N_TABLE_LIMIT,
    DEFAULT_EBIRD_DATA_FILENAME,
    EBIRD_PROFILE_URL,
    GITHUB_REPO_URL,
    INSTAGRAM_PROFILE_URL,
    MAP_BASEMAP_DEFAULT,
    MAP_BASEMAP_OPTIONS,
    MAP_DATE_FILTER_DEFAULT,
    MAP_EXPORT_HTML_FILENAME,
    MAP_HEIGHT_PX_DEFAULT,
    MAP_HEIGHT_PX_MAX,
    MAP_HEIGHT_PX_MIN,
    MAP_HEIGHT_PX_STEP,
    MAP_VIEW_LABELS,
    MAP_LAST_SEEN_COLOR_DEFAULT,
    MAP_LAST_SEEN_FILL_DEFAULT,
    MAP_DEFAULT_COLOR_DEFAULT,
    MAP_DEFAULT_FILL_DEFAULT,
    MAP_LIFER_COLOR_DEFAULT,
    MAP_LIFER_FILL_DEFAULT,
    MAP_MARK_LAST_SEEN_DEFAULT,
    MAP_MARK_LIFER_DEFAULT,
    MAP_PIN_COLOUR_ALLOWLIST,
    MAP_POPUP_SCROLL_HINT_DEFAULT,
    MAP_POPUP_SORT_ORDER_DEFAULT,
    MAP_SPECIES_COLOR_DEFAULT,
    MAP_SPECIES_FILL_DEFAULT,
    MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT,
    MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
    MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
    NOTEBOOK_MAIN_TAB_LABELS,
    SETTINGS_PANEL_MAX_WIDTH_REM,
    SETTINGS_SCHEMA_VERSION,
    SPECIES_SEARCH_CAPTION,
    SPECIES_SEARCH_DEBOUNCE_MS,
    SPECIES_SEARCH_EDIT_AFTER_SUBMIT,
    SPECIES_SEARCH_MAX_OPTIONS,
    SPECIES_SEARCH_MIN_QUERY_LEN,
    SPECIES_SEARCH_PLACEHOLDER,
    SPECIES_SEARCH_RERUN_SCOPE,
    SPINNER_THEME_CSS_CACHE_KEY_SUFFIX,
    TABLES_RANKINGS_TOP_N_DEFAULT,
    TABLES_RANKINGS_TOP_N_MAX,
    TABLES_RANKINGS_TOP_N_MIN,
    TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT,
    TABLES_RANKINGS_VISIBLE_ROWS_MAX,
    TABLES_RANKINGS_VISIBLE_ROWS_MIN,
    TAXONOMY_LOCALE_DEFAULT,
    THEME_PRIMARY_HEX,
    THEME_SECONDARY_BG_HEX,
    THEME_TEXT_HEX,
    YEARLY_RECENT_COLUMN_COUNT_DEFAULT,
    YEARLY_RECENT_COLUMN_COUNT_MAX,
    YEARLY_RECENT_COLUMN_COUNT_MIN,
    build_persisted_settings_defaults_dict,
)

DEFAULT_EBIRD_FILENAME = os.environ.get("STREAMLIT_EBIRD_DATA_FILE", DEFAULT_EBIRD_DATA_FILENAME)

# Map view labels → mode string; basemap/height use session keys (refs #70).
_MAP_VIEW_LABEL_TO_MODE = {
    "All locations": "all",
    "Selected species": "species",
    "Lifer locations": "lifers",
}
# Settings tab: cap control width on large viewports; column still uses full width on narrow screens (refs #70).
_SETTINGS_PANEL_CSS = f"""
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

# Session-only: bytes + filename so reruns work without rendering ``st.file_uploader`` on the dashboard.
_SESSION_UPLOAD_CACHE_KEY = "_ebird_streamlit_upload_csv_cache"
# Survive Map view switch All locations ↔ Lifer (widgets not rendered on Lifer runs).
_PERSIST_MAP_DATE_FILTER_KEY = "_preserve_map_date_filter"
_PERSIST_MAP_DATE_RANGE_KEY = "_preserve_map_date_range"
# Remember species pick when switching map view (e.g. species → Lifer → back).
_PERSIST_SPECIES_COMMON_KEY = "_preserve_streamlit_species_common"
_PERSIST_SPECIES_SCI_KEY = "_preserve_streamlit_species_sci"
_SESSION_PREV_MAP_VIEW_KEY = "_streamlit_prev_map_view_mode"
_SESSION_SPECIES_SEARCH_KEY = "streamlit_species_searchbox"
_SESSION_SPECIES_WS_KEY = "_ws_for_species_search_fragment"
_SESSION_SPECIES_IX_KEY = "_streamlit_species_whoosh_ix"
_SESSION_SPECIES_IX_SIG_KEY = "_streamlit_species_whoosh_ix_sig"
_SESSION_SPECIES_PICK_KEY = "_streamlit_species_pick_common"
_FOLIUM_STATIC_MAP_CACHE_KEY = "_folium_static_all_lifer_cache"
_SETTINGS_CONFIG_PATH_KEY = "_streamlit_settings_yaml_path"
_SETTINGS_CONFIG_SOURCE_KEY = "_streamlit_settings_source_label"
_SETTINGS_LOADED_FROM_KEY = "_streamlit_settings_loaded_from_path"
_SETTINGS_BASELINE_KEY = "_streamlit_settings_saved_baseline"
_SETTINGS_WARNED_KEY = "_streamlit_settings_warned"
_SETTINGS_FLASH_SAVE_KEY = "_streamlit_settings_flash_save"
_SETTINGS_FLASH_RESET_KEY = "_streamlit_settings_flash_reset"

_COUNTRY_SORT_LABELS = {
    COUNTRY_TAB_SORT_ALPHABETICAL: "Alphabetical",
    COUNTRY_TAB_SORT_LIFERS_WORLD: "By lifers (world)",
    COUNTRY_TAB_SORT_TOTAL_SPECIES: "By total species",
}

_SETTINGS_SESSION_KEYS = (
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

# Session flag: avoid stacking duplicate ``<style>`` blocks on every rerun.
# Bump ``SPINNER_THEME_CSS_CACHE_KEY_SUFFIX`` in :mod:`streamlit_app.defaults` when CSS changes.
_SPINNER_THEME_CSS_INJECTED_KEY = f"_ebird_spinner_theme_css_injected_{SPINNER_THEME_CSS_CACHE_KEY_SUFFIX}"

_SPINNER_THEME_CSS = f"""
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


def _inject_spinner_theme_css() -> None:
    """Tweak hoisted checklist-stats spinner to match our theme (refs #70).

    Use :func:`streamlit.html` for **style-only** blocks: ``st.markdown(..., unsafe_allow_html)``
    sanitizes or scopes HTML so global ``<style>`` may not affect the spinner; style-only
    ``st.html`` is applied via Streamlit’s event container (see Streamlit ``HtmlMixin.html``).
    """
    if st.session_state.get(_SPINNER_THEME_CSS_INJECTED_KEY):
        return
    # ``st.html`` exists from Streamlit 1.31+; requirements pin 1.40+.
    st.html(_SPINNER_THEME_CSS.strip())
    st.session_state[_SPINNER_THEME_CSS_INJECTED_KEY] = True


def _settings_persistence_flash_banners() -> None:
    """Full-width save/reset notices using theme greens (same style for both)."""
    if st.session_state.pop(_SETTINGS_FLASH_SAVE_KEY, False):
        st.markdown(
            '<div class="ebird-settings-persistence-banner">'
            "<strong>Saved.</strong> Preferences written to your configuration file."
            "</div>",
            unsafe_allow_html=True,
        )
    if st.session_state.pop(_SETTINGS_FLASH_RESET_KEY, False):
        st.markdown(
            '<div class="ebird-settings-persistence-banner">'
            "<strong>Defaults restored for this session.</strong> "
            "Click <strong>Save settings</strong> to persist."
            "</div>",
            unsafe_allow_html=True,
        )


def _init_and_clamp_streamlit_table_settings() -> None:
    """Defaults/ranges for Settings values (tables, maintenance, map display)."""
    if "streamlit_rankings_top_n" not in st.session_state:
        st.session_state.streamlit_rankings_top_n = TABLES_RANKINGS_TOP_N_DEFAULT
    else:
        st.session_state.streamlit_rankings_top_n = max(
            TABLES_RANKINGS_TOP_N_MIN,
            min(TABLES_RANKINGS_TOP_N_MAX, int(st.session_state.streamlit_rankings_top_n)),
        )
    if "streamlit_rankings_visible_rows" not in st.session_state:
        st.session_state.streamlit_rankings_visible_rows = TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT
    else:
        st.session_state.streamlit_rankings_visible_rows = max(
            TABLES_RANKINGS_VISIBLE_ROWS_MIN,
            min(
                TABLES_RANKINGS_VISIBLE_ROWS_MAX,
                int(st.session_state.streamlit_rankings_visible_rows),
            ),
        )
    if "streamlit_close_location_meters" not in st.session_state:
        st.session_state.streamlit_close_location_meters = DEFAULT_CLOSE_LOCATION_METERS
    else:
        st.session_state.streamlit_close_location_meters = max(
            MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
            min(
                MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
                int(st.session_state.streamlit_close_location_meters),
            ),
        )
    if "streamlit_yearly_recent_column_count" not in st.session_state:
        st.session_state.streamlit_yearly_recent_column_count = YEARLY_RECENT_COLUMN_COUNT_DEFAULT
    else:
        st.session_state.streamlit_yearly_recent_column_count = max(
            YEARLY_RECENT_COLUMN_COUNT_MIN,
            min(
                YEARLY_RECENT_COLUMN_COUNT_MAX,
                int(st.session_state.streamlit_yearly_recent_column_count),
            ),
        )
    if "streamlit_popup_sort_order" not in st.session_state:
        st.session_state.streamlit_popup_sort_order = MAP_POPUP_SORT_ORDER_DEFAULT
    elif st.session_state.streamlit_popup_sort_order not in ("ascending", "descending"):
        st.session_state.streamlit_popup_sort_order = MAP_POPUP_SORT_ORDER_DEFAULT
    if "streamlit_popup_scroll_hint" not in st.session_state:
        st.session_state.streamlit_popup_scroll_hint = MAP_POPUP_SCROLL_HINT_DEFAULT
    elif st.session_state.streamlit_popup_scroll_hint not in ("chevron", "shading", "both"):
        st.session_state.streamlit_popup_scroll_hint = MAP_POPUP_SCROLL_HINT_DEFAULT
    if "streamlit_mark_lifer" not in st.session_state:
        st.session_state.streamlit_mark_lifer = MAP_MARK_LIFER_DEFAULT
    if "streamlit_mark_last_seen" not in st.session_state:
        st.session_state.streamlit_mark_last_seen = MAP_MARK_LAST_SEEN_DEFAULT
    for k, default in (
        ("streamlit_lifer_color", MAP_LIFER_COLOR_DEFAULT),
        ("streamlit_lifer_fill", MAP_LIFER_FILL_DEFAULT),
        ("streamlit_last_seen_color", MAP_LAST_SEEN_COLOR_DEFAULT),
        ("streamlit_last_seen_fill", MAP_LAST_SEEN_FILL_DEFAULT),
        ("streamlit_species_color", MAP_SPECIES_COLOR_DEFAULT),
        ("streamlit_species_fill", MAP_SPECIES_FILL_DEFAULT),
        ("streamlit_default_color", MAP_DEFAULT_COLOR_DEFAULT),
        ("streamlit_default_fill", MAP_DEFAULT_FILL_DEFAULT),
    ):
        if k not in st.session_state:
            st.session_state[k] = default
        elif st.session_state[k] not in MAP_PIN_COLOUR_ALLOWLIST:
            st.session_state[k] = default


def _settings_state_payload() -> dict[str, Any]:
    """Current Settings payload in config schema shape."""
    return {
        "version": SETTINGS_SCHEMA_VERSION,
        "map_display": {
            "popup_sort_order": st.session_state.streamlit_popup_sort_order,
            "popup_scroll_hint": st.session_state.streamlit_popup_scroll_hint,
            "mark_lifer": bool(st.session_state.streamlit_mark_lifer),
            "mark_last_seen": bool(st.session_state.streamlit_mark_last_seen),
            "default_color": st.session_state.streamlit_default_color,
            "default_fill": st.session_state.streamlit_default_fill,
            "species_color": st.session_state.streamlit_species_color,
            "species_fill": st.session_state.streamlit_species_fill,
            "lifer_color": st.session_state.streamlit_lifer_color,
            "lifer_fill": st.session_state.streamlit_lifer_fill,
            "last_seen_color": st.session_state.streamlit_last_seen_color,
            "last_seen_fill": st.session_state.streamlit_last_seen_fill,
        },
        "tables_lists": {
            "rankings_top_n": int(st.session_state.streamlit_rankings_top_n),
            "rankings_visible_rows": int(st.session_state.streamlit_rankings_visible_rows),
        },
        "yearly_summary": {
            "recent_column_count": int(st.session_state.streamlit_yearly_recent_column_count),
        },
        "country": {
            "sort": st.session_state.streamlit_country_tab_sort,
        },
        "maintenance": {
            "close_location_meters": int(st.session_state.streamlit_close_location_meters),
        },
        "taxonomy": {
            "locale": (st.session_state.streamlit_taxonomy_locale.strip() or DEFAULT_TAXONOMY_LOCALE),
        },
    }


def _apply_settings_payload_to_state(cfg: dict[str, Any]) -> None:
    """Apply validated config payload to Streamlit session keys."""
    mp = cfg.get("map_display", {})
    tl = cfg.get("tables_lists", {})
    ys = cfg.get("yearly_summary", {})
    ct = cfg.get("country", {})
    mn = cfg.get("maintenance", {})
    tx = cfg.get("taxonomy", {})
    if isinstance(mp, dict):
        st.session_state.streamlit_popup_sort_order = mp.get(
            "popup_sort_order", MAP_POPUP_SORT_ORDER_DEFAULT
        )
        st.session_state.streamlit_popup_scroll_hint = mp.get(
            "popup_scroll_hint", MAP_POPUP_SCROLL_HINT_DEFAULT
        )
        st.session_state.streamlit_mark_lifer = bool(mp.get("mark_lifer", MAP_MARK_LIFER_DEFAULT))
        st.session_state.streamlit_mark_last_seen = bool(
            mp.get("mark_last_seen", MAP_MARK_LAST_SEEN_DEFAULT)
        )
        st.session_state.streamlit_default_color = mp.get("default_color", MAP_DEFAULT_COLOR_DEFAULT)
        st.session_state.streamlit_default_fill = mp.get("default_fill", MAP_DEFAULT_FILL_DEFAULT)
        st.session_state.streamlit_species_color = mp.get("species_color", MAP_SPECIES_COLOR_DEFAULT)
        st.session_state.streamlit_species_fill = mp.get("species_fill", MAP_SPECIES_FILL_DEFAULT)
        st.session_state.streamlit_lifer_color = mp.get("lifer_color", MAP_LIFER_COLOR_DEFAULT)
        st.session_state.streamlit_lifer_fill = mp.get("lifer_fill", MAP_LIFER_FILL_DEFAULT)
        st.session_state.streamlit_last_seen_color = mp.get(
            "last_seen_color", MAP_LAST_SEEN_COLOR_DEFAULT
        )
        st.session_state.streamlit_last_seen_fill = mp.get(
            "last_seen_fill", MAP_LAST_SEEN_FILL_DEFAULT
        )
    if isinstance(tl, dict):
        st.session_state.streamlit_rankings_top_n = int(
            tl.get("rankings_top_n", TABLES_RANKINGS_TOP_N_DEFAULT)
        )
        st.session_state.streamlit_rankings_visible_rows = int(
            tl.get("rankings_visible_rows", TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT)
        )
    if isinstance(ys, dict):
        st.session_state.streamlit_yearly_recent_column_count = int(
            ys.get("recent_column_count", YEARLY_RECENT_COLUMN_COUNT_DEFAULT)
        )
    if isinstance(ct, dict):
        st.session_state.streamlit_country_tab_sort = ct.get("sort", COUNTRY_TAB_SORT_ALPHABETICAL)
    if isinstance(mn, dict):
        st.session_state.streamlit_close_location_meters = int(
            mn.get("close_location_meters", DEFAULT_CLOSE_LOCATION_METERS)
        )
    if isinstance(tx, dict):
        st.session_state.streamlit_taxonomy_locale = str(tx.get("locale", DEFAULT_TAXONOMY_LOCALE))


def _settings_defaults_payload() -> dict[str, Any]:
    """Built-in defaults; used when config module/deps are unavailable."""
    return build_persisted_settings_defaults_dict()


def _load_settings_yaml_via_module(path: str) -> tuple[dict[str, Any], str | None]:
    try:
        from personal_ebird_explorer.streamlit_settings_config import load_settings_from_python_config
    except Exception as e:
        return _settings_defaults_payload(), f"Settings validation unavailable ({e}); using defaults."
    return load_settings_from_python_config(path)


def _write_settings_yaml_via_module(path: str, payload: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        from personal_ebird_explorer.streamlit_settings_config import write_sparse_settings_to_python_config
    except Exception as e:
        return False, f"Settings save unavailable ({e}). Install requirements-streamlit.txt."
    return write_sparse_settings_to_python_config(path, payload)


def _settings_config_module_available() -> bool:
    try:
        import personal_ebird_explorer.streamlit_settings_config  # noqa: F401
    except Exception:
        return False
    return True


def _static_map_cache_key(
    work_df: pd.DataFrame,
    map_view_mode: str,
    date_filter_banner: str,
    map_style: str,
    render_opts_sig: tuple = (),
    taxonomy_locale: str = "",
) -> tuple:
    """Stable key for All / Lifer map reuse (same CSV + filter + basemap + taxonomy)."""
    n = len(work_df)
    sid0 = ""
    if n > 0 and "Submission ID" in work_df.columns:
        sid0 = str(work_df["Submission ID"].iloc[0])
    tax = (taxonomy_locale or "").strip()
    return (map_view_mode, date_filter_banner, map_style, render_opts_sig, n, sid0, tax)


def _env_taxonomy_locale() -> str:
    """Non-empty locale from env if set (notebook parity)."""
    return (
        os.environ.get("STREAMLIT_EBIRD_TAXONOMY_LOCALE", "").strip()
        or os.environ.get("EBIRD_TAXONOMY_LOCALE", "").strip()
    )


def _ensure_streamlit_map_basemap_height_keys() -> None:
    """Seed basemap + map height in session state (keyed widgets; refs #70)."""
    if "streamlit_map_basemap" not in st.session_state:
        st.session_state.streamlit_map_basemap = MAP_BASEMAP_DEFAULT
    elif st.session_state.streamlit_map_basemap not in MAP_BASEMAP_OPTIONS:
        st.session_state.streamlit_map_basemap = MAP_BASEMAP_DEFAULT
    if "streamlit_map_height_px" not in st.session_state:
        st.session_state.streamlit_map_height_px = MAP_HEIGHT_PX_DEFAULT


def _sidebar_footer_links() -> None:
    """Small centred sidebar footer: GitHub, eBird, Instagram — text links only (icons dropped; narrow sidebar)."""
    st.sidebar.divider()
    link_style = 'color:#868e96;text-decoration:none;'
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
        "</div>",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _cached_checklist_stats_payload(df: pd.DataFrame) -> ChecklistStatsPayload | None:
    """Structured checklist stats for the Checklist Statistics tab (refs #68)."""
    return compute_checklist_stats_payload(df, CHECKLIST_STATS_TOP_N_TABLE_LIMIT)


@st.cache_data(show_spinner=False)
def _cached_sex_notation_by_year(df: pd.DataFrame) -> dict:
    """Sex-notation maintenance scan on full export (refs #79)."""
    from personal_ebird_explorer.stats import get_sex_notation_by_year

    return get_sex_notation_by_year(df)


def _full_location_data_for_maintenance(df: pd.DataFrame) -> pd.DataFrame:
    """Unique locations for map maintenance (same columns as notebook ``full_location_data``)."""
    cols = ["Location ID", "Location", "Latitude", "Longitude"]
    if not all(c in df.columns for c in cols):
        return pd.DataFrame(columns=cols)
    return df[cols].drop_duplicates()


@st.cache_resource(show_spinner="Loading eBird taxonomy…")
def _cached_species_url_fn(locale_key: str) -> Callable[[str], str | None]:
    """One taxonomy fetch per session per locale; used for species links in map UI."""
    from personal_ebird_explorer.taxonomy import get_species_url, load_taxonomy

    loc = locale_key.strip() if locale_key and locale_key.strip() else None
    if load_taxonomy(locale=loc):
        return get_species_url
    return lambda _: None


@st.fragment
def _species_searchbox_fragment() -> None:
    """Whoosh-backed search; fragment-scoped reruns avoid greying the whole app (refs #70)."""
    try:
        from streamlit_searchbox import st_searchbox
    except ImportError:
        st.error(
            "Missing **streamlit-searchbox**. Install with: "
            "`pip install -r requirements-streamlit.txt` (refs #70)."
        )
        return
    ix = st.session_state.get(_SESSION_SPECIES_IX_KEY)
    if ix is None:
        return
    persisted = st.session_state.get(_PERSIST_SPECIES_COMMON_KEY)

    def _search(term: str) -> list:
        return whoosh_species_suggestions(
            ix,
            term,
            max_options=SPECIES_SEARCH_MAX_OPTIONS,
            min_query_len=SPECIES_SEARCH_MIN_QUERY_LEN,
        )

    def _on_species_submit(selected: Any) -> None:
        """Library does not rerun the full app on submit; the map lives outside this fragment."""
        st.session_state[_SESSION_SPECIES_PICK_KEY] = selected
        st.rerun()

    def _on_species_reset() -> None:
        st.session_state.pop(_SESSION_SPECIES_PICK_KEY, None)
        st.rerun()

    pick = st_searchbox(
        _search,
        key=_SESSION_SPECIES_SEARCH_KEY,
        placeholder=SPECIES_SEARCH_PLACEHOLDER,
        label="Species",
        default=persisted,
        default_searchterm=persisted or "",
        debounce=SPECIES_SEARCH_DEBOUNCE_MS,
        edit_after_submit=SPECIES_SEARCH_EDIT_AFTER_SUBMIT,
        rerun_scope=SPECIES_SEARCH_RERUN_SCOPE,
        submit_function=_on_species_submit,
        reset_function=_on_species_reset,
    )
    st.session_state[_SESSION_SPECIES_PICK_KEY] = pick


def _load_dataframe(
    *,
    uploaded: Any | None = None,
    upload_cache: tuple[bytes, str] | None = None,
) -> tuple[pd.DataFrame | None, str | None, str | None, str | None, str | None]:
    """
    Return ``(df, provenance_html, source_label, data_abs_path, data_basename)``.

    *data_abs_path* is set only for on-disk resolution (``None`` for landing / session upload).
    *data_basename* is the CSV file name for display.
    """
    if uploaded is not None:
        try:
            raw = uploaded.getvalue()
            df = load_dataset(io.BytesIO(raw))
            name = uploaded.name
            return df, f"Upload: **{name}**", None, None, name
        except Exception as e:
            st.error(f"Could not load CSV: {e}")
            return None, None, None, None, None

    try:
        folders, sources = build_explorer_candidate_dirs(
            repo_root=_REPO_ROOT,
            cwd=os.getcwd(),
        )
        path, _folder, src = resolve_ebird_data_file(DEFAULT_EBIRD_FILENAME, folders, sources)
        df = load_dataset(path)
        label = src.replace("_", " ").title()
        base = os.path.basename(path)
        return df, f"Disk: `{path}` (_{label}_)", src, path, base
    except FileNotFoundError:
        pass

    if upload_cache is not None:
        raw, name = upload_cache
        try:
            df = load_dataset(io.BytesIO(raw))
            return df, f"Upload: **{name}**", None, None, name
        except Exception as e:
            st.error(f"Could not load CSV: {e}")
            return None, None, None, None, None

    return None, None, None, None, None


def _settings_data_path_html(
    *,
    data_basename: str | None,
    data_abs_path: str | None,
    source_label: str | None,
    repo_root: str,
) -> str:
    """Read-only Settings block: file name, optional disk path, loaded-by category."""
    if not data_basename:
        return (
            '<div class="ebird-data-path-block">'
            "<p><em>No dataset loaded in this session.</em></p>"
            "</div>"
        )
    esc_name = html.escape(data_basename, quote=False)
    rows: list[str] = [
        f'<p><strong>Data file name:</strong> <code>{esc_name}</code></p>',
    ]
    if data_abs_path:
        esc_path = html.escape(data_abs_path, quote=False)
        rows.append(f'<p><strong>Data file path:</strong> <code>{esc_path}</code></p>')

    if not (source_label and str(source_label).strip()):
        loaded_by = "Landing page"
    elif settings_yaml_path_for_source(repo_root, source_label):
        loaded_by = "Configuration file"
    elif source_label == "cwd":
        loaded_by = "Working directory"
    else:
        loaded_by = str(source_label).replace("_", " ").title()
    rows.append(
        f"<p><strong>Data file loaded by:</strong> {html.escape(loaded_by, quote=False)}</p>"
    )

    return f'<div class="ebird-data-path-block">{"".join(rows)}</div>'


def _settings_taxonomy_help_html() -> str:
    """Settings → Taxonomy: short copy + link to eBird help (locale codes; no API key)."""
    p1 = html.escape(
        "Used for species names in links, tables, popups and elsewhere. "
        "Update based on the locale of input data.",
        quote=False,
    )
    help_url = (
        "https://support.ebird.org/en/support/solutions/articles/48000804865-bird-names-in-ebird"
    )
    p2 = (
        "Match the language and region you use for common names in "
        "<strong>My eBird → Preferences</strong> "
        f"(e.g. English (Australia) → <code>en_AU</code>). "
        "This field is the same eBird <strong>locale</strong> code the "
        "taxonomy API accepts for common-name spellings. "
        f'<a href="{help_url}" target="_blank" rel="noopener noreferrer">'
        f"{html.escape('Bird names in eBird', quote=False)}</a>"
        " — how regional names are chosen."
    )
    return (
        '<div class="ebird-settings-section-copy">'
        f"<p>{p1}</p>"
        f'<p style="margin:0.65rem 0 0 0;">{p2}</p>'
        "</div>"
    )


def main() -> None:
    st.set_page_config(page_title="Personal eBird Explorer (Streamlit)", layout="wide")

    if "streamlit_taxonomy_locale" not in st.session_state:
        st.session_state.streamlit_taxonomy_locale = _env_taxonomy_locale() or DEFAULT_TAXONOMY_LOCALE
    if "streamlit_country_tab_sort" not in st.session_state:
        st.session_state.streamlit_country_tab_sort = COUNTRY_TAB_SORT_ALPHABETICAL

    upload_cache = st.session_state.get(_SESSION_UPLOAD_CACHE_KEY)
    if upload_cache is not None and not (
        isinstance(upload_cache, tuple) and len(upload_cache) == 2 and isinstance(upload_cache[0], bytes)
    ):
        upload_cache = None

    df_full, provenance, source_label, data_abs_path, data_basename = _load_dataframe(
        uploaded=None, upload_cache=upload_cache
    )

    if df_full is not None and provenance and "Disk:" in provenance:
        # Drop stale session upload when disk resolution wins (local path after a prior Cloud upload).
        st.session_state.pop(_SESSION_UPLOAD_CACHE_KEY, None)

    if df_full is None:
        # Keyed container: on the post-upload rerun this block is skipped entirely, so Cloud/Streamlit
        # can drop the whole landing subtree instead of leaving orphan markdown under tabs.
        with st.container(key="ebird_landing_main"):
            st.title("Personal eBird Explorer")
            st.subheader("Streamlit prototype")
            st.markdown("Upload your **My eBird Data** CSV to open the map and tabs.")
            uploaded = st.file_uploader(
                "eBird export (CSV)",
                type=["csv"],
                key="ebird_landing_csv_uploader",
                help="Official eBird full data export (CSV).",
            )
            if uploaded is not None:
                df_full, provenance, source_label, data_abs_path, data_basename = _load_dataframe(
                    uploaded=uploaded, upload_cache=None
                )
                if df_full is not None:
                    st.session_state[_SESSION_UPLOAD_CACHE_KEY] = (uploaded.getvalue(), uploaded.name)
                    # Landing widgets already ran above in this run; rerun loads from cache and skips this block.
                    st.rerun()

            if df_full is None:
                st.markdown(
                    """
**From eBird**

1. Sign in: [Download My Data](https://ebird.org/downloadMyData)
2. Under **My eBird Observations**, use **Request My Observations**.
3. A link to your data will be sent to your email address (often a few minutes; sometimes longer).
4. Open the email, download the **.zip** and unzip it.
5. Upload the CSV here (in English the file name should be **MyEBirdData.csv**).
                    """
                )
                st.caption(
                    "Species links default to **en_AU**; change locale under **Settings → Taxonomy** after load. "
                    "Data still loads if names don’t match.\n\n"
                    "This page is skipped when a CSV is already found on disk (local config path). "
                    "Support for local files works when Streamlit is running locally; see the code repo for more information. "
                    "Proper instructions will appear here in future releases."
                )
        _sidebar_footer_links()
        if df_full is None:
            return

    st.session_state[_SETTINGS_CONFIG_SOURCE_KEY] = source_label or ""
    settings_yaml_path = settings_yaml_path_for_source(_REPO_ROOT, source_label or "")
    st.session_state[_SETTINGS_CONFIG_PATH_KEY] = settings_yaml_path or ""
    if settings_yaml_path and st.session_state.get(_SETTINGS_LOADED_FROM_KEY) != settings_yaml_path:
        cfg_data, cfg_warn = _load_settings_yaml_via_module(settings_yaml_path)
        if cfg_warn and not st.session_state.get(_SETTINGS_WARNED_KEY):
            st.warning(cfg_warn)
            st.session_state[_SETTINGS_WARNED_KEY] = True
        _apply_settings_payload_to_state(cfg_data)
        st.session_state[_SETTINGS_LOADED_FROM_KEY] = settings_yaml_path
        st.session_state[_SETTINGS_BASELINE_KEY] = _settings_state_payload()

    _init_and_clamp_streamlit_table_settings()
    if _SETTINGS_BASELINE_KEY not in st.session_state:
        st.session_state[_SETTINGS_BASELINE_KEY] = _settings_state_payload()

    if "popup_html_cache" not in st.session_state:
        st.session_state.popup_html_cache = {}
    if "filtered_by_loc_cache" not in st.session_state:
        st.session_state.filtered_by_loc_cache = OrderedDict()

    _ensure_streamlit_map_basemap_height_keys()

    with st.sidebar:
        st.header("Map")

        map_view_label = st.selectbox(
            "Map view",
            list(MAP_VIEW_LABELS),
            key="streamlit_map_view_label",
        )
        map_view_mode = _MAP_VIEW_LABEL_TO_MODE[map_view_label]
        is_lifer_view = map_view_mode == "lifers"

        st.markdown("**Date**")
        if is_lifer_view:
            st.caption("Lifer locations is not date-filtered.")
            if st.session_state.get(_PERSIST_MAP_DATE_FILTER_KEY, MAP_DATE_FILTER_DEFAULT):
                st.caption("Your date filter is preserved for other map views.")
            date_filter_on_effective = False
            date_range_sel: tuple | None = None
        else:
            # Restore widget keys after Lifer view (those widgets were not rendered, keys may be missing).
            if "streamlit_map_date_filter" not in st.session_state:
                st.session_state.streamlit_map_date_filter = bool(
                    st.session_state.get(_PERSIST_MAP_DATE_FILTER_KEY, MAP_DATE_FILTER_DEFAULT)
                )
            if st.session_state.get("streamlit_map_date_filter", False):
                if "streamlit_map_date_range" not in st.session_state:
                    pr = st.session_state.get(_PERSIST_MAP_DATE_RANGE_KEY)
                    if isinstance(pr, tuple) and len(pr) == 2:
                        st.session_state.streamlit_map_date_range = pr
                    else:
                        a, b = date_inception_to_today_default(df_full)
                        st.session_state.streamlit_map_date_range = (a, b)

            date_filter_on_effective = st.toggle(
                "Date filter",
                key="streamlit_map_date_filter",
                help="Turn on to limit the map and checklist stats to a date range.",
            )
            if not date_filter_on_effective:
                date_range_sel = None
            else:
                d_inception, today = date_inception_to_today_default(df_full)
                if "streamlit_map_date_range" not in st.session_state:
                    st.session_state.streamlit_map_date_range = (d_inception, today)
                rng = st.session_state["streamlit_map_date_range"]
                if not isinstance(rng, tuple) or len(rng) != 2:
                    st.session_state.streamlit_map_date_range = (d_inception, today)
                else:
                    r0 = max(min(rng[0], today), d_inception)
                    r1 = max(min(rng[1], today), d_inception)
                    rng_val = (r0, r1) if r0 <= r1 else (r1, r0)
                    if rng_val != rng:
                        st.session_state.streamlit_map_date_range = rng_val
                dr = st.date_input(
                    "Date range",
                    min_value=d_inception,
                    max_value=today,
                    key="streamlit_map_date_range",
                )
                if isinstance(dr, tuple) and len(dr) == 2:
                    date_range_sel = (dr[0], dr[1])
                else:
                    date_range_sel = (d_inception, today)

            st.session_state[_PERSIST_MAP_DATE_FILTER_KEY] = date_filter_on_effective
            if date_filter_on_effective and date_range_sel is not None:
                st.session_state[_PERSIST_MAP_DATE_RANGE_KEY] = date_range_sel

    ws, date_filter_banner = streamlit_working_set_and_status(
        df_full,
        map_view_mode=map_view_mode,
        date_filter_on=date_filter_on_effective,
        date_range=date_range_sel,
        map_caches=(st.session_state.popup_html_cache, st.session_state.filtered_by_loc_cache),
    )
    if ws is None:
        st.error("Invalid date range. Using all-time data for this run.")
        ws, date_filter_banner = streamlit_working_set_and_status(
            df_full,
            map_view_mode=map_view_mode,
            date_filter_on=False,
            date_range=None,
            map_caches=(st.session_state.popup_html_cache, st.session_state.filtered_by_loc_cache),
        )
    work_df = ws.df

    hide_non_matching_locations = False
    species_pick_common: str | None = None
    species_pick_sci = ""

    _prev_mv = st.session_state.get(_SESSION_PREV_MAP_VIEW_KEY)
    if map_view_mode == "species" and _prev_mv is not None and _prev_mv != "species":
        st.session_state.pop(_SESSION_SPECIES_SEARCH_KEY, None)

    if map_view_mode == "species":
        _ix_sig = (len(ws.species_list), st.session_state.get("ebird_data_sig"))
        if st.session_state.get(_SESSION_SPECIES_IX_SIG_KEY) != _ix_sig:
            st.session_state[_SESSION_SPECIES_IX_KEY] = build_ram_species_whoosh_index(
                ws.species_list, ws.name_map
            )
            st.session_state[_SESSION_SPECIES_IX_SIG_KEY] = _ix_sig
        st.session_state[_SESSION_SPECIES_WS_KEY] = ws

        with st.sidebar:
            st.markdown("**Species**")
            st.caption(SPECIES_SEARCH_CAPTION)
            _species_searchbox_fragment()
            hide_non_matching_locations = st.toggle(
                "Show only selected species",
                key="streamlit_species_hide_only",
                help=(
                    "When off, all locations are shown with your species highlighted. "
                    "When on, only locations where you recorded the species."
                ),
            )

        species_pick_common = st.session_state.get(_SESSION_SPECIES_PICK_KEY)
        if species_pick_common:
            species_pick_sci = str(ws.name_map.get(species_pick_common, "") or "")
            st.session_state[_PERSIST_SPECIES_COMMON_KEY] = species_pick_common
            st.session_state[_PERSIST_SPECIES_SCI_KEY] = species_pick_sci
        else:
            st.session_state.pop(_PERSIST_SPECIES_COMMON_KEY, None)
            st.session_state.pop(_PERSIST_SPECIES_SCI_KEY, None)
    else:
        st.session_state.pop(_SESSION_SPECIES_PICK_KEY, None)

    with st.sidebar:
        st.divider()
        map_style = st.selectbox(
            "Basemap",
            options=list(MAP_BASEMAP_OPTIONS),
            key="streamlit_map_basemap",
        )
        st.markdown(
            '<div style="height:0.65rem" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        map_height = st.slider(
            "Map height (px)",
            min_value=MAP_HEIGHT_PX_MIN,
            max_value=MAP_HEIGHT_PX_MAX,
            step=MAP_HEIGHT_PX_STEP,
            key="streamlit_map_height_px",
        )

    st.session_state[_SESSION_PREV_MAP_VIEW_KEY] = map_view_mode

    tax_locale_effective = (st.session_state.streamlit_taxonomy_locale.strip() or DEFAULT_TAXONOMY_LOCALE)
    species_url_fn = _cached_species_url_fn(tax_locale_effective)
    popup_sort_order = st.session_state.streamlit_popup_sort_order
    popup_scroll_hint = st.session_state.streamlit_popup_scroll_hint
    mark_lifer = bool(st.session_state.streamlit_mark_lifer)
    mark_last_seen = bool(st.session_state.streamlit_mark_last_seen)

    _inject_spinner_theme_css()

    st.title("Personal eBird Explorer — Streamlit prototype")

    (
        tab_map,
        tab_checklist,
        tab_rankings,
        tab_yearly,
        tab_country,
        tab_maint,
        tab_settings,
    ) = st.tabs(NOTEBOOK_MAIN_TAB_LABELS)

    with st.spinner(CHECKLIST_STATS_SPINNER_MESSAGE):
        checklist_payload = _cached_checklist_stats_payload(work_df)
        maint_full_payload = _cached_checklist_stats_payload(df_full)
        sex_notation_by_year = _cached_sex_notation_by_year(df_full)

    with tab_map:
        prov_plain = provenance or ""
        sig = data_signature_for_caches(df_full, prov_plain)
        if st.session_state.get("ebird_data_sig") != sig:
            st.session_state.ebird_data_sig = sig
            st.session_state.popup_html_cache = {}
            st.session_state.filtered_by_loc_cache = OrderedDict()
            st.session_state.pop(_FOLIUM_STATIC_MAP_CACHE_KEY, None)

        try:
            ctx = prepare_all_locations_map_context(work_df, full_df=df_full)
        except ValueError as e:
            st.warning(str(e))
            st.session_state.pop("_explorer_map_html_bytes", None)
        else:
            overlay_common = (
                (species_pick_common or "").strip() if map_view_mode == "species" else ""
            )
            overlay_sci = (
                (species_pick_sci or "").strip() if map_view_mode == "species" else ""
            )
            hide_nm = (
                map_view_mode == "species"
                and bool(overlay_sci)
                and hide_non_matching_locations
            )
            _map_kw = {
                **ctx,
                "selected_species": overlay_sci,
                "selected_common_name": overlay_common,
                "map_style": map_style,
                "popup_sort_order": popup_sort_order,
                "popup_scroll_hint": popup_scroll_hint,
                "lifer_color": st.session_state.streamlit_lifer_color,
                "lifer_fill": st.session_state.streamlit_lifer_fill,
                "last_seen_color": st.session_state.streamlit_last_seen_color,
                "last_seen_fill": st.session_state.streamlit_last_seen_fill,
                "species_color": st.session_state.streamlit_species_color,
                "species_fill": st.session_state.streamlit_species_fill,
                "default_color": st.session_state.streamlit_default_color,
                "default_fill": st.session_state.streamlit_default_fill,
                "mark_lifer": mark_lifer,
                "mark_last_seen": mark_last_seen,
                "date_filter_status": date_filter_banner,
                "species_url_fn": species_url_fn,
                "base_species_fn": base_species_for_lifer,
                "taxonomy_locale": tax_locale_effective,
                "popup_html_cache": st.session_state.popup_html_cache,
                "filtered_by_loc_cache": st.session_state.filtered_by_loc_cache,
                "map_view_mode": map_view_mode,
                "hide_non_matching_locations": hide_nm,
            }
            _render_opts_sig = (
                popup_sort_order,
                popup_scroll_hint,
                st.session_state.streamlit_lifer_color,
                st.session_state.streamlit_lifer_fill,
                st.session_state.streamlit_last_seen_color,
                st.session_state.streamlit_last_seen_fill,
                st.session_state.streamlit_species_color,
                st.session_state.streamlit_species_fill,
                st.session_state.streamlit_default_color,
                st.session_state.streamlit_default_fill,
                mark_lifer,
                mark_last_seen,
            )
            _ck = _static_map_cache_key(
                work_df,
                map_view_mode,
                date_filter_banner,
                map_style,
                _render_opts_sig,
                taxonomy_locale=tax_locale_effective,
            )
            _use_static_cache = map_view_mode in ("all", "lifers")
            _cached = (
                st.session_state.get(_FOLIUM_STATIC_MAP_CACHE_KEY) if _use_static_cache else None
            )
            if (
                _use_static_cache
                and isinstance(_cached, dict)
                and _cached.get("key") == _ck
                and _cached.get("map") is not None
            ):
                result_map = _cached["map"]
                result_warning = _cached.get("warning")
            else:
                result = build_species_overlay_map(**_map_kw)
                result_map = result.map
                result_warning = result.warning
                if _use_static_cache and result_map is not None:
                    st.session_state[_FOLIUM_STATIC_MAP_CACHE_KEY] = {
                        "key": _ck,
                        "map": result_map,
                        "warning": result_warning,
                    }

            if result_warning:
                st.warning(result_warning)
                st.session_state.pop("_explorer_map_html_bytes", None)
            elif result_map is None:
                st.warning("Map could not be built.")
                st.session_state.pop("_explorer_map_html_bytes", None)
            else:
                st.session_state["_explorer_map_html_bytes"] = folium_map_to_html_bytes(result_map)
                try:
                    from streamlit_folium import st_folium
                except ImportError:
                    st.error(
                        "Missing **streamlit-folium** (needed to embed the Folium map). "
                        "Locally: `pip install -r requirements-streamlit.txt`. "
                        "**Streamlit Community Cloud:** set app **Python requirements** to "
                        "`requirements-streamlit.txt` or `streamlit_app/requirements.txt` "
                        "(not the repo root `requirements.txt`)."
                    )
                    st.stop()
                st_folium(
                    result_map,
                    use_container_width=True,
                    height=map_height,
                    key=f"explorer_folium_map_h{map_height}",
                    returned_objects=[],
                    return_on_hover=False,
                )

    with tab_checklist:
        if checklist_payload is not None:
            render_checklist_stats_streamlit_html(checklist_payload)
        else:
            st.warning("No checklist data to show.")

    with tab_rankings:
        if df_full is None or df_full.empty:
            st.info("Load checklist data to use Rankings & lists.")
        else:
            render_rankings_streamlit_tab(
                df_full,
                country_sort=st.session_state.streamlit_country_tab_sort,
                taxonomy_locale=tax_locale_effective,
            )

    with tab_yearly:
        sync_yearly_summary_session_inputs(checklist_payload)
        run_yearly_summary_streamlit_fragment()

    with tab_country:
        if checklist_payload is not None:
            sync_country_tab_session_inputs(checklist_payload)
            run_country_tab_streamlit_fragment()
        else:
            st.warning("No checklist data to show.")

    with tab_maint:
        loc_maint = _full_location_data_for_maintenance(df_full)
        incomplete_maint: dict = {}
        if maint_full_payload is not None:
            incomplete_maint = maint_full_payload.incomplete_by_year or {}
        render_maintenance_streamlit_tab(
            loc_maint,
            close_location_meters=int(st.session_state.streamlit_close_location_meters),
            incomplete_by_year=incomplete_maint,
            sex_notation_by_year=sex_notation_by_year,
            species_url_fn=species_url_fn,
        )

    with tab_settings:
        st.markdown(_SETTINGS_PANEL_CSS, unsafe_allow_html=True)
        with st.container(key="ebird_settings_panel"):
            settings_yaml_path = st.session_state.get(_SETTINGS_CONFIG_PATH_KEY, "") or ""
            settings_module_ready = _settings_config_module_available()
            can_save_settings = bool(settings_yaml_path) and settings_module_ready

            if can_save_settings:
                b1, b2 = st.columns(2)
                with b1:
                    if st.button(
                        "Save settings",
                        key="streamlit_save_settings_btn",
                        use_container_width=True,
                    ):
                        ok, err = _write_settings_yaml_via_module(
                            settings_yaml_path, _settings_state_payload()
                        )
                        if ok:
                            st.session_state[_SETTINGS_BASELINE_KEY] = _settings_state_payload()
                            st.session_state[_SETTINGS_FLASH_SAVE_KEY] = True
                        else:
                            st.error(err or "Failed to save settings.")
                with b2:
                    if st.button(
                        "Reset to defaults",
                        key="streamlit_reset_settings_btn",
                        use_container_width=True,
                    ):
                        _apply_settings_payload_to_state(_settings_defaults_payload())
                        _init_and_clamp_streamlit_table_settings()
                        st.session_state[_SETTINGS_FLASH_RESET_KEY] = True

                _settings_persistence_flash_banners()
                st.caption(
                    "Settings apply immediately in-session. Save writes your preferences to your "
                    "configuration file."
                )
                st.caption(f"Configuration file: {settings_yaml_path}")

            st.divider()
            st.subheader("Map display")
            st.toggle("Mark lifer", key="streamlit_mark_lifer")
            st.toggle("Mark last-seen", key="streamlit_mark_last_seen")
            st.selectbox(
                "Popup sort order",
                options=["ascending", "descending"],
                key="streamlit_popup_sort_order",
            )
            st.selectbox(
                "Popup scroll hint",
                options=["shading", "chevron", "both"],
                key="streamlit_popup_scroll_hint",
            )
            st.caption("Pin colors")
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox("Default edge", MAP_PIN_COLOUR_ALLOWLIST, key="streamlit_default_color")
                st.selectbox("Species edge", MAP_PIN_COLOUR_ALLOWLIST, key="streamlit_species_color")
                st.selectbox("Lifer edge", MAP_PIN_COLOUR_ALLOWLIST, key="streamlit_lifer_color")
                st.selectbox("Last-seen edge", MAP_PIN_COLOUR_ALLOWLIST, key="streamlit_last_seen_color")
            with c2:
                st.selectbox("Default fill", MAP_PIN_COLOUR_ALLOWLIST, key="streamlit_default_fill")
                st.selectbox("Species fill", MAP_PIN_COLOUR_ALLOWLIST, key="streamlit_species_fill")
                st.selectbox("Lifer fill", MAP_PIN_COLOUR_ALLOWLIST, key="streamlit_lifer_fill")
                st.selectbox("Last-seen fill", MAP_PIN_COLOUR_ALLOWLIST, key="streamlit_last_seen_fill")

            st.divider()
            st.subheader("Tables & lists")
            # Sliders feed Rankings & lists / Yearly Summary / Country sparse-year UI (shared formatters).
            st.slider(
                "Ranking tables: number of results",
                min_value=TABLES_RANKINGS_TOP_N_MIN,
                max_value=TABLES_RANKINGS_TOP_N_MAX,
                step=1,
                key="streamlit_rankings_top_n",
            )
            st.slider(
                "Ranking tables: visible rows",
                min_value=TABLES_RANKINGS_VISIBLE_ROWS_MIN,
                max_value=TABLES_RANKINGS_VISIBLE_ROWS_MAX,
                step=1,
                key="streamlit_rankings_visible_rows",
            )
            st.slider(
                "Yearly tables: recent year columns",
                min_value=YEARLY_RECENT_COLUMN_COUNT_MIN,
                max_value=YEARLY_RECENT_COLUMN_COUNT_MAX,
                step=1,
                key="streamlit_yearly_recent_column_count",
            )
            st.selectbox(
                "Country ordering",
                options=[
                    COUNTRY_TAB_SORT_ALPHABETICAL,
                    COUNTRY_TAB_SORT_LIFERS_WORLD,
                    COUNTRY_TAB_SORT_TOTAL_SPECIES,
                ],
                format_func=lambda k: _COUNTRY_SORT_LABELS[k],
                key="streamlit_country_tab_sort",
            )
            st.divider()
            st.subheader("Maintenance")
            st.slider(
                "Close location (m)",
                min_value=MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
                max_value=MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
                step=1,
                key="streamlit_close_location_meters",
                help=(
                    "Locations within this distance (metres), excluding exact duplicate coordinates, "
                    "are listed under **Maintenance → Location Maintenance → Close locations**."
                ),
            )
            st.divider()
            st.subheader("Taxonomy")
            st.text_input(
                "Taxonomy locale",
                key="streamlit_taxonomy_locale",
            )
            st.markdown(_settings_taxonomy_help_html(), unsafe_allow_html=True)
            st.divider()
            st.subheader("Data & path")
            st.caption("Read-only details for this session (useful when troubleshooting).")
            st.markdown(
                _settings_data_path_html(
                    data_basename=data_basename,
                    data_abs_path=data_abs_path,
                    source_label=source_label,
                    repo_root=_REPO_ROOT,
                ),
                unsafe_allow_html=True,
            )

    if st.session_state.get("_explorer_map_html_bytes"):
        with st.sidebar:
            st.divider()
            st.download_button(
                "Export map HTML",
                data=st.session_state["_explorer_map_html_bytes"],
                file_name=MAP_EXPORT_HTML_FILENAME,
                mime="text/html",
                key="export_map_html_btn",
                help="Standalone HTML for the current map (notebook-style export).",
            )

    _sidebar_footer_links()


if __name__ == "__main__":
    main()

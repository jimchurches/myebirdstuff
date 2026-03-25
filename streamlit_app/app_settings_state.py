"""YAML-backed Settings tab: session payload, save/load, clamping, helper HTML (refs #98)."""

from __future__ import annotations

import html
import os
from typing import Any

import streamlit as st

from personal_ebird_explorer.checklist_stats_display import COUNTRY_TAB_SORT_ALPHABETICAL
from personal_ebird_explorer.explorer_paths import settings_yaml_path_for_source
from streamlit_app.app_constants import (
    DEFAULT_CLOSE_LOCATION_METERS,
    DEFAULT_TAXONOMY_LOCALE,
    SETTINGS_FLASH_RESET_KEY,
    SETTINGS_FLASH_SAVE_KEY,
)
from streamlit_app.defaults import (
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
    MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
    MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
    SETTINGS_SCHEMA_VERSION,
    TABLES_RANKINGS_TOP_N_DEFAULT,
    TABLES_RANKINGS_TOP_N_MAX,
    TABLES_RANKINGS_TOP_N_MIN,
    TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT,
    TABLES_RANKINGS_VISIBLE_ROWS_MAX,
    TABLES_RANKINGS_VISIBLE_ROWS_MIN,
    YEARLY_RECENT_COLUMN_COUNT_DEFAULT,
    YEARLY_RECENT_COLUMN_COUNT_MAX,
    YEARLY_RECENT_COLUMN_COUNT_MIN,
    build_persisted_settings_defaults_dict,
)


def env_taxonomy_locale() -> str:
    """Non-empty locale from env if set (notebook parity)."""
    return (
        os.environ.get("STREAMLIT_EBIRD_TAXONOMY_LOCALE", "").strip()
        or os.environ.get("EBIRD_TAXONOMY_LOCALE", "").strip()
    )


def settings_persistence_flash_banners() -> None:
    """Full-width save/reset notices using theme greens (same style for both)."""
    if st.session_state.pop(SETTINGS_FLASH_SAVE_KEY, False):
        st.markdown(
            '<div class="ebird-settings-persistence-banner">'
            "<strong>Saved.</strong> Preferences written to your configuration file."
            "</div>",
            unsafe_allow_html=True,
        )
    if st.session_state.pop(SETTINGS_FLASH_RESET_KEY, False):
        st.markdown(
            '<div class="ebird-settings-persistence-banner">'
            "<strong>Defaults restored for this session.</strong> "
            "Click <strong>Save settings</strong> to persist."
            "</div>",
            unsafe_allow_html=True,
        )


def init_and_clamp_streamlit_table_settings() -> None:
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


def settings_state_payload() -> dict[str, Any]:
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


def apply_settings_payload_to_state(cfg: dict[str, Any]) -> None:
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


def settings_defaults_payload() -> dict[str, Any]:
    """Built-in defaults; used when config module/deps are unavailable."""
    return build_persisted_settings_defaults_dict()


def load_settings_yaml_via_module(path: str) -> tuple[dict[str, Any], str | None]:
    try:
        from personal_ebird_explorer.streamlit_settings_config import load_settings_from_python_config
    except Exception as e:
        return settings_defaults_payload(), f"Settings validation unavailable ({e}); using defaults."
    return load_settings_from_python_config(path)


def write_settings_yaml_via_module(path: str, payload: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        from personal_ebird_explorer.streamlit_settings_config import write_sparse_settings_to_python_config
    except Exception as e:
        return False, f"Settings save unavailable ({e}). Install requirements-streamlit.txt."
    return write_sparse_settings_to_python_config(path, payload)


def settings_config_module_available() -> bool:
    try:
        import personal_ebird_explorer.streamlit_settings_config  # noqa: F401
    except Exception:
        return False
    return True


def settings_data_path_html(
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


def settings_taxonomy_help_html() -> str:
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

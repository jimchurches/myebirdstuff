"""YAML-backed settings model for Streamlit explorer UI (refs #70)."""

from __future__ import annotations

import importlib.util
import os
import re
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from personal_ebird_explorer.checklist_stats_display import COUNTRY_TAB_SORT_ALPHABETICAL
from personal_ebird_explorer.settings_schema_defaults import (
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


class MapDisplayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    popup_sort_order: str = Field(
        default=MAP_POPUP_SORT_ORDER_DEFAULT, pattern="^(ascending|descending)$"
    )
    popup_scroll_hint: str = Field(
        default=MAP_POPUP_SCROLL_HINT_DEFAULT, pattern="^(chevron|shading|both)$"
    )
    mark_lifer: bool = MAP_MARK_LIFER_DEFAULT
    mark_last_seen: bool = MAP_MARK_LAST_SEEN_DEFAULT
    default_color: str = Field(default=MAP_DEFAULT_COLOR_DEFAULT)
    default_fill: str = Field(default=MAP_DEFAULT_FILL_DEFAULT)
    species_color: str = Field(default=MAP_SPECIES_COLOR_DEFAULT)
    species_fill: str = Field(default=MAP_SPECIES_FILL_DEFAULT)
    lifer_color: str = Field(default=MAP_LIFER_COLOR_DEFAULT)
    lifer_fill: str = Field(default=MAP_LIFER_FILL_DEFAULT)
    last_seen_color: str = Field(default=MAP_LAST_SEEN_COLOR_DEFAULT)
    last_seen_fill: str = Field(default=MAP_LAST_SEEN_FILL_DEFAULT)


class TablesListsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rankings_top_n: int = Field(
        default=TABLES_RANKINGS_TOP_N_DEFAULT, ge=TABLES_RANKINGS_TOP_N_MIN, le=TABLES_RANKINGS_TOP_N_MAX
    )
    rankings_visible_rows: int = Field(
        default=TABLES_RANKINGS_VISIBLE_ROWS_DEFAULT,
        ge=TABLES_RANKINGS_VISIBLE_ROWS_MIN,
        le=TABLES_RANKINGS_VISIBLE_ROWS_MAX,
    )
    high_count_sort: str = Field(
        default=TABLES_HIGH_COUNT_SORT_DEFAULT,
        pattern="^(total_count|alphabetical)$",
    )
    high_count_tie_break: str = Field(
        default=TABLES_HIGH_COUNT_TIE_BREAK_DEFAULT,
        pattern="^(first|last)$",
    )


class YearlySummaryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recent_column_count: int = Field(
        default=YEARLY_RECENT_COLUMN_COUNT_DEFAULT,
        ge=YEARLY_RECENT_COLUMN_COUNT_MIN,
        le=YEARLY_RECENT_COLUMN_COUNT_MAX,
    )


class CountryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort: str = Field(
        default=COUNTRY_TAB_SORT_ALPHABETICAL,
        pattern="^(alphabetical|lifers_world|total_species)$",
    )


class MaintenanceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    close_location_meters: int = Field(
        default=MAINTENANCE_CLOSE_LOCATION_METERS_DEFAULT,
        ge=MAINTENANCE_CLOSE_LOCATION_METERS_MIN,
        le=MAINTENANCE_CLOSE_LOCATION_METERS_MAX,
    )


class TaxonomyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: str = TAXONOMY_LOCALE_DEFAULT


class StreamlitSettingsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: int = SETTINGS_SCHEMA_VERSION
    map_display: MapDisplayConfig = Field(default_factory=MapDisplayConfig)
    tables_lists: TablesListsConfig = Field(default_factory=TablesListsConfig)
    yearly_summary: YearlySummaryConfig = Field(default_factory=YearlySummaryConfig)
    country: CountryConfig = Field(default_factory=CountryConfig)
    maintenance: MaintenanceConfig = Field(default_factory=MaintenanceConfig)
    taxonomy: TaxonomyConfig = Field(default_factory=TaxonomyConfig)


def defaults_dict() -> dict[str, Any]:
    return StreamlitSettingsConfig.model_validate(build_persisted_settings_defaults_dict()).model_dump()


def load_yaml_settings(path: str) -> tuple[dict[str, Any], str | None]:
    """Load and validate settings YAML; return defaults + warning on errors."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return defaults_dict(), None
    except OSError as e:
        return defaults_dict(), f"Could not read settings YAML: {e}"
    except yaml.YAMLError as e:
        return defaults_dict(), f"Could not parse settings YAML: {e}"

    if not isinstance(raw, dict):
        return defaults_dict(), "Settings YAML must be a mapping; using defaults."
    try:
        cfg = StreamlitSettingsConfig.model_validate(raw)
    except ValidationError as e:
        return defaults_dict(), f"Invalid settings YAML; using defaults. {e.errors()[0].get('msg', '')}"

    data = cfg.model_dump()
    # Guard user-edited colors with explicit allowlist.
    for key in (
        "default_color",
        "default_fill",
        "species_color",
        "species_fill",
        "lifer_color",
        "lifer_fill",
        "last_seen_color",
        "last_seen_fill",
    ):
        if data["map_display"][key] not in MAP_PIN_COLOUR_ALLOWLIST:
            data["map_display"][key] = defaults_dict()["map_display"][key]
    return data, None


def _sparse_diff(current: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in current.items():
        dv = defaults.get(k)
        if isinstance(v, dict) and isinstance(dv, dict):
            child = _sparse_diff(v, dv)
            if child:
                out[k] = child
        elif v != dv:
            out[k] = v
    return out


def write_sparse_yaml_settings(
    path: str,
    current: dict[str, Any],
) -> tuple[bool, str | None]:
    """Write sparse settings while preserving unknown keys in existing YAML."""
    defaults = defaults_dict()
    sparse = _sparse_diff(current, defaults)
    sparse["version"] = SETTINGS_SCHEMA_VERSION

    existing: dict[str, Any] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if isinstance(raw, dict):
            existing = raw
    except FileNotFoundError:
        existing = {}
    except (OSError, yaml.YAMLError):
        existing = {}

    # Preserve unknown keys by overlaying known sections only.
    out = dict(existing)
    for sect in (
        "version",
        "map_display",
        "tables_lists",
        "yearly_summary",
        "country",
        "maintenance",
        "taxonomy",
    ):
        if sect in sparse:
            out[sect] = sparse[sect]
        elif sect in out:
            del out[sect]
    out["version"] = SETTINGS_SCHEMA_VERSION

    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(out, f, sort_keys=False, allow_unicode=False)
    except OSError as e:
        return False, f"Could not write settings YAML: {e}"
    return True, None


_PY_SETTINGS_START = "# --- STREAMLIT_SETTINGS_YAML_START ---"
_PY_SETTINGS_END = "# --- STREAMLIT_SETTINGS_YAML_END ---"
_PY_SETTINGS_VAR = "STREAMLIT_SETTINGS_YAML"


def _load_yaml_text(yaml_text: str) -> tuple[dict[str, Any], str | None]:
    try:
        raw = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        return defaults_dict(), f"Could not parse settings YAML: {e}"
    if not isinstance(raw, dict):
        return defaults_dict(), "Settings YAML must be a mapping; using defaults."
    try:
        cfg = StreamlitSettingsConfig.model_validate(raw)
    except ValidationError as e:
        return defaults_dict(), f"Invalid settings YAML; using defaults. {e.errors()[0].get('msg', '')}"
    data = cfg.model_dump()
    for key in (
        "default_color",
        "default_fill",
        "species_color",
        "species_fill",
        "lifer_color",
        "lifer_fill",
        "last_seen_color",
        "last_seen_fill",
    ):
        if data["map_display"][key] not in MAP_PIN_COLOUR_ALLOWLIST:
            data["map_display"][key] = defaults_dict()["map_display"][key]
    return data, None


def _extract_embedded_yaml_from_py(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None
    except OSError:
        text = ""
    if text:
        pat = re.compile(
            rf"{re.escape(_PY_SETTINGS_START)}.*?{_PY_SETTINGS_VAR}\s*=\s*r?'''(.*?)'''.*?{re.escape(_PY_SETTINGS_END)}",
            re.DOTALL,
        )
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    # Backward/alternate style: read variable by importing module.
    try:
        spec = importlib.util.spec_from_file_location("streamlit_cfg_mod", path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        val = getattr(mod, _PY_SETTINGS_VAR, None)
        if isinstance(val, str) and val.strip():
            return val.strip()
    except (ImportError, SyntaxError, AttributeError, OSError):
        return None
    return None


def load_settings_from_python_config(config_py_path: str) -> tuple[dict[str, Any], str | None]:
    """Load embedded STREAMLIT_SETTINGS_YAML from ``config_secret.py`` or ``config.py`` (never from ``config_template.py``)."""
    yaml_text = _extract_embedded_yaml_from_py(config_py_path)
    if yaml_text:
        return _load_yaml_text(yaml_text)

    # Legacy migration fallback from sidecar YAML (one-time read).
    sidecar = config_py_path[:-3] + ".streamlit.yaml" if config_py_path.endswith(".py") else ""
    if sidecar and os.path.exists(sidecar):
        cfg, warn = load_yaml_settings(sidecar)
        if warn:
            return cfg, warn
        return cfg, f"Loaded legacy settings from `{os.path.basename(sidecar)}`; save to migrate into config .py."
    return defaults_dict(), None


def write_sparse_settings_to_python_config(
    config_py_path: str,
    current: dict[str, Any],
) -> tuple[bool, str | None]:
    """Write sparse YAML into STREAMLIT_SETTINGS_YAML block in config .py."""
    defaults = defaults_dict()
    sparse = _sparse_diff(current, defaults)
    sparse["version"] = SETTINGS_SCHEMA_VERSION

    existing_yaml = _extract_embedded_yaml_from_py(config_py_path)
    existing: dict[str, Any] = {}
    if existing_yaml:
        try:
            raw = yaml.safe_load(existing_yaml) or {}
            if isinstance(raw, dict):
                existing = raw
        except yaml.YAMLError:
            existing = {}

    out = dict(existing)
    for sect in (
        "version",
        "map_display",
        "tables_lists",
        "yearly_summary",
        "country",
        "maintenance",
        "taxonomy",
    ):
        if sect in sparse:
            out[sect] = sparse[sect]
        elif sect in out:
            del out[sect]
    out["version"] = SETTINGS_SCHEMA_VERSION
    yaml_text = yaml.safe_dump(out, sort_keys=False, allow_unicode=False).strip() + "\n"
    block = (
        f"{_PY_SETTINGS_START}\n"
        f"{_PY_SETTINGS_VAR} = r'''\n"
        f"{yaml_text}"
        f"'''\n"
        f"{_PY_SETTINGS_END}\n"
    )
    try:
        with open(config_py_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return False, f"Config file not found: {config_py_path}"
    except OSError as e:
        return False, f"Could not read config file: {e}"

    pat = re.compile(
        rf"{re.escape(_PY_SETTINGS_START)}.*?{re.escape(_PY_SETTINGS_END)}\n?",
        re.DOTALL,
    )
    if pat.search(text):
        new_text = pat.sub(block, text)
    else:
        new_text = text.rstrip() + "\n\n" + block

    try:
        with open(config_py_path, "w", encoding="utf-8") as f:
            f.write(new_text)
    except OSError as e:
        return False, f"Could not write config file: {e}"
    return True, None


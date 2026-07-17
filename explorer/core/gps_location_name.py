"""Resolve decimal GPS coordinates to eBird-style locality names.

**Keep in sync with** ``scripts/eBirdChecklistNameFromGPS.py`` (naming SSOT).

This module is a thin adapter: it loads the standalone GPS script and reuses its
parse / resolve / format helpers so Maintenance → Create location name from GPS and the GPS
script (UI.Vision macros) produce the same ``Locality ( lat, long )`` strings.
Do **not** fork ranking or naming rules here — change the script, then exercise
both the script offline tests and this adapter. See ``docs/AI_CONTEXT.md``.

The Google API key comes from the user's gitignored YAML only
(``config/config_secret.yaml`` then ``config/config.yaml``). Callers may pass a
session-only override when that file has no key; never commit keys.
"""

from __future__ import annotations

import importlib.util
import os
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Optional

from explorer.core.explorer_paths import _safe_load_yaml_mapping, explorer_config_dir

_GPS_SCRIPT_FILENAME = "eBirdChecklistNameFromGPS.py"
_GOOGLE_API_KEY_FIELD = "google_api_key"


@lru_cache(maxsize=1)
def _gps_script_module() -> ModuleType:
    """Load the standalone GPS script as a module (naming SSOT)."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / _GPS_SCRIPT_FILENAME
    if not script_path.is_file():
        raise RuntimeError(f"GPS naming script not found: {script_path}")
    spec = importlib.util.spec_from_file_location(
        "eBirdChecklistNameFromGPS", script_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load GPS naming script from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def google_geocode_api_key_from_yaml(repo_root: str) -> Optional[str]:
    """
    Load ``google_api_key`` from personal config YAML (gitignored).

    Search order (same idea as the GPS script):
    1. ``config/config_secret.yaml``
    2. ``config/config.yaml``

    Returns ``None`` when no usable key is present.
    """
    config_dir = explorer_config_dir(repo_root)
    for name in ("config_secret.yaml", "config.yaml"):
        raw = _safe_load_yaml_mapping(os.path.join(config_dir, name))
        value = raw.get(_GOOGLE_API_KEY_FIELD, "")
        if isinstance(value, str):
            key = value.strip()
            if key and "REPLACE_WITH" not in key:
                return key
    return None


def load_google_geocode_api_key(
    repo_root: str,
    *,
    override: Optional[str] = None,
) -> str:
    """
    Resolve the Google Geocoding API key.

    Preference order:
    1. ``override`` (session-only UI paste when YAML has no key)
    2. ``config/config_secret.yaml`` → ``google_api_key``
    3. ``config/config.yaml`` → ``google_api_key``

    Raises:
        RuntimeError: when no usable key is available.
    """
    if override is not None:
        key = str(override).strip()
        if key and "REPLACE_WITH" not in key:
            return key

    from_yaml = google_geocode_api_key_from_yaml(repo_root)
    if from_yaml:
        return from_yaml

    raise RuntimeError(
        "Google API key not configured. Set `google_api_key` in "
        "`config/config_secret.yaml` (preferred) or `config/config.yaml`, "
        "or enter the key in the Create location name from GPS expander for this session."
    )


def resolve_formatted_location_name(coord_text: str, api_key: str) -> str:
    """
    Parse coordinates, reverse-geocode, and format ``Locality ( lat, long )``.

    Matches the standalone GPS script output (without clipboard copy).

    Raises:
        ValueError: invalid or empty coordinate text.
        RuntimeError: geocode API failure or missing results path.
    """
    gps = _gps_script_module()
    lat, lng, _lat_dp, _lng_dp = gps.parse_coords_from_text(coord_text)
    name = gps.resolve_location(lat, lng, api_key=api_key)
    return gps.format_location_string(name, lat, lng, 6, 6)

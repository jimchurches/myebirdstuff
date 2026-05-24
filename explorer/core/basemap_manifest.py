"""
Load the shared basemap manifest (``explorer/data/basemaps.yaml``).

Single source of truth for allowlisted basemap keys, UI labels, and tile layer config.
Used by settings validation, Streamlit UI, HTML export, and generated frontend assets.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "data" / "basemaps.yaml"


@dataclass(frozen=True)
class BasemapEntry:
    key: str
    label: str
    url: str
    max_zoom: int
    attribution: str
    attribution_export: str
    subdomains: str | None = None


def _parse_entry(raw: dict[str, Any]) -> BasemapEntry:
    key = str(raw["key"])
    attribution = str(raw["attribution"])
    return BasemapEntry(
        key=key,
        label=str(raw["label"]),
        url=str(raw["url"]),
        max_zoom=int(raw["max_zoom"]),
        attribution=attribution,
        attribution_export=str(raw.get("attribution_export", attribution)),
        subdomains=str(raw["subdomains"]) if raw.get("subdomains") is not None else None,
    )


@lru_cache(maxsize=1)
def load_basemap_manifest() -> dict[str, Any]:
    """Parse and cache ``basemaps.yaml``."""
    data = yaml.safe_load(_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid basemap manifest: expected mapping at {_MANIFEST_PATH}")
    return data


@lru_cache(maxsize=1)
def get_basemap_entries() -> tuple[BasemapEntry, ...]:
    data = load_basemap_manifest()
    raw_list = data.get("basemaps")
    if not isinstance(raw_list, list) or not raw_list:
        raise ValueError("basemaps.yaml must define a non-empty basemaps list")
    entries = tuple(_parse_entry(item) for item in raw_list)
    keys = [e.key for e in entries]
    if len(keys) != len(set(keys)):
        raise ValueError("basemaps.yaml contains duplicate basemap keys")
    return entries


def get_basemap_default_key() -> str:
    data = load_basemap_manifest()
    default_key = str(data.get("default_key", "default"))
    keys = {e.key for e in get_basemap_entries()}
    if default_key not in keys:
        raise ValueError(f"default_key {default_key!r} is not in basemaps list")
    return default_key


MAP_BASEMAP_OPTIONS: tuple[str, ...] = tuple(e.key for e in get_basemap_entries())
MAP_BASEMAP_DEFAULT: str = get_basemap_default_key()
MAP_BASEMAP_LABELS: dict[str, str] = {e.key: e.label for e in get_basemap_entries()}


def basemap_tile_layer_for_component(entry: BasemapEntry) -> dict[str, Any]:
    """Leaflet tile layer payload for the React map component."""
    opts: dict[str, Any] = {
        "maxZoom": entry.max_zoom,
        "attribution": entry.attribution,
    }
    if entry.subdomains is not None:
        opts["subdomains"] = entry.subdomains
    return {"url": entry.url, "opts": opts}


def basemap_tile_layer_for_export(entry: BasemapEntry) -> dict[str, Any]:
    """Leaflet tile layer payload for standalone HTML export (plain attribution)."""
    opts: dict[str, Any] = {
        "maxZoom": entry.max_zoom,
        "attribution": entry.attribution_export,
    }
    if entry.subdomains is not None:
        opts["subdomains"] = entry.subdomains
    return {"url": entry.url, "opts": opts}


def basemap_tile_layers_for_component() -> dict[str, dict[str, Any]]:
    return {e.key: basemap_tile_layer_for_component(e) for e in get_basemap_entries()}


def basemap_tile_layers_for_export() -> dict[str, dict[str, Any]]:
    return {e.key: basemap_tile_layer_for_export(e) for e in get_basemap_entries()}


def basemap_tile_url_fragment(entry: BasemapEntry) -> str:
    """Stable substring used in tests to verify export HTML embeds the correct tiles."""
    url = entry.url
    for token in ("https://{s}.", "https://", "http://"):
        if url.startswith(token):
            url = url[len(token) :]
            break
    return url.split("/")[0].split("{")[0].rstrip(".")

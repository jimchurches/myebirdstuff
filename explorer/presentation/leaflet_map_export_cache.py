"""Cache-key helpers for Leaflet standalone map HTML export."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _digest_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def leaflet_export_html_cache_key(
    *,
    leaflet_revision: str,
    map_height: int,
    map_style: str,
    cluster_options: dict[str, Any],
    circle_marker_style: dict[str, Any],
    cluster_icon_style: dict[str, Any],
    viewport: dict[str, Any],
    map_theme_css: str,
    banner_html: str,
    legend_html: str,
) -> tuple[str, ...]:
    """Stable session-cache key for :func:`~explorer.presentation.leaflet_map_html_export.leaflet_map_to_html_bytes` output."""
    return (
        str(leaflet_revision),
        str(int(map_height)),
        str(map_style or "default"),
        _digest_json(cluster_options or {}),
        _digest_json(circle_marker_style or {}),
        _digest_json(cluster_icon_style or {}),
        _digest_json(viewport or {}),
        _digest_text(map_theme_css or ""),
        _digest_text(banner_html or ""),
        _digest_text(legend_html or ""),
    )

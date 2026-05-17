"""Standalone HTML export for Leaflet map component embeds (#222 §7).

Single-stack: uses the same GeoJSON + theme CSS as production, with a small vanilla JS viewer
(``static/leaflet_map_export.js``). No Folium build at export time.
"""

from __future__ import annotations

import html as html_module
import json
import re
from pathlib import Path
from typing import Any

from explorer.presentation.popup_v1_export_html import enrich_geojson_for_export

_STATIC = Path(__file__).resolve().parent / "static"
_COMPONENT_CSS = (
    Path(__file__).resolve().parents[1]
    / "components"
    / "all_locations_map"
    / "frontend"
    / "src"
    / "AllLocationsMapPopup.css"
)

_LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
_LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
_CLUSTER_CSS = "https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"
_CLUSTER_DEFAULT_CSS = (
    "https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"
)
_CLUSTER_JS = "https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"


def _read_static(name: str) -> str:
    return (_STATIC / name).read_text(encoding="utf-8")


def _extract_style_inner(css_bundle: str) -> str:
    parts = re.findall(r"<style[^>]*>(.*?)</style>", css_bundle, flags=re.DOTALL | re.IGNORECASE)
    return "\n".join(p.strip() for p in parts if p.strip())


def _json_for_script(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return raw.replace("</", "<\\/")


def leaflet_map_to_html_bytes(
    *,
    geojson: dict[str, Any],
    height: int,
    map_style: str = "default",
    cluster_options: dict[str, Any] | None = None,
    circle_marker_style: dict[str, Any] | None = None,
    cluster_icon_style: dict[str, Any] | None = None,
    viewport: dict[str, Any] | None = None,
    map_theme_css: str = "",
    banner_html: str = "",
    legend_html: str = "",
    title: str = "eBird map export",
) -> bytes:
    """Build a self-contained HTML file (network required for tiles + CDN scripts)."""
    enriched = enrich_geojson_for_export(geojson)
    config = {
        "geojson": enriched,
        "height": int(height),
        "map_style": str(map_style or "default"),
        "cluster_options": cluster_options if cluster_options is not None else {},
        "circle_marker_style": circle_marker_style if circle_marker_style is not None else {},
        "cluster_icon_style": cluster_icon_style if cluster_icon_style is not None else {},
        "viewport": viewport if viewport is not None else {},
    }
    theme_inner = _extract_style_inner(map_theme_css)
    popup_css = ""
    if _COMPONENT_CSS.is_file():
        popup_css = _COMPONENT_CSS.read_text(encoding="utf-8")
    page_css = _read_static("leaflet_map_export_page.css")
    viewer_js = _read_static("leaflet_map_export.js")
    esc_title = html_module.escape(title, quote=False)
    banner = (banner_html or "").strip()
    legend = (legend_html or "").strip()
    config_json = _json_for_script(config)

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc_title}</title>
<link rel="stylesheet" href="{_LEAFLET_CSS}"/>
<link rel="stylesheet" href="{_CLUSTER_CSS}"/>
<link rel="stylesheet" href="{_CLUSTER_DEFAULT_CSS}"/>
<style>
{theme_inner}
{popup_css}
{page_css}
</style>
</head>
<body>
<div class="pebird-export-shell">
<div class="pebird-export-map-host">
{banner}
<div id="pebird-export-map"></div>
{legend}
</div>
<p class="pebird-export-meta">Exported from Personal eBird Explorer — map tiles load from the internet.</p>
</div>
<script type="application/json" id="pebird-map-export-config">{config_json}</script>
<script src="{_LEAFLET_JS}"></script>
<script src="{_CLUSTER_JS}"></script>
<script>
{viewer_js}
</script>
</body>
</html>
"""
    return doc.encode("utf-8")

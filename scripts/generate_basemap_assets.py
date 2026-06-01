#!/usr/bin/env python3
"""Generate frontend map assets from repo manifests and ``defaults.py``.

Writes:

- ``explorer/components/all_locations_map/frontend/src/basemaps.generated.ts`` (from ``basemaps.yaml``)
- ``map_popup_constants.generated.ts`` / ``.css`` (from ``MAP_POPUP_MAX_WIDTH_PX`` in ``defaults.py``)
- ``explorer/presentation/static/leaflet_map_export_constants.generated.js`` (same popup width)

Run from repo root (also invoked by ``scripts/build_all_locations_map_frontend.py``):

    python3 scripts/generate_basemap_assets.py

Use ``--check`` in CI to fail when generated output is stale.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_SRC = _REPO_ROOT / "explorer/components/all_locations_map/frontend/src"
_STATIC = _REPO_ROOT / "explorer/presentation/static"


def _json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _popup_max_width_px() -> int:
    sys.path.insert(0, str(_REPO_ROOT))
    from explorer.app.streamlit.defaults import MAP_POPUP_MAX_WIDTH_PX  # noqa: PLC0415

    return int(MAP_POPUP_MAX_WIDTH_PX)


def render_basemaps_ts() -> str:
    sys.path.insert(0, str(_REPO_ROOT))
    from explorer.core.basemap_manifest import (  # noqa: PLC0415
        MAP_BASEMAP_DEFAULT,
        basemap_tile_layers_for_component,
        get_basemap_entries,
    )

    keys = [e.key for e in get_basemap_entries()]
    basemaps = basemap_tile_layers_for_component()
    union = " | ".join(_json_string(k) for k in keys)
    lines = [
        "/** AUTO-GENERATED from explorer/data/basemaps.yaml — do not edit. */",
        "/** Regenerate: python3 scripts/generate_basemap_assets.py */",
        "",
        "import type { TileLayerOptions } from \"leaflet\";",
        "",
        f"export type BasemapId = {union};",
        "",
        f"export const BASEMAP_IDS = [{', '.join(_json_string(k) for k in keys)}] as const;",
    ]
    lines.extend(
        [
            "",
            f"export const BASEMAP_DEFAULT: BasemapId = {_json_string(MAP_BASEMAP_DEFAULT)};",
            "",
            "export type BasemapTileConfig = { url: string; opts: TileLayerOptions };",
            "",
            "export const ALL_LOCATIONS_BASEMAPS: Record<BasemapId, BasemapTileConfig> = {",
        ]
    )
    for key in keys:
        layer = basemaps[key]
        opts_parts = [f"maxZoom: {layer['opts']['maxZoom']}"]
        if "subdomains" in layer["opts"]:
            opts_parts.append(f"subdomains: {_json_string(layer['opts']['subdomains'])}")
        opts_parts.append(f"attribution: {_json_string(layer['opts']['attribution'])}")
        opts_body = ", ".join(opts_parts)
        lines.append(f"  {_json_string(key)}: {{")
        lines.append(f"    url: {_json_string(layer['url'])},")
        lines.append(f"    opts: {{ {opts_body} }},")
        lines.append("  },")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def render_popup_constants_ts() -> str:
    width = _popup_max_width_px()
    return "\n".join(
        [
            "/** AUTO-GENERATED from explorer/app/streamlit/defaults.py — do not edit. */",
            "/** Regenerate: python3 scripts/generate_basemap_assets.py */",
            "",
            f"export const POPUP_MAX_WIDTH_PX = {width};",
            "",
        ]
    )


def render_popup_constants_css() -> str:
    width = _popup_max_width_px()
    return "\n".join(
        [
            "/** AUTO-GENERATED from explorer/app/streamlit/defaults.py — do not edit. */",
            "/** Regenerate: python3 scripts/generate_basemap_assets.py */",
            "",
            ":root {",
            f"  --pebird-map-popup-max-width: {width}px;",
            "}",
            "",
        ]
    )


def render_export_popup_constants_js() -> str:
    width = _popup_max_width_px()
    return "\n".join(
        [
            "/** AUTO-GENERATED from explorer/app/streamlit/defaults.py — do not edit. */",
            "/** Regenerate: python3 scripts/generate_basemap_assets.py */",
            "",
            f"var POPUP_MAX_WIDTH_PX = {width};",
            "",
        ]
    )


def _generated_outputs() -> tuple[tuple[Path, str], ...]:
    return (
        (_FRONTEND_SRC / "basemaps.generated.ts", render_basemaps_ts()),
        (_FRONTEND_SRC / "map_popup_constants.generated.ts", render_popup_constants_ts()),
        (_FRONTEND_SRC / "map_popup_constants.generated.css", render_popup_constants_css()),
        (
            _STATIC / "leaflet_map_export_constants.generated.js",
            render_export_popup_constants_js(),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any generated file is out of date (do not write).",
    )
    args = parser.parse_args()

    outputs = _generated_outputs()
    stale: list[str] = []
    for path, rendered in outputs:
        rel = path.relative_to(_REPO_ROOT)
        if args.check:
            if not path.is_file():
                stale.append(f"missing {rel}")
                continue
            existing = path.read_text(encoding="utf-8")
            if existing != rendered:
                stale.append(str(rel))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8")
            print(f"wrote {rel}")

    if args.check:
        if stale:
            print(
                "error: generated map assets are stale; "
                "run python3 scripts/generate_basemap_assets.py",
                file=sys.stderr,
            )
            for item in stale:
                print(f"  - {item}", file=sys.stderr)
            sys.exit(1)
        for path, _ in outputs:
            print(f"OK: {path.relative_to(_REPO_ROOT)}")
        return


if __name__ == "__main__":
    main()

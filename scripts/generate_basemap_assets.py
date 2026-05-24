#!/usr/bin/env python3
"""Generate frontend basemap assets from ``explorer/data/basemaps.yaml``.

Writes ``explorer/components/all_locations_map/frontend/src/basemaps.generated.ts``.

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
_TS_OUT = (
    _REPO_ROOT
    / "explorer/components/all_locations_map/frontend/src/basemaps.generated.ts"
)


def _json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_basemaps_ts() -> str:
    # Import after repo root is on path when run as script.
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if generated TS is out of date (do not write).",
    )
    args = parser.parse_args()

    rendered = render_basemaps_ts()
    if args.check:
        if not _TS_OUT.is_file():
            print(f"error: missing {_TS_OUT.relative_to(_REPO_ROOT)}", file=sys.stderr)
            sys.exit(1)
        existing = _TS_OUT.read_text(encoding="utf-8")
        if existing != rendered:
            print(
                f"error: {_TS_OUT.relative_to(_REPO_ROOT)} is stale; "
                "run python3 scripts/generate_basemap_assets.py",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"OK: {_TS_OUT.relative_to(_REPO_ROOT)} matches basemaps.yaml")
        return

    _TS_OUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {_TS_OUT.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()

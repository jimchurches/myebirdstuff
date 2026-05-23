#!/usr/bin/env python3
"""Extract headline perf stages from a release JSONL archive into committed metrics JSON.

Merges per-dataset runs into one file::

    { "release": "2026-05-23", "datasets": { "fixture": {...}, "real": {...} } }

Example::

    python3 scripts/extract_release_perf_metrics.py \\
        benchmarks/map_perf/snapshots/release-2026-05-23-real-r1.jsonl \\
        --dataset real
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

_HEADLINE_STAGES = (
    "e2e.first_paint",
    "taxonomy.cached_species_url_fn",
    "prep.map_context_prepare",
    "map.all_locations_leaflet.payload",
    "map.all_locations_leaflet.component_embed",
    "map.lifer_leaflet.payload",
    "map.lifer_leaflet.component_embed",
    "map.species_leaflet.payload",
    "map.species_leaflet.component_embed",
    "map.family_leaflet.payload",
    "map.family_leaflet.component_embed",
)


def _load_events(path: Path) -> list[dict]:
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _event_row(e: dict) -> dict:
    extra = e.get("extra") if isinstance(e.get("extra"), dict) else {}
    ds = e.get("dataset") if isinstance(e.get("dataset"), dict) else {}
    return {
        "stage": e.get("stage"),
        "elapsed_ms": round(float(e.get("elapsed_ms", 0)), 3),
        "session_warmth": e.get("session_warmth"),
        "payload_cache_hit": extra.get("payload_cache_hit"),
        "marker_count": extra.get("marker_count"),
        "popup_build_total_ms": extra.get("popup_build_total_ms"),
        "rows": ds.get("rows"),
        "unique_locations": ds.get("unique_locations"),
    }


def _dataset_block(events: list[dict], *, label: str, jsonl: Path, release: str) -> dict:
    headline = [_event_row(e) for e in events if e.get("stage") in _HEADLINE_STAGES]
    shape_src = next(
        (e for e in events if isinstance(e.get("dataset"), dict) and e["dataset"].get("rows")),
        events[0] if events else {},
    )
    ds = shape_src.get("dataset") if isinstance(shape_src.get("dataset"), dict) else {}
    return {
        "dataset_label": label,
        "source_jsonl": str(jsonl.relative_to(_REPO)) if jsonl.is_relative_to(_REPO) else str(jsonl),
        "git_ref": (events[0] if events else {}).get("git_ref"),
        "dataset_shape": {
            "rows": ds.get("rows"),
            "unique_locations": ds.get("unique_locations"),
            "unique_species": ds.get("unique_species"),
            "unique_checklists": ds.get("unique_checklists"),
        },
        "headline_events": headline,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="Perf JSONL archive path")
    parser.add_argument("--dataset", required=True, help="Label: fixture | real | custom")
    parser.add_argument("--release", default="2026-05-23")
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO / "docs/explorer/release-2026-05-23-baseline-metrics.json",
    )
    args = parser.parse_args()
    if not args.jsonl.is_file():
        print(f"error: missing {args.jsonl}", file=sys.stderr)
        sys.exit(1)

    events = _load_events(args.jsonl)
    block = _dataset_block(events, label=args.dataset, jsonl=args.jsonl, release=args.release)

    root: dict = {"release": args.release, "datasets": {}}
    if args.out.is_file():
        try:
            existing = json.loads(args.out.read_text(encoding="utf-8"))
            if isinstance(existing.get("datasets"), dict):
                root["datasets"] = dict(existing["datasets"])
            elif existing.get("dataset_label"):
                root["datasets"][str(existing["dataset_label"])] = existing
        except json.JSONDecodeError:
            pass
    root["datasets"][args.dataset] = block

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(root, indent=2) + "\n", encoding="utf-8")
    n = len(block["headline_events"])
    print(f"Wrote {args.out} (dataset={args.dataset!r}, {n} headline events)")


if __name__ == "__main__":
    main()

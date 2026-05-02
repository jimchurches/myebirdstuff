#!/usr/bin/env python3
"""Archive an ``EXPLORER_PERF_LOG_FILE`` JSONL into ``benchmarks/map_perf/snapshots/`` (#179).

Output is gitignored JSON (pretty-printed) with metadata + parsed ``events`` for local history and
diffs. Intended for solo-dev / single-machine before/after notes; not CI.

Example::

    export EXPLORER_PERF=1 EXPLORER_PERF_LOG_FILE=$PWD/tmp/perf.jsonl
    rm -f tmp/perf.jsonl && streamlit run explorer/app/streamlit/app.py
    # … exercise the map … then Ctrl+C
    python scripts/snapshot_explorer_perf_log.py tmp/perf.jsonl --label all-locations-warm

"""

from __future__ import annotations

import argparse
import json
import re
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path


def _slug_label(s: str) -> str:
    s = (s or "run").strip().lower().replace(" ", "_")
    s = re.sub(r"[^a-z0-9._-]", "_", s)
    return (s[:64] if len(s) > 64 else s) or "run"


def _events_from_jsonl(raw: str) -> list[dict]:
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    events: list[dict] = []
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Line {i}: invalid JSON ({exc})\n<<< {line[:200]}") from exc
        if isinstance(obj, dict):
            events.append(obj)
        else:
            raise SystemExit(f"Line {i}: expected JSON object, got {type(obj).__name__}")
    return events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy Explorer perf JSONL to benchmarks/map_perf/snapshots/ (listed in .gitignore).",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Existing JSONL path (same as EXPLORER_PERF_LOG_FILE).",
    )
    parser.add_argument(
        "--label",
        default="run",
        help="Short slug for the filename (e.g. fixture, after-pr-123). Default: run",
    )
    args = parser.parse_args(argv)

    src = Path(args.source).expanduser()
    if not src.is_file():
        print(f"error: source not found or not a file: {src}", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "benchmarks" / "map_perf" / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_text = src.read_text(encoding="utf-8")
    events = _events_from_jsonl(raw_text)

    now = datetime.now(tz=UTC)
    stem = now.strftime("%Y-%m-%dT%H-%M-%SZ") + "_" + _slug_label(str(args.label))
    out_path = out_dir / f"{stem}.json"

    payload = {
        "schema": 1,
        "created_utc": now.isoformat(),
        "source_resolved_path": str(src.resolve()),
        "hostname": socket.gethostname(),
        "label": args.label,
        "event_count": len(events),
        "events": events,
    }

    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(out_path.relative_to(repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

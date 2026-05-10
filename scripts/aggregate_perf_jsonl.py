#!/usr/bin/env python3
"""Aggregate Explorer perf JSONL archives into per-(group, stage) tables (#205 batch 4 I5).

Reads one or more ``EXPLORER_PERF_LOG_FILE`` archives (and/or ``e2e.first_paint`` records from
:func:`tests.explorer.e2e_support.append_e2e_first_paint_record`), groups files by a
filename-regex capture, and prints a table with per-stage event count, median, p95, and max
``elapsed_ms`` per group — plus optional per-stage aggregates over numeric ``extra.*`` fields.

Origin: ad-hoc ``/tmp/aggregate_w1_ab.py`` used during the W1 A/B for #205 batch 3. Graduating
into a reusable tool so future batches don't re-write the same arithmetic.

Examples
--------
Reproduce the W1 A/B summary::

    python scripts/aggregate_perf_jsonl.py \\
        benchmarks/map_perf/snapshots/issue-205-batch-3 \\
        --glob 'w1-*.jsonl' \\
        --group-regex 'w1-(?P<dataset>[^-]+)-fragment_(?P<mode>[^-]+)' \\
        --stage prep.map_iframe_embed \\
        --stage prep.build_species_overlay_map

Batch 4 baseline with the new I1/I2/I4 fields::

    python scripts/aggregate_perf_jsonl.py \\
        benchmarks/map_perf/snapshots/issue-205-batch-4 \\
        --group-regex 'baseline-(?P<dataset>[^-]+)-r(?P<run>\\d+)' \\
        --stage prep.build_species_overlay_map \\
        --stage e2e.first_paint \\
        --extra-key marker_count \\
        --extra-key popup_build_count \\
        --extra-key popup_cache_hit_count \\
        --extra-key popup_build_total_ms

Output is plain text by default (suitable for posting to GitHub comments) or JSON when
``--format json`` is passed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file and return parsed objects (skipping malformed / non-object lines)."""
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
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


def percentile(values: list[float], q: float) -> float:
    """Return the *q* percentile of *values* using the nearest-rank method (``q`` in 0..100)."""
    if not values:
        return float("nan")
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = max(0, min(len(s) - 1, int(round((q / 100.0) * (len(s) - 1)))))
    return s[k]


def group_label_for_filename(name: str, group_regex: re.Pattern[str] | None) -> str:
    """Return the regex-derived group label for *name*, or *name* itself when no regex matches."""
    if group_regex is None:
        return name
    m = group_regex.search(name)
    if not m:
        return name
    captures = m.groupdict()
    if not captures:
        return m.group(0)
    return "/".join(f"{k}={v}" for k, v in captures.items() if v is not None)


def aggregate(
    files: Iterable[Path],
    *,
    group_regex: re.Pattern[str] | None,
    stages: set[str] | None,
    extra_keys: list[str],
) -> dict[str, Any]:
    """Compute per-(group, stage) statistics from *files*.

    Returns a dict::

        {
            "groups": {
                "<group_label>": {
                    "n_files": int,
                    "files": [str, ...],
                    "stages": {
                        "<stage>": {
                            "n_runs": int,                # files in this group
                            "total_events": int,          # sum of events across files
                            "events_per_run": [int, ...], # per-file event count
                            "median_events_per_run": float,
                            "elapsed_ms": {
                                "median": float,
                                "p95": float,
                                "max": float,
                                "n_samples": int,
                            },
                            "extras": {
                                "<extra_key>": {
                                    "median": float,
                                    "p95": float,
                                    "max": float,
                                    "n_samples": int,
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    groups: dict[str, dict[Path, list[dict[str, Any]]]] = defaultdict(dict)
    for f in files:
        label = group_label_for_filename(f.name, group_regex)
        groups[label][f] = parse_jsonl(f)

    out_groups: dict[str, Any] = {}
    for label, file_map in groups.items():
        files_in_group = list(file_map.keys())
        all_stages_in_group = {
            ev.get("stage")
            for events in file_map.values()
            for ev in events
            if isinstance(ev.get("stage"), str)
        }
        stages_to_emit = (
            sorted(all_stages_in_group & stages) if stages else sorted(all_stages_in_group)
        )

        stage_blob: dict[str, Any] = {}
        for stage in stages_to_emit:
            events_per_run: list[int] = []
            elapsed_samples: list[float] = []
            extra_samples: dict[str, list[float]] = {k: [] for k in extra_keys}
            for events in file_map.values():
                matches = [e for e in events if e.get("stage") == stage]
                events_per_run.append(len(matches))
                for e in matches:
                    ms = e.get("elapsed_ms")
                    if isinstance(ms, (int, float)):
                        elapsed_samples.append(float(ms))
                    extra = e.get("extra") if isinstance(e.get("extra"), dict) else {}
                    for k in extra_keys:
                        # ``extra`` events for E2E first-paint records put fields at the top
                        # level rather than nested under ``extra``; check both.
                        v = extra.get(k) if isinstance(extra, dict) else None
                        if v is None:
                            v = e.get(k)
                        if isinstance(v, (int, float)):
                            extra_samples[k].append(float(v))
            stage_blob[stage] = {
                "n_runs": len(files_in_group),
                "total_events": sum(events_per_run),
                "events_per_run": events_per_run,
                "median_events_per_run": (
                    float(median(events_per_run)) if events_per_run else 0.0
                ),
                "elapsed_ms": {
                    "median": percentile(elapsed_samples, 50.0),
                    "p95": percentile(elapsed_samples, 95.0),
                    "max": max(elapsed_samples) if elapsed_samples else float("nan"),
                    "n_samples": len(elapsed_samples),
                },
                "extras": {
                    k: {
                        "median": percentile(extra_samples[k], 50.0),
                        "p95": percentile(extra_samples[k], 95.0),
                        "max": max(extra_samples[k]) if extra_samples[k] else float("nan"),
                        "n_samples": len(extra_samples[k]),
                    }
                    for k in extra_keys
                },
            }
        out_groups[label] = {
            "n_files": len(files_in_group),
            "files": sorted(str(f) for f in files_in_group),
            "stages": stage_blob,
        }
    return {"groups": out_groups}


def _fmt(v: float, width: int = 9) -> str:
    if v != v:  # NaN
        return "—".rjust(width)
    return f"{v:>{width}.1f}"


def render_text(result: dict[str, Any], extra_keys: list[str]) -> str:
    """Render the aggregate result as a flat text table (one row per (group, stage))."""
    lines: list[str] = []
    base_cols = [
        "group",
        "stage",
        "n_runs",
        "total_events",
        "med_evt/run",
        "med_ms",
        "p95_ms",
        "max_ms",
    ]
    extra_cols: list[str] = []
    for k in extra_keys:
        extra_cols += [f"{k}.med", f"{k}.max"]
    header_cols = base_cols + extra_cols
    lines.append(" ".join(f"{c:>14s}" if i >= 2 else f"{c:<28s}" for i, c in enumerate(header_cols)))
    lines.append("-" * (len(lines[-1])))

    for group_label in sorted(result["groups"].keys()):
        g = result["groups"][group_label]
        for stage in sorted(g["stages"].keys()):
            s = g["stages"][stage]
            row = [
                f"{group_label:<28s}",
                f"{stage:<28s}",
                f"{s['n_runs']:>14d}",
                f"{s['total_events']:>14d}",
                f"{s['median_events_per_run']:>14.1f}",
                _fmt(s["elapsed_ms"]["median"], 14),
                _fmt(s["elapsed_ms"]["p95"], 14),
                _fmt(s["elapsed_ms"]["max"], 14),
            ]
            for k in extra_keys:
                ev = s["extras"][k]
                row += [_fmt(ev["median"], 14), _fmt(ev["max"], 14)]
            lines.append(" ".join(row))
    return "\n".join(lines) + "\n"


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aggregate_perf_jsonl",
        description="Aggregate Explorer perf JSONL archives into per-(group, stage) tables.",
    )
    p.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing JSONL files (matched against --glob).",
    )
    p.add_argument(
        "--glob",
        default="*.jsonl",
        help="Glob pattern (relative to input_dir) for files to aggregate. Default: *.jsonl",
    )
    p.add_argument(
        "--group-regex",
        default=None,
        help=(
            "Optional regex applied to each file name; named captures become the group label. "
            "Example: 'w1-(?P<dataset>[^-]+)-fragment_(?P<mode>[^-]+)'."
        ),
    )
    p.add_argument(
        "--stage",
        action="append",
        default=[],
        dest="stages",
        help="Stage to include (repeatable). Default: include every stage observed.",
    )
    p.add_argument(
        "--extra-key",
        action="append",
        default=[],
        dest="extra_keys",
        help=(
            "Numeric key to aggregate from each event's ``extra`` dict (or top-level for "
            "synthesised E2E records). Repeatable."
        ),
    )
    p.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Default: text.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)

    if not args.input_dir.is_dir():
        print(f"error: input_dir is not a directory: {args.input_dir}", file=sys.stderr)
        return 2

    group_regex = re.compile(args.group_regex) if args.group_regex else None
    files = sorted(args.input_dir.glob(args.glob))
    if not files:
        print(f"warning: no files matched {args.glob!r} under {args.input_dir}", file=sys.stderr)

    stages_filter = set(args.stages) if args.stages else None
    result = aggregate(
        files,
        group_regex=group_regex,
        stages=stages_filter,
        extra_keys=list(args.extra_keys),
    )

    if args.format == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        print(render_text(result, list(args.extra_keys)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

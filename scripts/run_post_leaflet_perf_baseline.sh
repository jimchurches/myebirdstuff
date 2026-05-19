#!/usr/bin/env bash
# Post-Leaflet perf baseline (#222 §8.5): run journey, archive JSONL, print aggregate table.
#
# Usage:
#   ./scripts/run_post_leaflet_perf_baseline.sh              # integration fixture (fast)
#   ./scripts/run_post_leaflet_perf_baseline.sh --real       # tests/fixtures/MyEBirdData.csv if present
#   ./scripts/run_post_leaflet_perf_baseline.sh /path/to.csv # explicit export path
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SNAP_DIR="$ROOT/benchmarks/map_perf/snapshots"
REAL_CSV="$ROOT/tests/fixtures/MyEBirdData.csv"
MODE="fixture"
DATASET_ARG=()

if [[ "${1:-}" == "--real" ]]; then
  MODE="real"
  shift
elif [[ -n "${1:-}" && "${1:0:1}" != "-" ]]; then
  MODE="custom"
  export EXPLORER_E2E_DATASET_CSV="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
  shift
fi

if [[ "$MODE" == "real" ]]; then
  if [[ ! -f "$REAL_CSV" ]]; then
    echo "error: --real expects gitignored $REAL_CSV (copy your eBird export there)" >&2
    exit 1
  fi
  export EXPLORER_E2E_DATASET_CSV="$REAL_CSV"
  ARCHIVE="$SNAP_DIR/post-leaflet-real-r1.jsonl"
  LABEL="${1:-post-leaflet-real-myebrddata}"
elif [[ "$MODE" == "custom" ]]; then
  ARCHIVE="$SNAP_DIR/post-leaflet-custom-r1.jsonl"
  LABEL="${1:-post-leaflet-custom}"
else
  unset EXPLORER_E2E_DATASET_CSV 2>/dev/null || true
  ARCHIVE="$SNAP_DIR/post-leaflet-fixture-r1.jsonl"
  LABEL="${1:-post-leaflet-four-map-fixture}"
fi

mkdir -p "$SNAP_DIR"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export EXPLORER_E2E_PERF_JSONL_ARCHIVE="$ARCHIVE"
rm -f "$ARCHIVE"

if [[ -n "${EXPLORER_E2E_DATASET_CSV:-}" ]]; then
  echo "Running perf E2E (real CSV: $EXPLORER_E2E_DATASET_CSV) → $ARCHIVE"
else
  echo "Running perf E2E (fixture) → $ARCHIVE"
fi
pytest tests/explorer/test_map_perf_e2e.py::test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling --perf -q

echo ""
echo "Snapshot + aggregate:"
python scripts/snapshot_explorer_perf_log.py "$ARCHIVE" --label "$LABEL"
python scripts/aggregate_perf_jsonl.py "$SNAP_DIR" \
  --glob 'post-leaflet-*.jsonl' \
  --stage map.all_locations_leaflet.payload \
  --stage map.all_locations_leaflet.component_embed \
  --stage map.lifer_leaflet.payload \
  --stage map.lifer_leaflet.component_embed \
  --stage map.species_leaflet.payload \
  --stage map.family_leaflet.payload \
  --stage prep.map_context_prepare \
  --stage e2e.first_paint \
  --extra-key payload_cache_hit \
  --extra-key marker_count \
  --extra-key popup_build_total_ms \
  --extra-key popup_build_count \
  --extra-key banner_ms

echo ""
echo "Baseline doc: docs/explorer/issue-222-section-8-baseline.md"

#!/usr/bin/env bash
# Release perf baseline — archives JSONL under benchmarks/map_perf/snapshots/ (gitignored).
#
# Usage (repo root):
#   ./scripts/run_release_perf_baseline.sh              # integration fixture (~1 min)
#   ./scripts/run_release_perf_baseline.sh --real       # tests/fixtures/MyEBirdData.csv (~4 min)
#   ./scripts/run_release_perf_baseline.sh /path/to/MyEBirdData.csv
#
# Docs: docs/explorer/release-2026-05-23-baseline.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RELEASE="${EXPLORER_RELEASE_ID:-2026-05-23}"
SNAP_DIR="$ROOT/benchmarks/map_perf/snapshots"
REAL_CSV="$ROOT/tests/fixtures/MyEBirdData.csv"
MODE="fixture"

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
  ARCHIVE="$SNAP_DIR/release-${RELEASE}-real-r1.jsonl"
  LABEL="release-${RELEASE}-real"
elif [[ "$MODE" == "custom" ]]; then
  ARCHIVE="$SNAP_DIR/release-${RELEASE}-custom-r1.jsonl"
  LABEL="release-${RELEASE}-custom"
else
  unset EXPLORER_E2E_DATASET_CSV 2>/dev/null || true
  ARCHIVE="$SNAP_DIR/release-${RELEASE}-fixture-r1.jsonl"
  LABEL="release-${RELEASE}-fixture"
fi

mkdir -p "$SNAP_DIR"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

unset PLAYWRIGHT_BROWSERS_PATH 2>/dev/null || true

export EXPLORER_E2E_PERF_JSONL_ARCHIVE="$ARCHIVE"
rm -f "$ARCHIVE"

if [[ -n "${EXPLORER_E2E_DATASET_CSV:-}" ]]; then
  echo "Release $RELEASE perf E2E (real CSV: $EXPLORER_E2E_DATASET_CSV) → $ARCHIVE"
else
  echo "Release $RELEASE perf E2E (fixture) → $ARCHIVE"
fi

set +e
pytest tests/explorer/test_map_perf_e2e.py::test_map_perf_fixture_journey_emits_prep_stages_within_loose_ceiling --perf -q
PYTEST_RC=$?
set -e

echo ""
echo "Snapshot + aggregate (pytest exit $PYTEST_RC — journey may fail on Species banner E2E; JSONL still useful):"
python scripts/snapshot_explorer_perf_log.py "$ARCHIVE" --label "$LABEL" 2>/dev/null || true
python scripts/aggregate_perf_jsonl.py "$SNAP_DIR" \
  --glob "release-${RELEASE}-*.jsonl" \
  --group-regex "release-${RELEASE}-(?P<dataset>[^-]+)-r1" \
  --stage e2e.first_paint \
  --stage taxonomy.cached_species_url_fn \
  --stage prep.map_context_prepare \
  --stage map.all_locations_leaflet.payload \
  --stage map.all_locations_leaflet.component_embed \
  --stage map.lifer_leaflet.payload \
  --stage map.lifer_leaflet.component_embed \
  --stage map.species_leaflet.payload \
  --stage map.family_leaflet.payload \
  --extra-key payload_cache_hit \
  --extra-key marker_count \
  --extra-key popup_build_total_ms

echo ""
echo "Baseline doc: docs/explorer/release-${RELEASE}-baseline.md"
exit "$PYTEST_RC"

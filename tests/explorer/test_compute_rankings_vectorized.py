"""Regression: vectorized ranking groupbys on the integration fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from explorer.core.data_loader import load_dataset
from explorer.core.stats import compute_rankings, rankings_by_location

_INTEGRATION_CSV = (
    Path(__file__).resolve().parents[1] / "fixtures" / "ebird_integration_fixture.csv"
)


@pytest.fixture
def _fixture_tables():
    df = load_dataset(_INTEGRATION_CSV)
    cl = df.drop_duplicates(subset=["Submission ID"]).copy()
    dur_col = "Duration (Min)" if "Duration (Min)" in df.columns else None
    dist_col = "Distance Traveled (km)" if "Distance Traveled (km)" in df.columns else None
    return df, cl, dur_col, dist_col


def test_compute_rankings_returns_nonempty_core_sections(_fixture_tables) -> None:
    df, cl, dur_col, dist_col = _fixture_tables
    result = compute_rankings(df, cl, limit=200, dur_col=dur_col, dist_col=dist_col)
    assert len(result["species"]) > 0
    assert len(result["species_loc"]) > 0
    assert len(result["visited"]) > 0


def test_rankings_by_location_species_respects_limit(_fixture_tables) -> None:
    df, cl, _dur, _dist = _fixture_tables
    rows = rankings_by_location(df, cl, "species", lambda x: f"{int(x):,}", limit=5)
    assert 1 <= len(rows) <= 5


def test_compute_rankings_all_sections_bounded(_fixture_tables) -> None:
    df, cl, dur_col, dist_col = _fixture_tables
    result = compute_rankings(df, cl, limit=10, dur_col=dur_col, dist_col=dist_col)
    for key in ("species", "individuals", "species_loc", "individuals_loc", "visited"):
        assert len(result[key]) <= 10

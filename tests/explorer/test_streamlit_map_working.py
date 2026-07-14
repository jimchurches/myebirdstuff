"""Tests for ``explorer.app.streamlit.map_working`` helpers."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

pytest.importorskip("streamlit", reason="explorer.app.streamlit.map_working is for Streamlit UI")

from explorer.core.data_loader import load_dataset  # noqa: E402

from explorer.app.streamlit.map_working import (  # noqa: E402
    date_bounds_from_df,
    date_inception_to_today_default,
    streamlit_working_set_and_status,
)


def _fixture_csv_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "tests" / "fixtures" / "ebird_integration_fixture.csv"


@pytest.fixture
def df() -> pd.DataFrame:
    path = _fixture_csv_path()
    assert path.is_file(), f"required integration fixture is missing: {path}"
    return load_dataset(path)


def test_date_bounds_from_df(df: pd.DataFrame) -> None:
    lo, hi = date_bounds_from_df(df)
    assert (lo, hi) == (date(2022, 1, 16), date(2026, 2, 25))


def test_date_inception_to_today_default(df: pd.DataFrame) -> None:
    a, b = date_inception_to_today_default(df)
    assert a == date(2022, 1, 16)
    assert b == date.today()


def test_streamlit_lifer_status(df: pd.DataFrame) -> None:
    ws, status = streamlit_working_set_and_status(
        df,
        map_view_mode="lifers",
        date_filter_on=False,
        date_range=None,
    )
    assert ws is not None
    assert len(ws.df) == len(df)
    assert status == "Lifer view uses all-time data"


def test_streamlit_date_filter_on(df: pd.DataFrame) -> None:
    lo, hi = date_bounds_from_df(df)
    ws, status = streamlit_working_set_and_status(
        df,
        map_view_mode="all",
        date_filter_on=True,
        date_range=(lo, hi),
    )
    assert ws is not None
    assert len(ws.df) == len(df)
    assert status == f"Date filter: {lo.isoformat()} to {hi.isoformat()}"


def test_streamlit_species_view_uses_same_date_filter_as_all(df: pd.DataFrame) -> None:
    lo, hi = date_bounds_from_df(df)
    ws_all, st_all = streamlit_working_set_and_status(
        df,
        map_view_mode="all",
        date_filter_on=True,
        date_range=(lo, hi),
    )
    ws_sp, st_sp = streamlit_working_set_and_status(
        df,
        map_view_mode="species",
        date_filter_on=True,
        date_range=(lo, hi),
    )
    assert ws_all is not None and ws_sp is not None
    assert ws_all.df["Submission ID"].tolist() == ws_sp.df["Submission ID"].tolist()
    assert st_all == st_sp


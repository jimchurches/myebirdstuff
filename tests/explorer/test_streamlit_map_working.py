"""Tests for ``streamlit_app/map_working`` helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

pytest.importorskip("streamlit", reason="streamlit_app/map_working is for Streamlit UI")

from personal_ebird_explorer.data_loader import load_dataset  # noqa: E402

from streamlit_app.map_working import (
    date_bounds_from_df,
    date_inception_to_today_default,
    folium_map_to_html_bytes,
    streamlit_working_set_and_status,
)


def _fixture_csv_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "tests" / "fixtures" / "ebird_integration_fixture.csv"


@pytest.fixture
def df() -> pd.DataFrame:
    path = _fixture_csv_path()
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}")
    return load_dataset(path)


def test_date_bounds_from_df(df: pd.DataFrame) -> None:
    lo, hi = date_bounds_from_df(df)
    assert lo <= hi


def test_date_inception_to_today_default(df: pd.DataFrame) -> None:
    a, b = date_inception_to_today_default(df)
    assert a <= b


def test_streamlit_lifer_status(df: pd.DataFrame) -> None:
    ws, status = streamlit_working_set_and_status(
        df,
        map_view_mode="lifers",
        date_filter_on=False,
        date_range=None,
        map_caches=None,
    )
    assert ws is not None
    assert "Lifer" in status


def test_streamlit_date_filter_on(df: pd.DataFrame) -> None:
    lo, hi = date_bounds_from_df(df)
    ws, status = streamlit_working_set_and_status(
        df,
        map_view_mode="all",
        date_filter_on=True,
        date_range=(lo, hi),
        map_caches=None,
    )
    assert ws is not None
    assert "Date filter:" in status


def test_folium_map_to_html_bytes() -> None:
    import folium

    m = folium.Map()
    b = folium_map_to_html_bytes(m)
    low = b.lower()
    assert b"<!doctype html>" in low or b"<html" in low

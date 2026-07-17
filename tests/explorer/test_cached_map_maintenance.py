"""Streamlit cache for location duplicate maintenance scan."""

from __future__ import annotations

import pandas as pd
import pytest

from explorer.app.streamlit import app_caches
from explorer.core.duplicate_checks import get_map_maintenance_data


@pytest.fixture(autouse=True)
def _clear_map_maintenance_cache() -> None:
    app_caches.cached_map_maintenance_data.clear()
    yield
    app_caches.cached_map_maintenance_data.clear()


def test_cached_map_maintenance_matches_direct_call() -> None:
    loc_df = pd.DataFrame(
        {
            "Location ID": ["L1", "L2", "L3"],
            "Location": ["A", "B", "C"],
            "Latitude": [-35.0, -35.0000001, -36.0],
            "Longitude": [149.0, 149.0000001, 150.0],
        }
    )
    threshold_m = 10

    expected = get_map_maintenance_data(loc_df, threshold_m)
    first = app_caches.cached_map_maintenance_data(loc_df, threshold_m)
    second = app_caches.cached_map_maintenance_data(loc_df, threshold_m)

    assert first == expected
    assert second == first


def test_cached_map_maintenance_reuses_result_for_same_dataframe_and_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loc_df = pd.DataFrame(
        {
            "Location ID": ["L1", "L2", "L3"],
            "Location": ["A", "B", "C"],
            "Latitude": [-35.0, -35.0000001, -36.0],
            "Longitude": [149.0, 149.0000001, 150.0],
        }
    )
    threshold_m = 10
    calls: list[int] = []

    def fake_scan(_loc_df: pd.DataFrame, threshold: int):
        calls.append(threshold)
        return [("duplicate", threshold)], [("near", threshold)]

    monkeypatch.setattr("explorer.core.duplicate_checks.get_map_maintenance_data", fake_scan)
    first = app_caches.cached_map_maintenance_data(loc_df, threshold_m)
    second = app_caches.cached_map_maintenance_data(loc_df, threshold_m)

    assert first == ([("duplicate", 10)], [("near", 10)])
    assert second == first
    assert calls == [10]


def test_cached_map_maintenance_threshold_is_part_of_cache_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loc_df = pd.DataFrame(
        {
            "Location ID": ["L1", "L2"],
            "Location": ["A", "B"],
            "Latitude": [-35.0, -35.0001],
            "Longitude": [149.0, 149.0001],
        }
    )
    calls: list[int] = []

    def fake_scan(_loc_df: pd.DataFrame, threshold: int):
        calls.append(threshold)
        return [], [(threshold,)]

    monkeypatch.setattr("explorer.core.duplicate_checks.get_map_maintenance_data", fake_scan)

    assert app_caches.cached_map_maintenance_data(loc_df, 10) == ([], [(10,)])
    assert app_caches.cached_map_maintenance_data(loc_df, 20) == ([], [(20,)])
    assert calls == [10, 20]

"""Checklist stats Streamlit cache: single impl, no duplicate compute on matching keys."""

from __future__ import annotations

import pandas as pd
import pytest

from explorer.app.streamlit import app_caches
from explorer.app.streamlit.streamlit_ui_constants import CHECKLIST_STATS_TOP_N_TABLE_LIMIT
from explorer.core.checklist_stats_compute import ChecklistStatsPayload


def _minimal_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Submission ID": ["S1", "S1"],
            "Date": pd.to_datetime(["2025-01-01", "2025-01-01"]),
            "Time": ["08:00", "08:00"],
            "Scientific Name": ["Anas gracilis", "Anas castanea"],
            "Common Name": ["Grey Teal", "Chestnut Teal"],
            "Count": [2, 1],
            "Location ID": ["L1", "L1"],
            "Location": ["Wetland", "Wetland"],
            "Latitude": [-35.0, -35.0],
            "Longitude": [149.0, 149.0],
            "Protocol": ["Traveling", "Traveling"],
            "Duration (Min)": [30, 30],
            "Distance Traveled (km)": [1.0, 1.0],
        }
    )


@pytest.fixture(autouse=True)
def _clear_checklist_stats_cache() -> None:
    app_caches._cached_checklist_stats_payload_impl.clear()
    yield
    app_caches._cached_checklist_stats_payload_impl.clear()


def test_working_and_full_export_share_one_compute_when_args_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default settings: full export uses same top_n/high-count defaults as the Checklist tab."""
    compute_calls: list[tuple[pd.DataFrame, int, str, str, str | None]] = []

    def counting_compute(
        df: pd.DataFrame,
        top_n_limit: int,
        *,
        high_count_sort: str = "total_count",
        high_count_tie_break: str = "last",
        taxonomy_locale: str | None = None,
    ) -> ChecklistStatsPayload | None:
        compute_calls.append(
            (df, top_n_limit, high_count_sort, high_count_tie_break, taxonomy_locale)
        )
        return ChecklistStatsPayload(
            n_checklists=1,
            n_species=1,
            n_individuals=1,
            n_completed_display="1",
            protocol_rows=[],
            total_minutes=0.0,
            total_hours=0.0,
            total_days_dec=0.0,
            total_months=0.0,
            total_years=0.0,
            n_days_with_checklist=1,
            n_shared=0,
            shared_minutes=0.0,
            shared_hours=0.0,
            n_days_birding_with_others=0,
            total_km=0.0,
            parkruns=0.0,
            marathons=0.0,
            times_equator=0.0,
            times_godwit=0.0,
            streak=0,
            streak_start_date="",
            streak_start_loc="",
            streak_start_sid="",
            streak_start_lid="",
            streak_end_date="",
            streak_end_loc="",
            streak_end_sid="",
            streak_end_lid="",
            rankings={},
            years_list=[],
            yearly_rows=[],
            incomplete_by_year={},
            country_sections=[],
        )

    monkeypatch.setattr(app_caches, "compute_checklist_stats_payload", counting_compute)
    df = _minimal_df()
    locale = "en_AU"

    app_caches.cached_checklist_stats_payload(df, locale)
    app_caches.cached_full_export_checklist_stats_payload(
        df,
        CHECKLIST_STATS_TOP_N_TABLE_LIMIT,
        "total_count",
        "last",
        locale,
    )

    assert compute_calls == [
        (
            df,
            CHECKLIST_STATS_TOP_N_TABLE_LIMIT,
            "total_count",
            "last",
            locale,
        )
    ]


def test_full_export_recomputes_when_top_n_differs(monkeypatch: pytest.MonkeyPatch) -> None:
    compute_calls: list[tuple[tuple, dict]] = []

    def counting_compute(*args, **kwargs) -> ChecklistStatsPayload | None:
        compute_calls.append((args, kwargs))
        return None

    monkeypatch.setattr(app_caches, "compute_checklist_stats_payload", counting_compute)
    df = _minimal_df()
    locale = "en_AU"

    app_caches.cached_checklist_stats_payload(df, locale)
    app_caches.cached_full_export_checklist_stats_payload(df, 50, "total_count", "last", locale)

    assert [call_args[1] for call_args, _ in compute_calls] == [
        CHECKLIST_STATS_TOP_N_TABLE_LIMIT,
        50,
    ]
    assert [kwargs for _, kwargs in compute_calls] == [
        {
            "high_count_sort": "total_count",
            "high_count_tie_break": "last",
            "taxonomy_locale": locale,
        },
        {
            "high_count_sort": "total_count",
            "high_count_tie_break": "last",
            "taxonomy_locale": locale,
        },
    ]

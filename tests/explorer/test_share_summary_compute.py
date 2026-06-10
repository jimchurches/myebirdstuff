"""Tests for :mod:`explorer.core.share_summary_compute`."""

from datetime import date

import pandas as pd

from explorer.core.share_summary_compute import (
    compute_share_summary_stats,
    format_custom_date_range,
    period_for_custom,
    period_for_year,
)


def _row(*, sid: str, dt: str, species: str, loc: str = "L1", country: str = "AU") -> dict:
    return {
        "Submission ID": sid,
        "Date": dt,
        "Scientific Name": species,
        "Common Name": species,
        "Count": 1,
        "Location ID": loc,
        "Location": loc,
        "Country": country,
        "Protocol": "Traveling",
        "All Obs Reported": 1,
    }


def test_compute_share_summary_stats_year():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-10", species="Species a"),
            _row(sid="S1", dt="2025-01-10", species="Species b"),
            _row(sid="S2", dt="2025-06-01", species="Species c"),
            _row(sid="S3", dt="2024-12-31", species="Species old"),
        ]
    )
    stats = compute_share_summary_stats(df, period_for_year(2025))
    assert stats is not None
    assert stats.species == 3
    assert stats.checklists == 2
    assert stats.lifers == 3


def test_longest_streak_for_month_period():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-06-01", species="Species a"),
            _row(sid="S2", dt="2025-06-02", species="Species a"),
            _row(sid="S3", dt="2025-06-03", species="Species a"),
            _row(sid="S4", dt="2025-06-10", species="Species b"),
        ]
    )
    from explorer.core.share_summary_compute import period_for_month

    stats = compute_share_summary_stats(df, period_for_month(2025, 6))
    assert stats is not None
    assert stats.longest_streak == 3


def test_longest_streak_not_computed_for_custom_trip():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-06-01", species="Species a"),
            _row(sid="S2", dt="2025-06-02", species="Species a"),
        ]
    )
    stats = compute_share_summary_stats(
        df,
        period_for_custom(date(2025, 6, 1), date(2025, 6, 7), trip_title="Trip"),
    )
    assert stats is not None
    assert stats.longest_streak is None


def test_countries_for_year_period():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-03-01", species="Species a", country="AU"),
            _row(sid="S2", dt="2025-04-01", species="Species b", country="US"),
        ]
    )
    stats = compute_share_summary_stats(df, period_for_year(2025))
    assert stats is not None
    assert stats.countries == 2


def test_countries_computed_for_custom_trip():
    df = pd.DataFrame([_row(sid="S1", dt="2025-06-01", species="Species a", country="AU")])
    stats = compute_share_summary_stats(
        df,
        period_for_custom(date(2025, 6, 1), date(2025, 6, 7), trip_title="Trip"),
    )
    assert stats is not None
    assert stats.countries == 1


def test_period_for_week_containing_sun_sat():
    from explorer.core.share_summary_compute import period_for_week_containing

    period = period_for_week_containing(date(2026, 6, 3))  # Wed
    assert period.start == date(2026, 5, 31)  # Sunday
    assert period.end == date(2026, 6, 6)  # Saturday
    assert period.label == "May 31, 2026 - June 6, 2026"


def test_birding_days_in_stat_pairs():
    from explorer.presentation.share_summary_preview import stat_pairs

    stats = compute_share_summary_stats(
        pd.DataFrame([_row(sid="S1", dt="2025-06-01", species="a"), _row(sid="S2", dt="2025-06-02", species="b")]),
        period_for_custom(date(2025, 6, 1), date(2025, 6, 7)),
    )
    pairs = dict(stat_pairs(stats))
    assert pairs["Birding days"] == "2"


def test_format_custom_date_range_same_month():
    assert format_custom_date_range(date(2025, 6, 1), date(2025, 6, 7)) == "1 – 7 June 2025"
    assert format_custom_date_range(date(2025, 5, 6), date(2025, 5, 12)) == "6 – 12 May 2025"


def test_compute_share_summary_stats_custom_trip():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-03-05", species="Species a", loc="A"),
            _row(sid="S2", dt="2025-03-07", species="Species b", loc="B"),
        ]
    )
    period = period_for_custom(
        date(2025, 3, 5),
        date(2025, 3, 7),
        trip_title="Tassie trip",
    )
    stats = compute_share_summary_stats(df, period)
    assert stats is not None
    assert stats.period_label == "5 – 7 March 2025"
    assert stats.trip_title == "Tassie trip"
    assert stats.checklists == 2
    assert stats.locations == 2


def test_trip_title_renders_on_card():
    from explorer.presentation.share_summary_preview import render_share_summary_preview_html
    from explorer.core.share_summary_compute import ShareSummaryStats

    stats = ShareSummaryStats(
        period_label="1 – 7 June 2025",
        period_kind="custom",
        trip_title="North Coast NSW Exploration",
        lifers=12,
    )
    html = render_share_summary_preview_html(stats, layout="hero")
    assert "1 – 7 June 2025" in html
    assert "North Coast NSW Exploration" in html

"""Tests for :mod:`explorer.core.share_summary_compute`."""

from datetime import date

import pandas as pd

from explorer.core.share_summary_compute import (
    compute_share_summary_all_time_stats,
    compute_share_summary_stats,
    format_custom_date_range,
    period_for_custom,
    period_for_lifetime,
    period_for_month,
    period_for_previous_month,
    period_for_previous_week_containing,
    period_for_week_containing,
    period_for_year,
    period_species_common_names,
    period_species_name_map,
    resolve_period,
    suggest_period_anchor,
)
from explorer.presentation.share_summary_preview import summary_status_metrics


def _row(
    *,
    sid: str,
    dt: str,
    species: str,
    loc: str = "L1",
    country: str = "AU",
    observers: float = 1.0,
) -> dict:
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
        "Number of Observers": observers,
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
    assert stats.completed_checklists == 2


def test_compute_share_summary_stats_completed_checklists():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-10", species="Species a"),
            _row(sid="S2", dt="2025-01-11", species="Species b"),
        ]
    )
    df.loc[df["Submission ID"] == "S2", "All Obs Reported"] = 0
    stats = compute_share_summary_stats(df, period_for_year(2025))
    assert stats is not None
    assert stats.checklists == 2
    assert stats.completed_checklists == 1


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


def test_period_for_lifetime_uses_full_export_span():
    period = period_for_lifetime(date(2018, 3, 15), date(2025, 11, 2))
    assert period.kind == "lifetime"
    assert period.start == date(2018, 3, 15)
    assert period.end == date(2025, 11, 2)
    assert period.label == "Lifetime"


def test_compute_share_summary_stats_lifetime_omits_lifers():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2020-01-10", species="Species a"),
            _row(sid="S2", dt="2024-06-01", species="Species b"),
            _row(sid="S3", dt="2024-12-31", species="Species c"),
        ]
    )
    period = period_for_lifetime(date(2020, 1, 10), date(2024, 12, 31))
    stats = compute_share_summary_stats(df, period)
    assert stats is not None
    assert stats.period_kind == "lifetime"
    assert stats.species == 3
    assert stats.checklists == 3
    assert stats.lifers is None


def test_compute_share_summary_stats_lifetime_longest_streak():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2020-01-01", species="Species a"),
            _row(sid="S2", dt="2020-01-02", species="Species a"),
            _row(sid="S3", dt="2020-01-03", species="Species a"),
            _row(sid="S4", dt="2020-06-01", species="Species b"),
        ]
    )
    period = period_for_lifetime(date(2020, 1, 1), date(2020, 12, 31))
    stats = compute_share_summary_stats(df, period)
    assert stats is not None
    assert stats.longest_streak == 3


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


def test_shared_checklists_and_days_birding_with_others():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-06-01", species="Species a", observers=2),
            _row(sid="S2", dt="2025-06-02", species="Species b", observers=2),
            _row(sid="S3", dt="2025-06-02", species="Species c", observers=1),
            _row(sid="S4", dt="2025-06-10", species="Species d", observers=1),
        ]
    )
    stats = compute_share_summary_stats(df, period_for_month(2025, 6))
    assert stats is not None
    assert stats.shared_checklists == 2
    assert stats.days_birding_with_others == 2


def test_shared_stats_none_without_observers_column():
    row = _row(sid="S1", dt="2025-06-01", species="Species a")
    del row["Number of Observers"]
    stats = compute_share_summary_stats(pd.DataFrame([row]), period_for_month(2025, 6))
    assert stats is not None
    assert stats.shared_checklists is None
    assert stats.days_birding_with_others is None


def test_resolve_period_current_and_previous_month():
    ref = date(2026, 6, 2)
    current = resolve_period("month", anchor="current", reference=ref)
    previous = resolve_period("month", anchor="previous", reference=ref)
    assert current.label == "June 2026"
    assert previous.label == "May 2026"


def test_resolve_period_previous_week():
    ref = date(2026, 6, 3)  # Wed in week May 31 – Jun 6
    previous = resolve_period("week", anchor="previous", reference=ref)
    assert previous.start == date(2026, 5, 24)
    assert previous.end == date(2026, 5, 30)


def test_period_for_previous_month_january():
    period = period_for_previous_month(2026, 1)
    assert period.label == "December 2025"


def test_period_for_previous_week_containing():
    period = period_for_previous_week_containing(date(2026, 6, 3))
    assert period.start == date(2026, 5, 24)
    assert period.end == date(2026, 5, 30)


def test_suggest_period_anchor_early_month():
    assert suggest_period_anchor("month", date(2026, 6, 2)) == "previous"
    assert suggest_period_anchor("month", date(2026, 6, 15)) == "current"


def test_suggest_period_anchor_weekend():
    assert suggest_period_anchor("week", date(2026, 6, 6)) == "current"  # Saturday
    assert suggest_period_anchor("week", date(2026, 6, 1)) == "previous"  # Monday


def test_summary_status_metrics_includes_all_time_stats():
    from explorer.core.share_summary_compute import ShareSummaryAllTimeStats, ShareSummaryStats

    stats = ShareSummaryStats(period_label="2025", period_kind="year", species=10)
    all_time = ShareSummaryAllTimeStats(
        total_species_taxa=10_800,
        observed_species_taxa=312,
        total_families_taxa=248,
        world_bird_coverage_pct=6.8,
    )
    pairs = dict(summary_status_metrics(stats, all_time=all_time))
    assert pairs["World bird species (from taxa)"] == "312"
    assert pairs["World bird families (from taxa)"] == "248"
    assert pairs["World bird coverage"] == "6.8%"


def test_compute_share_summary_all_time_stats_from_fixture(monkeypatch):
    from pathlib import Path

    from explorer.app.streamlit import bird_families_streamlit_html as bf
    from explorer.core.data_loader import load_dataset

    tax = pd.DataFrame(
        [
            {
                "scientific_name": "Anas gracilis",
                "common_name": "Grey Teal",
                "species_code": "grytea1",
                "taxon_order": 637.0,
                "base_species": "anas gracilis",
                "is_extinct": False,
            },
            {
                "scientific_name": "Cacatua galerita",
                "common_name": "Sulphur-crested Cockatoo",
                "species_code": "sulcoc2",
                "taxon_order": 12212.0,
                "base_species": "cacatua galerita",
                "is_extinct": False,
            },
        ]
    )
    groups = [
        {"group_name": "Waterfowl", "group_order": 1, "bounds": [(0.0, 1000.0)]},
        {"group_name": "Parrots", "group_order": 2, "bounds": [(12000.0, 13000.0)]},
    ]
    monkeypatch.setattr(bf, "_load_taxonomy_species_rows", lambda _loc: tax)
    monkeypatch.setattr(bf, "_load_taxonomy_groups", lambda _loc: groups)

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "ebird_integration_fixture.csv"
    df = load_dataset(fixture)
    assert df is not None and not df.empty
    all_time = compute_share_summary_all_time_stats(df, taxonomy_locale="en_AU")
    assert all_time is not None
    assert all_time.total_species_taxa == 2
    assert all_time.total_families_taxa == 2
    assert all_time.world_bird_coverage_pct is not None
    assert all_time.world_bird_coverage_pct > 0


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


def test_period_species_common_names_scoped_to_period():
    df = pd.DataFrame(
        [
            {**_row(sid="S1", dt="2025-06-01", species="Malurus cyaneus"), "Common Name": "Superb Fairywren"},
            {**_row(sid="S2", dt="2025-06-02", species="Trichoglossus moluccanus"), "Common Name": "Rainbow Lorikeet"},
            {**_row(sid="S3", dt="2024-01-01", species="Other sp"), "Common Name": "Outside Period"},
        ]
    )
    period = period_for_month(2025, 6)
    names = period_species_common_names(df, period)
    assert names == ["Rainbow Lorikeet", "Superb Fairywren"]
    name_map = period_species_name_map(df, period)
    assert name_map["Superb Fairywren"] == "Malurus cyaneus"

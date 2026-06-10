"""Tests for :mod:`explorer.presentation.share_summary_preview`."""

from explorer.core.checklist_stats_compute import ChecklistStatsPayload
from explorer.core.share_summary_compute import ShareSummaryStats
from explorer.presentation.share_summary_preview import (
    render_share_summary_export_html,
    render_share_summary_preview_html,
    sample_share_summary_stats,
    share_summary_stats_for_year,
)


def _minimal_payload(*, years: list[int], species_vals: list[str]) -> ChecklistStatsPayload:
    yearly_rows = [("Total species", species_vals)]
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
        years_list=years,
        yearly_rows=yearly_rows,
        incomplete_by_year={},
        country_sections=[],
    )


def test_share_summary_stats_for_year_extracts_species():
    payload = _minimal_payload(years=[2024, 2025], species_vals=["100", "312"])
    stats = share_summary_stats_for_year(payload, 2025)
    assert stats is not None
    assert stats.species == 312
    assert stats.period_label == "2025"
    assert stats.longest_streak is None


def test_share_summary_stats_for_year_counts_countries_from_sections():
    payload = _minimal_payload(years=[2025], species_vals=["10"])
    payload = ChecklistStatsPayload(
        **{
            **payload.__dict__,
            "country_sections": [
                ("AU", [2024, 2025], []),
                ("US", [2025], []),
                ("_UNKNOWN", [2025], []),
            ],
        }
    )
    stats = share_summary_stats_for_year(payload, 2025)
    assert stats is not None
    assert stats.countries == 2


def test_render_preview_includes_period_label_and_logo():
    html = render_share_summary_preview_html(sample_share_summary_stats(), layout="hero")
    assert "2025" in html
    assert "pebird-share-preview-wrap" in html
    assert "Personal eBird Explorer" in html


def test_render_export_html_full_size_document():
    html = render_share_summary_export_html(sample_share_summary_stats(), layout="hero", fmt="square")
    assert "<!DOCTYPE html>" in html
    assert "pebird-share-preview-wrap" not in html
    assert "width:1080px" in html
    assert "height:1080px" in html
    assert "data:image/svg+xml;base64," in html


def test_spotlight_layout_renders():
    stats = ShareSummaryStats(period_label="2025", period_kind="year", lifers=47)
    html = render_share_summary_preview_html(stats, layout="spotlight", spotlight_stat="lifers")
    assert "47" in html
    assert "Lifers" in html


def test_spotlight_species_label_by_period():
    from explorer.presentation.share_summary_preview import spotlight_species_label, spotlight_value

    year = ShareSummaryStats(period_label="2025", period_kind="year", species=312)
    assert spotlight_value(year, "species") == ("Year birds", "312")

    month = ShareSummaryStats(period_label="June 2025", period_kind="month", species=89)
    assert spotlight_value(month, "species") == ("Month birds", "89")

    week = ShareSummaryStats(period_label="May 31, 2025 - June 6, 2025", period_kind="week", species=34)
    assert spotlight_value(week, "species") == ("Week birds", "34")

    custom = ShareSummaryStats(period_label="1 – 7 June 2025", period_kind="custom", species=56)
    assert spotlight_value(custom, "species") == ("Species", "56")


def test_summary_status_metrics_includes_world_coverage():
    from explorer.presentation.share_summary_preview import summary_status_metrics

    stats = sample_share_summary_stats()
    metrics = summary_status_metrics(stats, world_bird_coverage_pct=6.8)
    assert metrics[-1] == ("World bird coverage", "6.8%")


def test_card_stat_pairs_year_includes_countries():
    from explorer.presentation.share_summary_preview import card_stat_pairs

    stats = sample_share_summary_stats(period_kind="year")
    labels = [lab for lab, _ in card_stat_pairs(stats, max_count=6)]
    assert "Countries" in labels
    assert "Birding days" in labels


def test_card_stat_pairs_hero_default_four():
    from explorer.presentation.share_summary_preview import card_stat_pairs

    stats = sample_share_summary_stats(period_kind="custom", trip_title="Trip")
    labels = [lab for lab, _ in card_stat_pairs(stats, max_count=4, layout="hero")]
    assert labels == ["Total species", "Lifers", "Total checklists", "Unique locations"]


def test_card_stat_pairs_tiles_includes_countries_and_birding_days():
    from explorer.presentation.share_summary_preview import card_stat_pairs

    stats = sample_share_summary_stats(period_kind="month")
    labels = [lab for lab, _ in card_stat_pairs(stats, max_count=6, layout="tiles")]
    assert labels == [
        "Total species",
        "Lifers",
        "Total checklists",
        "Unique locations",
        "Countries",
        "Birding days",
    ]


def test_trip_title_on_all_layouts():
    stats = ShareSummaryStats(
        period_label="1 – 7 June 2025",
        period_kind="custom",
        trip_title="North Coast NSW Exploration",
        species=56,
        lifers=3,
        checklists=8,
        locations=6,
        days_with_checklist=7,
        countries=2,
    )
    for layout in ("hero", "tiles", "minimal", "spotlight"):
        html = render_share_summary_preview_html(stats, layout=layout)
        assert "North Coast NSW Exploration" in html

    tiles_html = render_share_summary_preview_html(stats, layout="tiles")
    minimal_html = render_share_summary_preview_html(stats, layout="minimal")
    assert "My birding stats" not in tiles_html
    assert ">Summary</p>" not in minimal_html
    html = render_share_summary_preview_html(sample_share_summary_stats(), fmt="portrait_post")
    assert "1350px" in html

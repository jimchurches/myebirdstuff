"""Tests for Interesting Insights facts (#285)."""

import pandas as pd

from explorer.core.share_summary_compute import period_for_year
from explorer.core.share_summary_insight_facts import (
    ShareSummaryInsightFact,
    compute_insight_facts,
    format_insight_fact_metric,
    insight_fact_by_id,
    species_common_names_in_period,
)
from explorer.presentation.share_summary_preview import (
    render_share_summary_preview_html,
    resolve_insight_fact,
)


def _row(
    *,
    sid: str,
    dt: str,
    common: str,
    count: int | str = 1,
    scientific: str | None = None,
) -> dict:
    return {
        "Submission ID": sid,
        "Date": dt,
        "Scientific Name": scientific or common,
        "Common Name": common,
        "Count": count,
        "Location ID": "L1",
        "Location": "Test location",
        "Country": "AU",
    }


def test_compute_insight_facts_most_common_checklist_species():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Australian Magpie"),
            _row(sid="S2", dt="2025-02-01", common="Australian Magpie"),
            _row(sid="S3", dt="2025-03-01", common="Willie Wagtail"),
        ]
    )
    period = period_for_year(2025)
    facts = compute_insight_facts(df, period)
    top = insight_fact_by_id(facts, "most_common_checklist_species")
    assert top is not None
    assert top.primary_text == "Australian Magpie"
    assert top.metric_value == 2
    assert format_insight_fact_metric(top) == "2 checklists"


def test_compute_insight_facts_filters_period_and_non_countable_taxa():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Australian Magpie", count=2),
            _row(sid="S2", dt="2025-02-01", common="Australian Magpie", count=3),
            _row(sid="S3", dt="2024-03-01", common="Zebra Finch", count=999),
            _row(
                sid="S4",
                dt="2025-04-01",
                common="Mallard (Domestic type)",
                scientific="Anas platyrhynchos",
                count=500,
            ),
            _row(
                sid="S5",
                dt="2025-05-01",
                common="duck sp.",
                scientific="Anas sp.",
                count=600,
            ),
        ]
    )
    facts = compute_insight_facts(df, period_for_year(2025))
    by_id = {fact.fact_id: fact for fact in facts}
    assert by_id["most_common_checklist_species"].primary_text == "Australian Magpie"
    assert by_id["most_common_checklist_species"].metric_value == 2
    assert by_id["most_individuals_species"].primary_text == "Australian Magpie"
    assert by_id["most_individuals_species"].metric_value == 5
    assert by_id["biggest_checklist_count"].primary_text == "Australian Magpie"
    assert by_id["biggest_checklist_count"].metric_value == 3


def test_compute_insight_facts_most_individuals():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Wedge-tailed Shearwater", count=120),
            _row(sid="S1", dt="2025-01-01", common="Wedge-tailed Shearwater", count=80),
            _row(sid="S2", dt="2025-02-01", common="Australian Magpie", count=5),
        ]
    )
    facts = compute_insight_facts(df, period_for_year(2025))
    top = insight_fact_by_id(facts, "most_individuals_species")
    assert top is not None
    assert top.primary_text == "Wedge-tailed Shearwater"
    assert top.metric_value == 200


def test_compute_insight_facts_species_individuals_selected():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Lewin's Rail", count=40),
            _row(sid="S2", dt="2025-02-01", common="Lewin's Rail", count=26),
            _row(sid="S3", dt="2025-02-02", common="Lewin's Rail", count="X"),
            _row(sid="S3", dt="2025-03-01", common="Other Bird", count=1),
        ]
    )
    period = period_for_year(2025)
    facts = compute_insight_facts(df, period, species_common=" lewin's rail ")
    selected = insight_fact_by_id(facts, "species_individuals")
    assert selected is not None
    assert selected.label == "Species count"
    assert selected.primary_text == "Lewin's Rail"
    assert selected.metric_value == 66


def test_species_common_names_in_period_sorted():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Zebra Finch"),
            _row(sid="S2", dt="2025-02-01", common="Australian Magpie"),
        ]
    )
    names = species_common_names_in_period(df, period_for_year(2025))
    assert names == ("Australian Magpie", "Zebra Finch")


def test_species_common_names_in_period_excludes_non_countable():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Australian Magpie"),
            _row(
                sid="S2",
                dt="2025-02-01",
                common="Mallard (Domestic type)",
                scientific="Anas platyrhynchos",
            ),
            _row(sid="S3", dt="2025-03-01", common="duck sp.", scientific="Anas sp."),
        ]
    )
    names = species_common_names_in_period(df, period_for_year(2025))
    assert names == ("Australian Magpie",)


def test_insight_layout_renders():
    from explorer.core.share_summary_compute import ShareSummaryStats
    from explorer.core.share_summary_defaults import (
        SHARE_SUMMARY_LAYOUT_SUBTITLE_INSIGHT,
    )

    stats = ShareSummaryStats(period_label="2025", period_kind="year")
    fact = ShareSummaryInsightFact(
        fact_id="most_common_checklist_species",
        label="Most common checklist species",
        primary_text="Australian Magpie",
        metric_value=3999,
        metric_unit="checklists",
    )
    html = render_share_summary_preview_html(
        stats,
        layout="insight",
        insight_fact=fact,
        fmt="story",
    )
    assert SHARE_SUMMARY_LAYOUT_SUBTITLE_INSIGHT in html
    assert "<h1" in html
    assert "Most common checklist species" in html
    assert "Australian Magpie" in html
    assert "3,999 checklists" in html
    assert "linear-gradient(145deg" in html
    assert "<pre>" not in html.lower()
    assert "&lt;div" not in html


def test_insight_layout_escapes_insight_fact_text():
    from explorer.core.share_summary_compute import ShareSummaryStats

    stats = ShareSummaryStats(period_label="2025", period_kind="year")
    fact = ShareSummaryInsightFact(
        fact_id="most_common_checklist_species",
        label='Most <common> "checklist"',
        primary_text="<script>alert('magpie')</script>",
        metric_value=12,
        metric_unit="checklists",
    )
    html = render_share_summary_preview_html(
        stats,
        layout="insight",
        insight_fact=fact,
        fmt="story",
    )
    assert 'Most &lt;common&gt; "checklist"' in html
    assert "&lt;script&gt;alert('magpie')&lt;/script&gt;" in html
    assert "<script>alert" not in html


def test_insight_story_header_matches_tiles():
    from explorer.core.share_summary_compute import ShareSummaryStats

    stats = ShareSummaryStats(period_label="2026", period_kind="year")
    fact = ShareSummaryInsightFact(
        fact_id="biggest_checklist_count",
        label="Biggest single-checklist count",
        primary_text="Wedge-tailed Shearwater",
        metric_value=4200,
        metric_unit="on one checklist",
    )
    insight_html = render_share_summary_preview_html(
        stats,
        layout="insight",
        insight_fact=fact,
        fmt="story",
    )
    tiles = render_share_summary_preview_html(
        stats,
        layout="tiles",
        fmt="story",
        card_stat_labels=("Total species", "Lifers", "Total checklists", "Unique locations"),
    )
    insight_header_end = insight_html.index("</h1>") + len("</h1>")
    tiles_header_end = tiles.index("</h1>") + len("</h1>")
    header_marker = '<div style="padding:48px 56px 24px;text-align:center;">'
    insight_header = insight_html[insight_html.index(header_marker) : insight_header_end]
    tiles_header = tiles[tiles.index(header_marker) : tiles_header_end]
    assert insight_header == tiles_header


def test_resolve_insight_fact_uses_requested_id():
    facts = [
        ShareSummaryInsightFact(
            fact_id="most_common_checklist_species",
            label="Most common checklist species",
            primary_text="Magpie",
            metric_value=1,
            metric_unit="checklists",
        ),
        ShareSummaryInsightFact(
            fact_id="most_individuals_species",
            label="Most individuals of a single species",
            primary_text="Shearwater",
            metric_value=100,
            metric_unit="individuals",
        ),
    ]
    resolved = resolve_insight_fact(facts, "most_individuals_species")
    assert resolved is not None
    assert resolved.fact_id == "most_individuals_species"


def test_resolve_insight_fact_falls_back_to_default_then_first():
    default = ShareSummaryInsightFact(
        fact_id="most_common_checklist_species",
        label="Most common checklist species",
        primary_text="Magpie",
        metric_value=1,
        metric_unit="checklists",
    )
    first_without_default = ShareSummaryInsightFact(
        fact_id="biggest_checklist_count",
        label="Biggest single-checklist count",
        primary_text="Shearwater",
        metric_value=100,
        metric_unit="on one checklist",
    )
    assert resolve_insight_fact([first_without_default, default], "missing") == default
    assert resolve_insight_fact([first_without_default], "missing") == first_without_default
    assert resolve_insight_fact([], "missing") is None


def test_species_individuals_insight_fact_isolates_one_species():
    from explorer.core.share_summary_compute import period_for_year
    from explorer.core.share_summary_insight_facts import (
        species_individuals_insight_fact,
    )

    df = pd.DataFrame(
        {
            "Date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "Submission ID": ["s1", "s2", "s3"],
            "Count": [2, 5, 1],
            "Common Name": [
                "Australian Magpie",
                "Australian Magpie",
                "Superb Fairywren",
            ],
            "Scientific Name": [
                "Gymnorhina tibicen",
                "Gymnorhina tibicen",
                "Malurus cyaneus",
            ],
        }
    )
    fact = species_individuals_insight_fact(
        df, period_for_year(2025), "Australian Magpie"
    )
    assert fact is not None
    assert fact.fact_id == "species_individuals"
    assert fact.primary_text == "Australian Magpie"
    assert fact.metric_value == 7
    assert species_individuals_insight_fact(df, period_for_year(2025), "") is None
    assert (
        species_individuals_insight_fact(df, period_for_year(2024), "Australian Magpie")
        is None
    )


def _peak_row(
    *,
    sid: str,
    dt: str,
    common: str,
    count: int = 1,
    all_obs: str | int = 1,
    scientific: str | None = None,
) -> dict:
    return {
        "Submission ID": sid,
        "Date": dt,
        "Scientific Name": scientific or common,
        "Common Name": common,
        "Count": count,
        "All Obs Reported": all_obs,
        "Location ID": "L1",
        "Location": "Test location",
        "Country": "AU",
    }


def test_peak_year_facts_lifetime_only():
    from datetime import date

    from explorer.core.share_summary_compute import (
        period_for_lifetime,
        period_for_year,
    )
    from explorer.core.share_summary_insight_facts import peak_fact_ids_for_period_kind

    df = pd.DataFrame(
        [
            _peak_row(
                sid="S1",
                dt="2023-01-01",
                common="Australian Magpie",
                scientific="Gymnorhina tibicen",
                count=1,
            ),
            _peak_row(
                sid="S2",
                dt="2024-01-01",
                common="Australian Magpie",
                scientific="Gymnorhina tibicen",
                count=1,
            ),
            _peak_row(
                sid="S3",
                dt="2024-06-01",
                common="Willie Wagtail",
                scientific="Rhipidura leucophrys",
                count=10,
            ),
            _peak_row(
                sid="S4",
                dt="2025-01-01",
                common="Australian Magpie",
                scientific="Gymnorhina tibicen",
                count=1,
            ),
        ]
    )
    lifetime = period_for_lifetime(date(2023, 1, 1), date(2025, 12, 31))
    facts = compute_insight_facts(df, lifetime)
    year_checklists = insight_fact_by_id(facts, "year_most_checklists")
    assert year_checklists is not None
    assert year_checklists.primary_text == "2024"
    assert year_checklists.metric_value == 2
    assert year_checklists.label == "Best year for checklists"
    year_species = insight_fact_by_id(facts, "year_most_species")
    assert year_species is not None
    assert year_species.primary_text == "2024"
    assert year_species.metric_value == 2
    year_individuals = insight_fact_by_id(facts, "year_most_individuals")
    assert year_individuals is not None
    assert year_individuals.primary_text == "2024"
    assert year_individuals.metric_value == 11
    assert year_individuals.label == "Best year for individual birds"
    assert format_insight_fact_metric(year_individuals) == "11 individual birds"

    yearly = compute_insight_facts(df, period_for_year(2024))
    assert insight_fact_by_id(yearly, "year_most_checklists") is None
    assert "year_most_checklists" not in peak_fact_ids_for_period_kind("year")
    assert insight_fact_by_id(yearly, "month_most_checklists") is not None


def test_peak_month_and_day_gating():
    from datetime import date

    from explorer.core.share_summary_compute import (
        period_for_custom,
        period_for_lifetime,
        period_for_month,
        period_for_week_containing,
        period_for_year,
    )

    magpie = dict(common="Australian Magpie", scientific="Gymnorhina tibicen")
    wagtail = dict(common="Willie Wagtail", scientific="Rhipidura leucophrys")
    finch = dict(common="Zebra Finch", scientific="Taeniopygia guttata")
    df = pd.DataFrame(
        [
            _peak_row(sid="S1", dt="2025-01-01", count=1, **magpie),
            _peak_row(sid="S2", dt="2025-01-01", count=2, **wagtail),
            _peak_row(sid="S3", dt="2025-03-15", count=1, **magpie),
            _peak_row(sid="S4", dt="2025-03-15", count=1, **wagtail),
            _peak_row(sid="S5", dt="2025-03-15", count=5, **finch),
        ]
    )
    yearly = compute_insight_facts(df, period_for_year(2025))
    month = insight_fact_by_id(yearly, "month_most_checklists")
    assert month is not None
    assert month.primary_text == "Mar 2025"
    assert month.metric_value == 3
    day = insight_fact_by_id(yearly, "day_most_species")
    assert day is not None
    assert day.primary_text == "15 Mar 2025"
    assert day.metric_value == 3

    monthly = compute_insight_facts(df, period_for_month(2025, 3))
    assert insight_fact_by_id(monthly, "month_most_checklists") is None
    assert insight_fact_by_id(monthly, "day_most_checklists") is not None

    lifetime = compute_insight_facts(
        df, period_for_lifetime(date(2025, 1, 1), date(2025, 12, 31))
    )
    assert insight_fact_by_id(lifetime, "day_most_checklists") is not None
    assert insight_fact_by_id(lifetime, "month_most_checklists") is None

    week = compute_insight_facts(df, period_for_week_containing(date(2025, 3, 15)))
    assert insight_fact_by_id(week, "day_most_checklists") is None
    custom = compute_insight_facts(
        df, period_for_custom(date(2025, 3, 1), date(2025, 3, 31))
    )
    assert insight_fact_by_id(custom, "day_most_checklists") is None


def test_peak_checklists_all_vs_completed_and_tie_earliest():
    from datetime import date

    from explorer.core.share_summary_compute import period_for_lifetime

    magpie = dict(common="Australian Magpie", scientific="Gymnorhina tibicen")
    df = pd.DataFrame(
        [
            # 2023: 2 all, 2 completed
            _peak_row(sid="A1", dt="2023-01-01", all_obs=1, **magpie),
            _peak_row(sid="A2", dt="2023-02-01", all_obs=1, **magpie),
            # 2024: 3 all, 1 completed — wins all; loses completed
            _peak_row(sid="B1", dt="2024-01-01", all_obs=1, **magpie),
            _peak_row(sid="B2", dt="2024-02-01", all_obs=0, **magpie),
            _peak_row(sid="B3", dt="2024-03-01", all_obs=0, **magpie),
            # 2025: 2 all, 2 completed — ties 2023 on completed; earliest year wins
            _peak_row(sid="C1", dt="2025-01-01", all_obs=1, **magpie),
            _peak_row(sid="C2", dt="2025-02-01", all_obs=1, **magpie),
        ]
    )
    facts = compute_insight_facts(
        df, period_for_lifetime(date(2023, 1, 1), date(2025, 12, 31))
    )
    all_cl = insight_fact_by_id(facts, "year_most_checklists")
    assert all_cl is not None
    assert all_cl.primary_text == "2024"
    assert all_cl.metric_value == 3
    assert all_cl.peak_tied is False

    completed = insight_fact_by_id(facts, "year_most_completed_checklists")
    assert completed is not None
    assert completed.primary_text == "2023"
    assert completed.metric_value == 2
    assert completed.peak_tied is True
    assert format_insight_fact_metric(completed) == "2 checklists"

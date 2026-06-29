"""Tests for rich Spotlight facts (#285)."""


import pandas as pd

from explorer.core.share_summary_compute import period_for_year
from explorer.core.share_summary_spotlight_facts import (
    ShareSummarySpotlightFact,
    compute_spotlight_facts,
    format_spotlight_fact_metric,
    species_common_names_in_period,
    spotlight_fact_by_id,
)
from explorer.presentation.share_summary_preview import (
    render_share_summary_preview_html,
    resolve_spotlight_fact,
)


def _row(*, sid: str, dt: str, common: str, count: int = 1) -> dict:
    return {
        "Submission ID": sid,
        "Date": dt,
        "Scientific Name": common,
        "Common Name": common,
        "Count": count,
        "Location ID": "L1",
        "Location": "Test location",
        "Country": "AU",
    }


def test_compute_spotlight_facts_most_common_checklist_species():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Australian Magpie"),
            _row(sid="S2", dt="2025-02-01", common="Australian Magpie"),
            _row(sid="S3", dt="2025-03-01", common="Willie Wagtail"),
        ]
    )
    period = period_for_year(2025)
    facts = compute_spotlight_facts(df, period)
    top = spotlight_fact_by_id(facts, "most_common_checklist_species")
    assert top is not None
    assert top.primary_text == "Australian Magpie"
    assert top.metric_value == 2
    assert format_spotlight_fact_metric(top) == "2 checklists"


def test_compute_spotlight_facts_most_individuals():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Wedge-tailed Shearwater", count=120),
            _row(sid="S1", dt="2025-01-01", common="Wedge-tailed Shearwater", count=80),
            _row(sid="S2", dt="2025-02-01", common="Australian Magpie", count=5),
        ]
    )
    facts = compute_spotlight_facts(df, period_for_year(2025))
    top = spotlight_fact_by_id(facts, "most_individuals_species")
    assert top is not None
    assert top.primary_text == "Wedge-tailed Shearwater"
    assert top.metric_value == 200


def test_compute_spotlight_facts_species_individuals_selected():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Lewin's Rail", count=40),
            _row(sid="S2", dt="2025-02-01", common="Lewin's Rail", count=26),
            _row(sid="S3", dt="2025-03-01", common="Other Bird", count=1),
        ]
    )
    period = period_for_year(2025)
    facts = compute_spotlight_facts(df, period, species_common="Lewin's Rail")
    selected = spotlight_fact_by_id(facts, "species_individuals")
    assert selected is not None
    assert selected.primary_text == "Lewin's Rail"
    assert selected.metric_value == 66
    assert "Lewin's Rail" in selected.label


def test_species_common_names_in_period_sorted():
    df = pd.DataFrame(
        [
            _row(sid="S1", dt="2025-01-01", common="Zebra Finch"),
            _row(sid="S2", dt="2025-02-01", common="Australian Magpie"),
        ]
    )
    names = species_common_names_in_period(df, period_for_year(2025))
    assert names == ("Australian Magpie", "Zebra Finch")


def test_spotlight_rich_layout_renders():
    from explorer.core.share_summary_compute import ShareSummaryStats

    stats = ShareSummaryStats(period_label="2025", period_kind="year")
    fact = ShareSummarySpotlightFact(
        fact_id="most_common_checklist_species",
        label="Most common checklist species",
        primary_text="Australian Magpie",
        metric_value=3999,
        metric_unit="checklists",
    )
    html = render_share_summary_preview_html(
        stats,
        layout="spotlight",
        spotlight_mode="rich",
        spotlight_fact=fact,
    )
    assert "Most common checklist species" in html
    assert "Australian Magpie" in html
    assert "3,999 checklists" in html
    assert "<pre>" not in html.lower()
    assert "&lt;div" not in html


def test_resolve_spotlight_fact_falls_back_to_default():
    facts = [
        ShareSummarySpotlightFact(
            fact_id="most_common_checklist_species",
            label="Most common checklist species",
            primary_text="Magpie",
            metric_value=1,
            metric_unit="checklists",
        ),
        ShareSummarySpotlightFact(
            fact_id="most_individuals_species",
            label="Most individuals of a single species",
            primary_text="Shearwater",
            metric_value=100,
            metric_unit="individuals",
        ),
    ]
    resolved = resolve_spotlight_fact(facts, "most_individuals_species")
    assert resolved is not None
    assert resolved.fact_id == "most_individuals_species"

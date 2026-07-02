"""Tests for Social Cards Streamlit helpers (#327)."""

from __future__ import annotations

from explorer.app.streamlit.social_cards_streamlit_helpers import (
    card_stat_data_scope_from_session_export,
    png_export_fingerprint,
)
from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.core.share_summary_insight_facts import ShareSummaryInsightFact


def _base_png_fingerprint_kwargs() -> dict:
    return {
        "stats": ShareSummaryStats(
            period_label="2025",
            period_kind="year",
            checklists=10,
            species=42,
            lifers=3,
            individuals=100,
        ),
        "layout": "tiles",
        "fmt": "square",
        "spotlight_label": "Species",
        "all_time": ShareSummaryAllTimeStats(
            observed_species_taxa=42,
            total_species_taxa=10_800,
            world_bird_coverage_pct=0.39,
        ),
        "color_scheme_index": 0,
        "scope_label": "World",
        "geo_scope": ShareSummaryGeoScope(),
        "tiles_presentation": "grid",
        "spotlight_presentation": "classic",
        "insight_fact": None,
    }


def test_card_stat_data_scope_from_session_export_uses_export_source():
    scope = card_stat_data_scope_from_session_export(
        period_kind="year",
        period_label="2025",
        geo_scope=ShareSummaryGeoScope(country_key="AU"),
        fmt="portrait",
        tiles_presentation="circles",
    )
    assert scope.startswith("export|")
    assert "AU" in scope or "au" in scope.lower() or "|" in scope


def test_png_export_fingerprint_changes_when_stat_picks_change():
    base_kwargs = _base_png_fingerprint_kwargs()
    fp_a = png_export_fingerprint(**base_kwargs, card_stat_labels=("Species", "Checklists"))
    fp_b = png_export_fingerprint(**base_kwargs, card_stat_labels=("Checklists", "Species"))
    assert fp_a != fp_b


def test_png_export_fingerprint_changes_when_visible_stat_value_changes():
    base_kwargs = _base_png_fingerprint_kwargs()
    changed_lifers = ShareSummaryStats(
        period_label="2025",
        period_kind="year",
        checklists=10,
        species=42,
        lifers=4,
        individuals=100,
    )

    fp_a = png_export_fingerprint(**base_kwargs, card_stat_labels=("Lifers",))
    fp_b = png_export_fingerprint(
        **{**base_kwargs, "stats": changed_lifers},
        card_stat_labels=("Lifers",),
    )

    assert fp_a != fp_b


def test_png_export_fingerprint_changes_when_scheme_values_change(monkeypatch):
    from explorer.core.share_summary_defaults import SHARE_SUMMARY_COLOR_SCHEMES

    base_kwargs = _base_png_fingerprint_kwargs()
    fp_a = png_export_fingerprint(**base_kwargs, card_stat_labels=("Species",))
    monkeypatch.setitem(SHARE_SUMMARY_COLOR_SCHEMES[0], "tile_bg", "#abcdef")

    fp_b = png_export_fingerprint(**base_kwargs, card_stat_labels=("Species",))

    assert fp_a != fp_b


def test_png_export_fingerprint_includes_insight_fact():
    stats = ShareSummaryStats(
        period_label="2025",
        period_kind="year",
        checklists=1,
        species=1,
        individuals=1,
    )
    fact = ShareSummaryInsightFact(
        fact_id="biggest_checklist_count",
        label="Biggest day",
        primary_text="42 species on one checklist",
        metric_value=42,
        metric_unit="species",
    )
    kwargs = {
        "stats": stats,
        "layout": "insight",
        "fmt": "square",
        "card_stat_labels": (),
        "spotlight_label": "Species",
        "all_time": None,
        "color_scheme_index": 1,
        "scope_label": "World",
        "geo_scope": ShareSummaryGeoScope(),
        "tiles_presentation": "grid",
        "spotlight_presentation": "classic",
    }
    without = png_export_fingerprint(**kwargs, insight_fact=None)
    with_fact = png_export_fingerprint(**kwargs, insight_fact=fact)
    assert without != with_fact

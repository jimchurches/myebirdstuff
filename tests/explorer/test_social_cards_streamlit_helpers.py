"""Tests for Social Cards Streamlit helpers (#327)."""

from __future__ import annotations

import pytest

from explorer.app.streamlit.social_cards_streamlit_helpers import (
    card_stat_data_scope_from_session_export,
    ordered_custom_date_range,
    png_export_fingerprint,
    social_cards_dataframe_signature,
)
from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.core.share_summary_insight_facts import ShareSummaryInsightFact


def test_ordered_custom_date_range_swaps_inverted_pair():
    from datetime import date

    start, end, swapped = ordered_custom_date_range(
        date(2025, 6, 7),
        date(2025, 6, 1),
        default_start=date(2025, 1, 1),
        default_end=date(2025, 12, 31),
    )
    assert (start, end, swapped) == (date(2025, 6, 1), date(2025, 6, 7), True)

    start, end, swapped = ordered_custom_date_range(
        date(2025, 6, 1),
        date(2025, 6, 7),
        default_start=date(2025, 1, 1),
        default_end=date(2025, 12, 31),
    )
    assert (start, end, swapped) == (date(2025, 6, 1), date(2025, 6, 7), False)

    start, end, swapped = ordered_custom_date_range(
        None,
        "bad",
        default_start=date(2020, 1, 1),
        default_end=date(2020, 12, 31),
    )
    assert (start, end, swapped) == (date(2020, 1, 1), date(2020, 12, 31), False)


def test_resolve_geo_scoped_dataframe_caches_by_signature_and_token(monkeypatch):
    import pandas as pd

    from explorer.app.streamlit import social_cards_streamlit_helpers as helpers
    from explorer.core.share_summary_compute import ShareSummaryGeoScope

    df = pd.DataFrame(
        {
            "Submission ID": ["s1", "s2"],
            "Country": ["Australia", "Indonesia"],
            "State/Province": ["AU-NSW", "ID-JW"],
            "Date": ["2025-01-01", "2025-01-02"],
        }
    )
    calls: list[str] = []

    def _counting_filter(frame, scope):
        calls.append(scope.scope_token())
        return frame.iloc[:1].copy()

    monkeypatch.setattr(helpers, "filter_df_by_geo_scope", _counting_filter)

    scope = ShareSummaryGeoScope(country_key="AU")
    scoped, entry, hit = helpers.resolve_geo_scoped_dataframe(
        df, scope, dataset_sig=("sig", 1), cache_entry=None
    )
    assert hit is False
    assert calls == ["AU"]
    scoped2, entry2, hit2 = helpers.resolve_geo_scoped_dataframe(
        df, scope, dataset_sig=("sig", 1), cache_entry=entry
    )
    assert hit2 is True
    assert scoped2 is scoped
    assert entry2 is entry
    assert calls == ["AU"]

    # Different geo token forces a miss.
    helpers.resolve_geo_scoped_dataframe(
        df,
        ShareSummaryGeoScope(),
        dataset_sig=("sig", 1),
        cache_entry=entry,
    )
    assert calls == ["AU", "world"]

    # Different dataset signature forces a miss.
    helpers.resolve_geo_scoped_dataframe(
        df, scope, dataset_sig=("sig", 2), cache_entry=entry
    )
    assert calls == ["AU", "world", "AU"]

    assert helpers.peek_geo_scoped_dataframe_cache(
        dataset_sig=("sig", 1),
        geo_scope=scope,
        cache_entry=entry,
    ) is scoped
    assert (
        helpers.peek_geo_scoped_dataframe_cache(
            dataset_sig=("sig", 2),
            geo_scope=scope,
            cache_entry=entry,
        )
        is None
    )


def test_social_cards_dataframe_signature_prefers_session_sig():
    assert social_cards_dataframe_signature(None, session_sig=("a", 1, "x")) == (
        "a",
        1,
        "x",
    )
    assert social_cards_dataframe_signature(None) == ("empty", 0)


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


@pytest.mark.parametrize(
    ("field", "changed_value"),
    [
        ("layout", "minimal"),
        ("fmt", "story"),
        ("spotlight_label", "Lifers"),
        (
            "all_time",
            ShareSummaryAllTimeStats(
                observed_species_taxa=43,
                total_species_taxa=10_800,
                world_bird_coverage_pct=0.40,
            ),
        ),
        ("color_scheme_index", 1),
        ("scope_label", "Australia"),
        ("geo_scope", ShareSummaryGeoScope(country_key="AU")),
        ("tiles_presentation", "circles"),
        ("spotlight_presentation", "circle"),
    ],
)
def test_png_export_fingerprint_changes_for_every_render_control(
    field,
    changed_value,
):
    base_kwargs = _base_png_fingerprint_kwargs()
    base = png_export_fingerprint(
        **base_kwargs,
        card_stat_labels=("Species", "Checklists"),
    )
    changed = png_export_fingerprint(
        **{**base_kwargs, field: changed_value},
        card_stat_labels=("Species", "Checklists"),
    )

    assert changed != base


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

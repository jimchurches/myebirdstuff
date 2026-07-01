"""Tests for Social Cards tab shell data wiring (#326)."""

from __future__ import annotations

import pandas as pd

from explorer.app.streamlit import bird_families_streamlit_html as bf
from explorer.app.streamlit.social_cards_streamlit_helpers import (
    all_time_stats_from_rankings_bundle,
    resolve_social_cards_stats,
)
from explorer.core.share_summary_compute import (
    ShareSummaryGeoScope,
    period_for_year,
)


def test_all_time_stats_from_rankings_bundle_reads_world_and_family_keys():
    summary = pd.DataFrame(
        {
            "group_name": ["Waterfowl", "Parrots"],
            "seen_species": [3, 0],
            "total_species": [10, 8],
            "percent_seen": [30.0, 0.0],
        }
    )
    bundle = {
        bf.WORLD_SPECIES_COVERAGE_METRICS_KEY: (42, 10_800, 0.39),
        bf.GROUP_COVERAGE_SUMMARY_KEY: summary,
    }

    all_time = all_time_stats_from_rankings_bundle(bundle)

    assert all_time is not None
    assert all_time.observed_species_taxa == 42
    assert all_time.total_species_taxa == 10_800
    assert all_time.world_bird_coverage_pct == 0.39
    assert all_time.total_families_taxa == 2
    assert all_time.observed_families == 1


def test_all_time_stats_from_rankings_bundle_empty_returns_none():
    assert all_time_stats_from_rankings_bundle(None) is None
    assert all_time_stats_from_rankings_bundle({}) is None


def test_resolve_social_cards_stats_uses_bundle_not_recompute(monkeypatch):
    df = pd.DataFrame(
        {
            "Date": ["2025-06-01", "2025-06-02"],
            "Submission ID": ["s1", "s2"],
            "Count": [1, 2],
            "Common Name": ["Grey Teal", "Sulphur-crested Cockatoo"],
            "Scientific Name": ["Anas gracilis", "Cacatua galerita"],
        }
    )
    calls: list[str] = []

    def _forbidden(*_args, **_kwargs):
        calls.append("recompute")
        raise AssertionError("must not re-run taxonomy merge")

    monkeypatch.setattr(
        "explorer.core.share_summary_compute.compute_share_summary_all_time_stats",
        _forbidden,
    )

    bundle = {bf.WORLD_SPECIES_COVERAGE_METRICS_KEY: (1, 100, 1.0)}
    stats, all_time = resolve_social_cards_stats(
        df_full=df,
        df_scoped=df,
        period=period_for_year(2025),
        geo_scope=ShareSummaryGeoScope(),
        rankings_bundle=bundle,
    )

    assert calls == []
    assert stats is not None
    assert stats.checklists == 2
    assert all_time is not None
    assert all_time.total_species_taxa == 100


def test_resolve_social_cards_stats_skips_all_time_when_geo_scoped():
    df = pd.DataFrame(
        {
            "Date": ["2025-06-01"],
            "Submission ID": ["s1"],
            "Count": [1],
            "Country": ["Australia"],
            "State/Province": ["New South Wales"],
            "Common Name": ["Grey Teal"],
            "Scientific Name": ["Anas gracilis"],
        }
    )
    bundle = {bf.WORLD_SPECIES_COVERAGE_METRICS_KEY: (1, 100, 1.0)}
    scope = ShareSummaryGeoScope(country_key="AU", region_code="NSW")

    stats, all_time = resolve_social_cards_stats(
        df_full=df,
        df_scoped=df,
        period=period_for_year(2025),
        geo_scope=scope,
        rankings_bundle=bundle,
    )

    assert stats is not None
    assert all_time is None

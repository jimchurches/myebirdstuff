"""Tests for Social Cards tab shell data wiring (#326)."""

from __future__ import annotations

import pandas as pd

from explorer.app.streamlit import bird_families_streamlit_html as bf
from explorer.core.share_summary_compute import (
    GROUP_COVERAGE_SUMMARY_KEY,
    WORLD_SPECIES_COVERAGE_METRICS_KEY,
    ShareSummaryGeoScope,
    all_time_stats_from_rankings_bundle,
    period_for_year,
    resolve_social_cards_stats,
    world_taxonomy_bundle_status,
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
        WORLD_SPECIES_COVERAGE_METRICS_KEY: (42, 10_800, 0.39),
        GROUP_COVERAGE_SUMMARY_KEY: summary,
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


def test_resolve_social_cards_stats_uses_scoped_export_and_bundle_not_recompute(
    monkeypatch,
):
    df_full = pd.DataFrame(
        {
            "Date": ["2025-06-01", "2025-06-02"],
            "Submission ID": ["s1", "s2"],
            "Count": [1, 2],
            "Common Name": ["Grey Teal", "Sulphur-crested Cockatoo"],
            "Scientific Name": ["Anas gracilis", "Cacatua galerita"],
        }
    )
    df_scoped = df_full.iloc[[0]].copy()
    calls: list[str] = []

    def _forbidden(label: str):
        calls.append(label)
        raise AssertionError("must not re-run taxonomy merge")

    monkeypatch.setattr(
        "explorer.core.share_summary_compute.compute_share_summary_all_time_stats",
        lambda *_args, **_kwargs: _forbidden("compute_share_summary_all_time_stats"),
    )
    monkeypatch.setattr(
        bf,
        "build_group_coverage_tables",
        lambda *_args, **_kwargs: _forbidden("build_group_coverage_tables"),
    )

    bundle = {WORLD_SPECIES_COVERAGE_METRICS_KEY: (1, 100, 1.0)}
    stats, all_time = resolve_social_cards_stats(
        df_full=df_full,
        df_scoped=df_scoped,
        period=period_for_year(2025),
        geo_scope=ShareSummaryGeoScope(),
        rankings_bundle=bundle,
    )

    assert calls == []
    assert stats is not None
    assert stats.checklists == 1
    assert stats.species == 1
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
    bundle = {WORLD_SPECIES_COVERAGE_METRICS_KEY: (1, 100, 1.0)}
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


def test_world_taxonomy_bundle_status_pending_when_bundle_missing():
    assert world_taxonomy_bundle_status(None) == "pending"


def test_world_taxonomy_bundle_status_ready_when_metrics_present():
    bundle = {WORLD_SPECIES_COVERAGE_METRICS_KEY: (1, 100, 1.0)}
    assert world_taxonomy_bundle_status(bundle) == "ready"


def test_world_taxonomy_bundle_status_unavailable_when_bundle_empty():
    assert world_taxonomy_bundle_status({}) == "unavailable"

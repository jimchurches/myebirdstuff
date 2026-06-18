"""Tests for design share summary app helpers."""

from explorer.app.streamlit.design_share_summary_app import (
    _card_stat_data_scope,
    _design_sample_dataset,
    _period_has_checklist_data,
)
from explorer.core.share_summary_compute import (
    ShareSummaryGeoScope,
    ShareSummaryStats,
    geo_country_keys_from_df,
    geo_region_options_for_country,
)


def test_card_stat_data_scope_changes_when_source_or_period_changes():
    sample = _card_stat_data_scope(
        use_sample=True,
        period_kind="month",
        period_label="June 2025",
        upload_name=None,
    )
    csv = _card_stat_data_scope(
        use_sample=False,
        period_kind="month",
        period_label="June 2025",
        upload_name="MyEBirdData.csv",
    )
    other_month = _card_stat_data_scope(
        use_sample=False,
        period_kind="month",
        period_label="May 2025",
        upload_name="MyEBirdData.csv",
    )
    assert sample != csv
    assert csv != other_month


def test_card_stat_data_scope_changes_when_geo_scope_changes():
    world = _card_stat_data_scope(
        use_sample=False,
        period_kind="year",
        period_label="2025",
        upload_name="MyEBirdData.csv",
        geo_scope=ShareSummaryGeoScope(),
    )
    country = _card_stat_data_scope(
        use_sample=False,
        period_kind="year",
        period_label="2025",
        upload_name="MyEBirdData.csv",
        geo_scope=ShareSummaryGeoScope(country_key="AU-NSW"),
    )
    assert world != country


def test_design_sample_dataset_has_expected_geo_options():
    df = _design_sample_dataset()
    countries = geo_country_keys_from_df(df)
    assert countries == ["AU", "IN"]
    au_regions = [code for code, _ in geo_region_options_for_country(df, "AU")]
    assert set(au_regions) == {"NSW", "QLD"}
    in_regions = [code for code, _ in geo_region_options_for_country(df, "IN")]
    assert in_regions == ["GA"]


def test_period_has_checklist_data():
    assert _period_has_checklist_data(
        ShareSummaryStats(period_label="June 2025", period_kind="month", checklists=3)
    )
    assert not _period_has_checklist_data(
        ShareSummaryStats(period_label="June 2026", period_kind="month")
    )
    assert not _period_has_checklist_data(
        ShareSummaryStats(period_label="June 2026", period_kind="month", checklists=0)
    )

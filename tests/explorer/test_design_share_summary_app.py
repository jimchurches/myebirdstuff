"""Tests for design share summary app helpers."""

from explorer.app.streamlit.design_share_summary_app import (
    _card_stat_data_scope,
    _period_has_checklist_data,
)
from explorer.core.share_summary_compute import ShareSummaryStats


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

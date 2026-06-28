"""Tests for design share summary app helpers."""

from explorer.app.streamlit.design_share_summary_app import (
    _card_stat_data_scope,
    _card_stat_ui_row_count,
    _default_card_stat_slot_count,
    _design_sample_dataset,
    _period_has_checklist_data,
    _resolve_card_stat_selectbox_value,
)
from explorer.core.share_summary_compute import (
    ShareSummaryGeoScope,
    ShareSummaryStats,
    geo_country_keys_from_df,
    geo_region_options_for_country,
)


def test_card_stat_ui_row_count_clamps_slot_count_to_layout_limit():
    assert _card_stat_ui_row_count("tiles", "story", slot_count=4) == 4
    assert _card_stat_ui_row_count("minimal", "story", slot_count=6) == 6
    assert _card_stat_ui_row_count("tiles", "story", slot_count=14) == 14
    assert _card_stat_ui_row_count("tiles", "story", slot_count=16) == 14
    assert _card_stat_ui_row_count("tiles", "story", slot_count=2) == 4
    assert _card_stat_ui_row_count("tiles", "portrait_post", slot_count=9) == 8
    assert _card_stat_ui_row_count("tiles", "portrait_post", slot_count=3) == 4
    assert (
        _card_stat_ui_row_count(
            "tiles",
            "square",
            slot_count=8,
            tiles_presentation="circles",
        )
        == 6
    )
    assert (
        _card_stat_ui_row_count(
            "tiles",
            "portrait_post",
            slot_count=12,
            tiles_presentation="circles",
        )
        == 8
    )
    assert (
        _card_stat_ui_row_count(
            "tiles",
            "story",
            slot_count=12,
            tiles_presentation="circles",
        )
        == 10
    )


def test_layout_grid_stat_default_count():
    from explorer.presentation.share_summary_preview import (
        layout_grid_stat_default_count,
    )

    assert layout_grid_stat_default_count("square") == 4
    assert layout_grid_stat_default_count("portrait_post") == 6
    assert layout_grid_stat_default_count("story") == 6


def test_default_card_stat_slot_count():
    assert _default_card_stat_slot_count(
        circle_cluster=True,
        defaults=["A", "B", "C", "D", "E", "F"],
        max_slots=10,
        layout="tiles",
        fmt="story",
    ) == 6
    assert _default_card_stat_slot_count(
        circle_cluster=False,
        defaults=["A", "B", "C", "D", "E", "F"],
        max_slots=10,
        layout="tiles",
        fmt="square",
        tiles_presentation="grid",
    ) == 4
    assert _default_card_stat_slot_count(
        circle_cluster=False,
        defaults=["A", "B", "C", "D", "E", "F"],
        max_slots=10,
        layout="tiles",
        fmt="portrait_post",
        tiles_presentation="grid",
    ) == 6
    assert _default_card_stat_slot_count(
        circle_cluster=False,
        defaults=["A", "B", "C", "D", "E", "F"],
        max_slots=10,
        layout="tiles",
        fmt="story",
        tiles_presentation="grid",
    ) == 6
    assert _default_card_stat_slot_count(
        circle_cluster=False,
        defaults=["A", "B", "C", "D"],
        max_slots=10,
        layout="minimal",
        fmt="story",
    ) == 4
    assert _default_card_stat_slot_count(
        circle_cluster=False,
        defaults=[],
        max_slots=6,
        layout="minimal",
        fmt="square",
    ) == 1


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
    assert sample == "sample|month|June 2025|world|square|grid"
    assert csv == "MyEBirdData.csv|month|June 2025|world|square|grid"
    assert other_month == "MyEBirdData.csv|month|May 2025|world|square|grid"
    assert sample != csv
    assert csv != other_month
    assert (
        _card_stat_data_scope(
            use_sample=True,
            period_kind="month",
            period_label="June 2025",
            upload_name=None,
        )
        == sample
    )


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
    assert world == "MyEBirdData.csv|year|2025|world|square|grid"
    assert country == "MyEBirdData.csv|year|2025|AU-NSW|square|grid"
    assert world != country


def test_card_stat_data_scope_changes_when_format_or_presentation_changes():
    square = _card_stat_data_scope(
        use_sample=True,
        period_kind="year",
        period_label="2025",
        upload_name=None,
        fmt="square",
    )
    story = _card_stat_data_scope(
        use_sample=True,
        period_kind="year",
        period_label="2025",
        upload_name=None,
        fmt="story",
    )
    circles = _card_stat_data_scope(
        use_sample=True,
        period_kind="year",
        period_label="2025",
        upload_name=None,
        fmt="story",
        tiles_presentation="circles",
    )
    assert square != story
    assert story != circles


def test_resolve_card_stat_selectbox_value_prefers_widget_over_stale_pick():
    options = ["", "Lifers", "Australia Lifers", "Total species"]
    assert (
        _resolve_card_stat_selectbox_value(
            session_value="Australia Lifers",
            desired="Lifers",
            options=options,
        )
        == "Australia Lifers"
    )
    assert (
        _resolve_card_stat_selectbox_value(
            session_value="Countries",
            desired="Lifers",
            options=options,
        )
        == "Lifers"
    )


def test_design_sample_dataset_has_expected_geo_options():
    from datetime import date

    df = _design_sample_dataset(date.today().year)
    countries = geo_country_keys_from_df(df)
    assert countries == ["AU", "IN"]
    au_regions = [code for code, _ in geo_region_options_for_country(df, "AU")]
    assert set(au_regions) == {"NSW", "QLD"}
    in_regions = [code for code, _ in geo_region_options_for_country(df, "IN")]
    assert in_regions == ["GA"]


def test_design_sample_dataset_has_checklists_for_current_year():
    from datetime import date

    from explorer.core.share_summary_compute import compute_share_summary_stats, period_for_year

    year = date.today().year
    df = _design_sample_dataset(year)
    stats = compute_share_summary_stats(df, period_for_year(year))
    assert stats is not None
    assert stats.checklists == 4
    assert stats.species == 12
    assert stats.individuals == 24
    assert stats.completed_checklists == 4
    assert stats.incidental_checklists == 0
    assert stats.locations == 4
    assert stats.countries == 2
    assert stats.birding_hours == 4.0
    assert stats.days_with_checklist == 4


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

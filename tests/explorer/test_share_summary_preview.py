"""Tests for :mod:`explorer.presentation.share_summary_preview`."""

from explorer.core.checklist_stats_compute import ChecklistStatsPayload
from explorer.core.share_summary_compute import ShareSummaryAllTimeStats, ShareSummaryStats
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


def test_share_summary_color_scheme_ids_light_and_dark():
    from explorer.core.share_summary_defaults import (
        SHARE_SUMMARY_COLOR_SCHEME_IDS,
        share_summary_color_scheme_label,
    )

    assert SHARE_SUMMARY_COLOR_SCHEME_IDS == ("light", "dark")
    assert share_summary_color_scheme_label("light") == "Light"
    assert share_summary_color_scheme_label("dark") == "Dark"


def test_preview_color_scheme_index_changes_palette():
    from explorer.core.share_summary_defaults import SHARE_SUMMARY_COLOR_SCHEMES

    stats = sample_share_summary_stats()
    light = render_share_summary_preview_html(stats, layout="hero", color_scheme_index=0)
    dark = render_share_summary_preview_html(stats, layout="hero", color_scheme_index=1)
    assert SHARE_SUMMARY_COLOR_SCHEMES[0]["bg"] in light
    assert SHARE_SUMMARY_COLOR_SCHEMES[1]["bg"] in dark
    assert light != dark


def test_layout_card_stat_max_story_supports_ten():
    from explorer.presentation.share_summary_preview import layout_card_stat_max

    assert layout_card_stat_max("minimal", "story") == 10
    assert layout_card_stat_max("tiles", "story") == 10
    assert layout_card_stat_max("minimal", "square") == 6
    assert layout_card_stat_max("tiles", "square") == 6
    assert layout_card_stat_max("hero", "story") == 4


def test_minimal_story_renders_extra_selected_stats():
    stats = sample_share_summary_stats()
    labels = (
        "Total species",
        "Lifers",
        "Total checklists",
        "Unique locations",
        "Countries",
        "Birding days",
        "Total individuals",
        "Total bird families",
    )
    html = render_share_summary_preview_html(
        stats,
        layout="minimal",
        fmt="story",
        card_stat_labels=labels,
    )
    assert "Total individuals" in html
    assert "Total bird families" in html


def test_tiles_story_renders_extra_selected_stats():
    stats = sample_share_summary_stats()
    labels = (
        "Total species",
        "Lifers",
        "Total checklists",
        "Unique locations",
        "Countries",
        "Birding days",
        "Total individuals",
        "Total bird families",
    )
    html = render_share_summary_preview_html(
        stats,
        layout="tiles",
        fmt="story",
        card_stat_labels=labels,
    )
    assert "Total individuals" in html
    assert "Total bird families" in html


def test_hero_and_tiles_render_favourite_birds_block():
    stats = sample_share_summary_stats()
    birds = ("Superb Fairywren", "Rainbow Lorikeet")
    hero = render_share_summary_preview_html(stats, layout="hero", favourite_birds=birds)
    tiles = render_share_summary_preview_html(
        stats, layout="tiles", fmt="portrait_post", favourite_birds=birds
    )
    for html in (hero, tiles):
        assert "Favourite birds" in html
        assert "Favourite bird</div>" not in html  # plural heading only
        assert "Superb Fairywren" in html
        assert "Rainbow Lorikeet" in html


def test_tiles_square_omits_favourite_birds():
    stats = sample_share_summary_stats()
    html = render_share_summary_preview_html(
        stats,
        layout="tiles",
        fmt="square",
        favourite_birds=("Superb Fairywren",),
    )
    assert "Favourite bird" not in html
    assert "Superb Fairywren" not in html
    assert "grid-template-columns:repeat(2" in html


def test_hero_uses_singular_favourite_bird_heading_for_one_pick():
    stats = sample_share_summary_stats()
    html = render_share_summary_preview_html(
        stats, layout="hero", favourite_birds=("Superb Fairywren",)
    )
    assert "Favourite bird</div>" in html
    assert "Favourite birds</div>" not in html


def test_minimal_layout_ignores_favourite_birds():
    stats = sample_share_summary_stats()
    html = render_share_summary_preview_html(
        stats, layout="minimal", favourite_birds=("Superb Fairywren",)
    )
    assert "Favourite bird" not in html
    assert "Superb Fairywren" not in html


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
    from explorer.presentation.share_summary_preview import (
        spotlight_label_from_id,
        spotlight_pair_for_label,
        spotlight_species_label,
        spotlight_value,
    )

    assert spotlight_species_label("year") == "Year birds"
    assert spotlight_species_label("month") == "Month birds"
    assert spotlight_species_label("week") == "Week birds"
    assert spotlight_species_label("custom") == "Species"
    assert spotlight_species_label("lifetime") == "Species"

    year = ShareSummaryStats(period_label="2025", period_kind="year", species=312)
    assert spotlight_value(year, "species") == ("Total species", "312")
    assert spotlight_pair_for_label(year, "Total species") == ("Total species", "312")
    assert spotlight_label_from_id("species") == "Total species"

    month = ShareSummaryStats(period_label="June 2025", period_kind="month", species=89)
    assert spotlight_value(month, "species") == ("Total species", "89")

    week = ShareSummaryStats(
        period_label="May 31, 2025 - June 6, 2025", period_kind="week", species=34
    )
    assert spotlight_value(week, "species") == ("Total species", "34")

    custom = ShareSummaryStats(period_label="1 – 7 June 2025", period_kind="custom", species=56)
    assert spotlight_value(custom, "species") == ("Total species", "56")


def test_spotlight_layout_accepts_all_time_label():
    from explorer.core.share_summary_compute import ShareSummaryAllTimeStats
    from explorer.presentation.share_summary_preview import render_share_summary_preview_html

    stats = sample_share_summary_stats()
    all_time = ShareSummaryAllTimeStats(world_bird_coverage_pct=6.8)
    html = render_share_summary_preview_html(
        stats,
        layout="spotlight",
        spotlight_label="Observed species (%)",
        all_time=all_time,
    )
    assert "Observed species (%)" in html
    assert "6.8%" in html


def test_summary_status_metrics_includes_observed_species_pct():
    from explorer.presentation.share_summary_preview import summary_status_metrics

    stats = sample_share_summary_stats()
    metrics = summary_status_metrics(stats, world_bird_coverage_pct=6.8)
    labels = [lab for lab, _ in metrics]
    assert "Observed species (%)" in labels
    assert labels.index("Observed species (%)") > labels.index("Total bird families")


def test_summary_status_metrics_preferred_order():
    from explorer.presentation.share_summary_preview import summary_status_metrics

    stats = sample_share_summary_stats(period_kind="month")
    all_time = ShareSummaryAllTimeStats(
        observed_species_taxa=312,
        total_families_taxa=248,
        observed_families=186,
        world_bird_coverage_pct=6.8,
    )
    labels = [lab for lab, _ in summary_status_metrics(stats, all_time=all_time)]
    assert labels[:9] == [
        "Total species",
        "Lifers",
        "Total checklists",
        "Completed checklists",
        "Unique locations",
        "Countries",
        "Birding hours",
        "Birding days",
        "Longest streak (days)",
    ]
    assert labels[9:14] == [
        "Total individuals",
        "Total bird families",
        "Observed species (%)",
        "Observed species",
        "Observed families",
    ]


def test_sample_share_summary_stats_lifetime_omits_lifers():
    from explorer.presentation.share_summary_preview import sample_share_summary_stats

    stats = sample_share_summary_stats(period_label="Lifetime", period_kind="lifetime")
    assert stats.period_kind == "lifetime"
    assert stats.lifers is None
    assert stats.species == 847
    assert stats.checklists == 1_240
    assert stats.completed_checklists == 1_104


def test_lifetime_default_card_stats():
    from explorer.presentation.share_summary_preview import (
        card_stat_pairs,
        default_card_stat_labels,
        sample_share_summary_stats,
        summary_status_metrics,
    )

    stats = sample_share_summary_stats(period_kind="lifetime")
    metrics = summary_status_metrics(stats)
    hero = default_card_stat_labels("hero", metrics, period_kind="lifetime")
    assert hero == (
        "Total species",
        "Countries",
        "Total checklists",
        "Unique locations",
    )
    tiles = default_card_stat_labels("minimal", metrics, period_kind="lifetime")
    assert tiles == (
        "Total species",
        "Countries",
        "Birding days",
        "Total checklists",
        "Total individuals",
        "Longest streak (days)",
    )
    tile_labels = [lab for lab, _ in card_stat_pairs(stats, max_count=6, layout="tiles")]
    assert tile_labels == list(tiles)


def test_completed_checklists_in_summary_metrics():
    from explorer.presentation.share_summary_preview import (
        sample_share_summary_stats,
        summary_status_metrics,
    )

    stats = sample_share_summary_stats(period_kind="year")
    labels = [label for label, _ in summary_status_metrics(stats)]
    assert "Total checklists" in labels
    assert "Completed checklists" in labels
    lookup = dict(summary_status_metrics(stats))
    assert lookup["Total checklists"] == "186"
    assert lookup["Completed checklists"] == "172"


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


def test_card_stat_pairs_selected_labels_includes_all_time():
    from explorer.core.share_summary_compute import ShareSummaryAllTimeStats
    from explorer.presentation.share_summary_preview import card_stat_pairs

    stats = sample_share_summary_stats()
    all_time = ShareSummaryAllTimeStats(
        world_bird_coverage_pct=6.8,
        observed_species_taxa=847,
    )
    pairs = card_stat_pairs(
        stats,
        max_count=4,
        selected_labels=("Observed species (%)", "Lifers"),
        all_time=all_time,
    )
    assert pairs == [("Observed species (%)", "6.8%"), ("Lifers", "47")]


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

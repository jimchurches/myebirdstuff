"""Tests for :mod:`explorer.presentation.share_summary_preview`."""

from explorer.core.share_summary_compute import (
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.presentation.share_summary_preview import (
    render_share_summary_export_html,
    render_share_summary_preview_html,
    sample_share_summary_stats,
    stat_pairs,
)


def test_render_preview_includes_period_label_and_logo():
    html = render_share_summary_preview_html(sample_share_summary_stats(), layout="tiles")
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
    light = render_share_summary_preview_html(stats, layout="tiles", color_scheme_index=0)
    dark = render_share_summary_preview_html(stats, layout="tiles", color_scheme_index=1)
    assert SHARE_SUMMARY_COLOR_SCHEMES[0]["bg"] in light
    assert SHARE_SUMMARY_COLOR_SCHEMES[1]["bg"] in dark
    assert light != dark


def test_layout_card_stat_max_grid_and_minimal_limits():
    from explorer.presentation.share_summary_preview import (
        layout_card_stat_max,
        layout_grid_stat_max,
        layout_grid_stat_min,
    )

    assert layout_grid_stat_min("square") == 4
    assert layout_grid_stat_max("square") == 6
    assert layout_grid_stat_max("portrait_post") == 8
    assert layout_grid_stat_max("story") == 14
    assert layout_card_stat_max("minimal", "story") == 18
    assert layout_card_stat_max("minimal", "story", available_stat_count=14) == 14
    assert layout_card_stat_max("minimal", "story", available_stat_count=25) == 18
    assert layout_card_stat_max("tiles", "story") == 14
    assert layout_card_stat_max("tiles", "portrait_post") == 8
    assert layout_card_stat_max("minimal", "square") == 6
    assert layout_card_stat_max("tiles", "square") == 6


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
        "Bird families",
    )
    html = render_share_summary_preview_html(
        stats,
        layout="minimal",
        fmt="story",
        card_stat_labels=labels,
    )
    assert "Total individuals" in html
    assert "Bird families" in html


def test_tiles_grid_uses_uniform_cell_sizing_across_formats():
    stats = ShareSummaryStats(
        period_label="2025",
        period_kind="year",
        species=312,
        lifers=47,
        checklists=186,
        completed_checklists=172,
        incidental_checklists=14,
        locations=42,
        families=89,
        individuals=12_450,
        days_with_checklist=98,
        countries=5,
        longest_streak=14,
        birding_hours=214.5,
        distance_km=1_842.5,
        shared_checklists=8,
        days_birding_with_others=6,
    )
    labels_six = (
        "Total species",
        "Lifers",
        "Total checklists",
        "Unique locations",
        "Countries",
        "Birding days",
    )
    labels_twelve = labels_six + (
        "Total individuals",
        "Bird families",
        "Longest streak (days)",
        "Completed checklists",
        "Incidental checklists",
        "Birding hours",
    )
    labels_fourteen = labels_twelve + (
        "Total distance (km)",
        "Shared checklists",
    )
    square = render_share_summary_preview_html(
        stats, layout="tiles", fmt="square", card_stat_labels=labels_six
    )
    portrait = render_share_summary_preview_html(
        stats, layout="tiles", fmt="portrait_post", card_stat_labels=labels_six
    )
    story_six = render_share_summary_preview_html(
        stats, layout="tiles", fmt="story", card_stat_labels=labels_six
    )
    story_twelve = render_share_summary_preview_html(
        stats, layout="tiles", fmt="story", card_stat_labels=labels_twelve
    )
    story_fourteen = render_share_summary_preview_html(
        stats, layout="tiles", fmt="story", card_stat_labels=labels_fourteen
    )
    for html in (square, portrait, story_six, story_twelve, story_fourteen):
        assert 'font-size:52px;font-weight:700;">' in html
        assert "font-size:20px;color:" in html
        assert "padding:32px 20px" in html
        assert "gap:20px" in html
    assert story_fourteen.count('font-size:52px;font-weight:700;">') == 14
    assert "Shared checklists" in story_fourteen
    assert 'font-size:40px;font-weight:700;">' not in story_six
    assert 'font-size:40px;font-weight:700;">' not in story_twelve


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
        "Bird families",
    )
    html = render_share_summary_preview_html(
        stats,
        layout="tiles",
        fmt="story",
        card_stat_labels=labels,
    )
    assert "Total individuals" in html
    assert "Bird families" in html


def test_minimal_square_uses_tighter_stat_row_sizing():
    stats = sample_share_summary_stats()
    square = render_share_summary_preview_html(stats, layout="minimal", fmt="square")
    portrait = render_share_summary_preview_html(stats, layout="minimal", fmt="portrait_post")
    assert 'font-size:40px;font-weight:700;">312</span>' in square
    assert "padding:17px 0;border-bottom" in square
    assert 'font-size:44px;font-weight:700;">312</span>' in portrait
    assert "padding:20px 0;border-bottom" in portrait


def test_render_export_html_full_size_document():
    html = render_share_summary_export_html(sample_share_summary_stats(), layout="tiles", fmt="square")
    assert "<!DOCTYPE html>" in html
    assert "pebird-share-preview-wrap" not in html
    assert "width:1080px" in html
    assert "height:1080px" in html
    assert "data:image/svg+xml;base64," in html


def test_spotlight_layout_renders():
    stats = ShareSummaryStats(period_label="2025", period_kind="year", lifers=47)
    html = render_share_summary_preview_html(stats, layout="spotlight", spotlight_label="Lifers")
    assert "47" in html
    assert "Lifers" in html


def test_spotlight_pair_for_label_by_period():
    from explorer.presentation.share_summary_preview import spotlight_pair_for_label

    year = ShareSummaryStats(period_label="2025", period_kind="year", species=312)
    assert spotlight_pair_for_label(year, "Total species") == ("Species", "312")

    month = ShareSummaryStats(period_label="June 2025", period_kind="month", species=89)
    assert spotlight_pair_for_label(month, "Total species") == ("Species", "89")

    week = ShareSummaryStats(
        period_label="May 31, 2025 - June 6, 2025", period_kind="week", species=34
    )
    assert spotlight_pair_for_label(week, "Total species") == ("Species", "34")

    custom = ShareSummaryStats(period_label="1 – 7 June 2025", period_kind="custom", species=56)
    assert spotlight_pair_for_label(custom, "Total species") == ("Species", "56")
    assert spotlight_pair_for_label(custom, "Nonexistent stat") is None


def test_spotlight_layout_accepts_all_time_label():
    from explorer.core.share_summary_compute import ShareSummaryAllTimeStats
    from explorer.presentation.share_summary_preview import render_share_summary_preview_html

    stats = sample_share_summary_stats()
    all_time = ShareSummaryAllTimeStats(total_species_taxa=10_800)
    html = render_share_summary_preview_html(
        stats,
        layout="spotlight",
        spotlight_label="Observed species (%)",
        all_time=all_time,
    )
    assert "Observed species (%)" in html
    assert "2.9%" in html


def test_summary_status_metrics_includes_observed_species_pct():
    from explorer.core.share_summary_compute import ShareSummaryAllTimeStats
    from explorer.presentation.share_summary_preview import summary_status_metrics

    stats = sample_share_summary_stats()
    all_time = ShareSummaryAllTimeStats(total_species_taxa=10_800)
    metrics = summary_status_metrics(stats, all_time=all_time)
    labels = [lab for lab, _ in metrics]
    assert "Observed species (%)" in labels
    assert dict(metrics)["Observed species (%)"] == "2.9%"
    assert labels.index("Observed species (%)") > labels.index("Bird families")


def test_summary_status_metrics_preferred_order():
    from explorer.presentation.share_summary_preview import summary_status_metrics

    stats = sample_share_summary_stats(period_kind="month")
    all_time = ShareSummaryAllTimeStats(
        total_species_taxa=10_800,
        total_families_taxa=248,
    )
    labels = [lab for lab, _ in summary_status_metrics(stats, all_time=all_time)]
    assert labels == [
        "Total species",
        "Lifers",
        "Total checklists",
        "Completed checklists",
        "Incidental checklists",
        "Shared checklists",
        "Unique locations",
        "Countries",
        "Birding hours",
        "Birding days",
        "Days birding with others",
        "Longest streak (days)",
        "Total individuals",
        "Bird families",
        "Observed species (%)",
        "Species in eBird taxonomy",
        "Families in eBird taxonomy",
    ]
    assert dict(summary_status_metrics(stats, all_time=all_time))["Observed species (%)"] == "0.8%"


def test_summary_status_metrics_includes_distance_for_year_only():
    from explorer.presentation.share_summary_preview import summary_status_metrics

    year_labels = [lab for lab, _ in summary_status_metrics(sample_share_summary_stats())]
    assert "Total distance (km)" in year_labels
    assert dict(summary_status_metrics(sample_share_summary_stats()))["Total distance (km)"] == "1,842.5"

    month_labels = [
        lab for lab, _ in summary_status_metrics(sample_share_summary_stats(period_kind="month"))
    ]
    assert "Total distance (km)" not in month_labels


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
    four_stat_labels = [lab for lab, _ in card_stat_pairs(stats, max_count=4)]
    assert four_stat_labels == [
        "Species",
        "Countries",
        "Total checklists",
        "Unique locations",
    ]
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
    assert tile_labels == [
        "Species",
        "Countries",
        "Birding days",
        "Total checklists",
        "Total individuals",
        "Longest streak (days)",
    ]


def test_country_scope_four_stat_default_card_stats():
    from explorer.core.share_summary_compute import ShareSummaryGeoScope
    from explorer.presentation.share_summary_preview import (
        card_stat_pairs,
        sample_share_summary_stats,
    )

    stats = sample_share_summary_stats(period_kind="lifetime")
    for scope in (
        ShareSummaryGeoScope(country_key="AU"),
        ShareSummaryGeoScope(country_key="AU", region_code="NSW"),
    ):
        labels = [lab for lab, _ in card_stat_pairs(stats, max_count=4, geo_scope=scope)]
        assert labels == ["Species", "Total individuals", "Total checklists", "Unique locations"]


def test_country_scope_tiles_default_card_stats_exclude_world_only():
    from explorer.core.share_summary_compute import ShareSummaryGeoScope
    from explorer.presentation.share_summary_preview import (
        default_card_stat_labels,
        sample_share_summary_stats,
        summary_status_metrics,
    )

    stats = sample_share_summary_stats(period_kind="year")
    scope = ShareSummaryGeoScope(country_key="AU")
    metrics = summary_status_metrics(stats, geo_scope=scope)
    tiles = default_card_stat_labels("tiles", metrics, period_kind="year", geo_scope=scope)
    assert tiles == (
        "Total species",
        "Lifers",
        "Birding days",
        "Total individuals",
        "Total checklists",
        "Unique locations",
    )
    assert "Countries" not in tiles
    assert "Bird families" not in tiles


def test_render_preview_uses_card_stat_labels_at_country_scope():
    from explorer.core.share_summary_compute import ShareSummaryGeoScope
    from explorer.presentation.share_summary_preview import (
        render_share_summary_preview_html,
        sample_share_summary_stats,
    )

    stats = sample_share_summary_stats(period_kind="year")
    labels = (
        "Total species",
        "Lifers",
        "Birding days",
        "Total individuals",
        "Total checklists",
        "Unique locations",
    )
    html = render_share_summary_preview_html(
        stats,
        layout="tiles",
        card_stat_labels=labels,
        geo_scope=ShareSummaryGeoScope(country_key="AU"),
    )
    assert "Lifers" in html
    assert "Total individuals" in html
    assert "Bird families" not in html


def test_completed_checklists_in_summary_metrics():
    from explorer.presentation.share_summary_preview import (
        sample_share_summary_stats,
        summary_status_metrics,
    )

    stats = sample_share_summary_stats(period_kind="year")
    labels = [label for label, _ in summary_status_metrics(stats)]
    assert "Total checklists" in labels
    assert "Completed checklists" in labels
    assert "Incidental checklists" in labels
    assert labels.index("Incidental checklists") == labels.index("Completed checklists") + 1
    lookup = dict(summary_status_metrics(stats))
    assert lookup["Total checklists"] == "186"
    assert lookup["Completed checklists"] == "172"
    assert lookup["Incidental checklists"] == "14"


def test_incidental_checklists_not_on_default_card_stats():
    from explorer.core.share_summary_defaults import (
        SHARE_SUMMARY_COUNTRY_TILES_DEFAULT_STATS,
        SHARE_SUMMARY_FOUR_STAT_DEFAULT_STATS,
        SHARE_SUMMARY_LIFETIME_FOUR_STAT_DEFAULT_STATS,
        SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS,
        SHARE_SUMMARY_TILES_DEFAULT_STATS,
    )

    defaults = (
        SHARE_SUMMARY_FOUR_STAT_DEFAULT_STATS,
        SHARE_SUMMARY_TILES_DEFAULT_STATS,
        SHARE_SUMMARY_LIFETIME_FOUR_STAT_DEFAULT_STATS,
        SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS,
        SHARE_SUMMARY_COUNTRY_TILES_DEFAULT_STATS,
    )
    for stat_defaults in defaults:
        assert "Incidental checklists" not in stat_defaults


def test_stat_card_display_label_maps_picker_to_short_tile():
    from explorer.presentation.share_summary_preview import stat_card_display_label

    assert stat_card_display_label("Total species") == "Species"
    assert stat_card_display_label("Lifers") == "Lifers"


def test_card_stat_pairs_year_includes_countries():
    from explorer.presentation.share_summary_preview import card_stat_pairs

    stats = sample_share_summary_stats(period_kind="year")
    labels = [lab for lab, _ in card_stat_pairs(stats, max_count=6)]
    assert "Countries" in labels
    assert "Birding days" in labels


def test_card_stat_pairs_four_stat_default():
    from explorer.presentation.share_summary_preview import card_stat_pairs

    stats = sample_share_summary_stats(period_kind="custom", trip_title="Trip")
    labels = [lab for lab, _ in card_stat_pairs(stats, max_count=4)]
    assert labels == ["Species", "Lifers", "Total checklists", "Unique locations"]


def test_card_stat_pairs_tiles_includes_countries_and_birding_days():
    from explorer.presentation.share_summary_preview import card_stat_pairs

    stats = sample_share_summary_stats(period_kind="month")
    labels = [lab for lab, _ in card_stat_pairs(stats, max_count=6, layout="tiles")]
    assert labels == [
        "Species",
        "Lifers",
        "Total checklists",
        "Unique locations",
        "Countries",
        "Birding days",
    ]


def test_summary_status_metrics_includes_region_lifers_when_geo_scoped():
    from explorer.core.share_summary_compute import ShareSummaryGeoScope, geo_region_lifer_stat_label
    from explorer.presentation.share_summary_preview import summary_status_metrics

    scope = ShareSummaryGeoScope(country_key="AU", region_code="NSW")
    label = geo_region_lifer_stat_label(scope)
    stats = ShareSummaryStats(
        period_label="2026",
        period_kind="year",
        lifers=3,
        region_lifers=5,
    )
    metrics = dict(summary_status_metrics(stats, geo_scope=scope))
    assert metrics["Lifers"] == "3"
    assert metrics[label] == "5"
    labels = [lab for lab, _ in summary_status_metrics(stats, geo_scope=scope)]
    assert labels.index("Lifers") < labels.index(label)


def test_render_preview_html_includes_region_lifer_label():
    from explorer.core.share_summary_compute import ShareSummaryGeoScope
    from explorer.presentation.share_summary_preview import (
        render_share_summary_preview_html,
        sample_share_summary_stats,
    )

    stats = sample_share_summary_stats(period_kind="year")
    stats = ShareSummaryStats(
        period_label=stats.period_label,
        period_kind=stats.period_kind,
        species=stats.species,
        lifers=stats.lifers,
        region_lifers=4,
        checklists=stats.checklists,
        locations=stats.locations,
    )
    scope = ShareSummaryGeoScope(country_key="AU")
    html = render_share_summary_preview_html(
        stats,
        layout="spotlight",
        spotlight_label="Australia Lifers",
        card_stat_labels=("Australia Lifers",),
        geo_scope=scope,
    )
    assert "Australia Lifers" in html
    assert "4" in html


def test_summary_status_metrics_hides_world_only_stats_when_not_world():
    from explorer.core.share_summary_compute import ShareSummaryAllTimeStats, ShareSummaryGeoScope
    from explorer.presentation.share_summary_preview import (
        LABEL_OBSERVED_SPECIES_PCT,
        LABEL_SPECIES_IN_TAXONOMY,
        sample_share_summary_stats,
        summary_status_metrics,
    )

    stats = sample_share_summary_stats(period_kind="year")
    all_time = ShareSummaryAllTimeStats(total_species_taxa=10_800, total_families_taxa=248)
    world = dict(
        summary_status_metrics(
            stats,
            all_time=all_time,
            geo_scope=ShareSummaryGeoScope(),
        )
    )
    assert "Countries" in world
    assert LABEL_SPECIES_IN_TAXONOMY in world
    assert LABEL_OBSERVED_SPECIES_PCT in world

    regional = dict(
        summary_status_metrics(
            stats,
            all_time=all_time,
            geo_scope=ShareSummaryGeoScope(country_key="AU", region_code="NSW"),
        )
    )
    assert "Countries" not in regional
    assert LABEL_SPECIES_IN_TAXONOMY not in regional
    assert LABEL_OBSERVED_SPECIES_PCT not in regional
    assert "Total species" in regional


def test_render_preview_html_includes_scope_label_in_footer():
    from explorer.presentation.share_summary_preview import (
        render_share_summary_preview_html,
        sample_share_summary_stats,
    )

    html = render_share_summary_preview_html(
        sample_share_summary_stats(),
        scope_label="Australia · New South Wales",
    )
    assert "Australia · New South Wales" in html


def test_card_stat_pairs_selected_labels_includes_all_time():
    from explorer.core.share_summary_compute import ShareSummaryAllTimeStats
    from explorer.presentation.share_summary_preview import card_stat_pairs

    stats = sample_share_summary_stats()
    all_time = ShareSummaryAllTimeStats(total_species_taxa=10_800)
    pairs = card_stat_pairs(
        stats,
        max_count=4,
        selected_labels=("Observed species (%)", "Lifers"),
        all_time=all_time,
    )
    assert pairs == [("Observed species (%)", "2.9%"), ("Lifers", "47")]


def test_stat_pairs_hide_zero_shared_stats_and_geo_scope_countries():
    stats = ShareSummaryStats(
        period_label="June 2025",
        period_kind="month",
        species=12,
        countries=2,
        shared_checklists=0,
        days_birding_with_others=0,
    )
    world_labels = [label for label, _ in stat_pairs(stats)]
    assert "Countries" in world_labels
    assert "Shared checklists" not in world_labels
    assert "Days birding with others" not in world_labels

    regional_labels = [
        label
        for label, _ in stat_pairs(
            stats,
            geo_scope=ShareSummaryGeoScope(country_key="AU", region_code="NSW"),
        )
    ]
    assert "Countries" not in regional_labels
    assert "Total species" in regional_labels


def test_trip_title_on_all_layouts():
    from explorer.core.share_summary_defaults import (
        SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL,
        SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES,
    )

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
    for layout in ("tiles", "minimal", "spotlight"):
        html = render_share_summary_preview_html(stats, layout=layout)
        assert "North Coast NSW Exploration" in html

    tiles_html = render_share_summary_preview_html(stats, layout="tiles")
    minimal_html = render_share_summary_preview_html(stats, layout="minimal")
    assert SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES not in tiles_html
    assert SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL not in minimal_html


def test_lifetime_card_subtitles_read_from_defaults():
    from explorer.core.share_summary_defaults import (
        SHARE_SUMMARY_LIFETIME_SUBTITLE,
        share_summary_card_subtitle,
    )

    for layout in ("tiles", "minimal", "spotlight"):
        assert share_summary_card_subtitle(layout=layout, period_kind="lifetime") == (
            SHARE_SUMMARY_LIFETIME_SUBTITLE
        )


def test_lifetime_layouts_render_subtitle_from_defaults():
    from explorer.core.share_summary_defaults import SHARE_SUMMARY_LIFETIME_SUBTITLE

    stats = ShareSummaryStats(
        period_label="Lifetime",
        period_kind="lifetime",
        species=847,
        checklists=1240,
        locations=186,
    )
    for layout in ("tiles", "minimal", "spotlight"):
        html = render_share_summary_preview_html(stats, layout=layout)
        assert SHARE_SUMMARY_LIFETIME_SUBTITLE in html


def test_non_lifetime_layout_subtitles_read_from_defaults():
    from explorer.core.share_summary_defaults import (
        SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL,
        SHARE_SUMMARY_LAYOUT_SUBTITLE_SPOTLIGHT,
        SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES,
        SHARE_SUMMARY_PERIOD_SUBTITLE_YEAR,
        share_summary_card_subtitle,
        share_summary_period_subtitle,
    )

    assert share_summary_period_subtitle("year") == SHARE_SUMMARY_PERIOD_SUBTITLE_YEAR
    assert share_summary_card_subtitle(layout="tiles", period_kind="year") == (
        SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES
    )
    assert share_summary_card_subtitle(layout="minimal", period_kind="year") == (
        SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL
    )
    assert share_summary_card_subtitle(layout="spotlight", period_kind="year") == (
        SHARE_SUMMARY_LAYOUT_SUBTITLE_SPOTLIGHT
    )


def test_year_layouts_render_layout_subtitles_from_defaults():
    from explorer.core.share_summary_defaults import (
        SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL,
        SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES,
    )

    stats = ShareSummaryStats(period_label="2025", period_kind="year", species=312)
    tiles_html = render_share_summary_preview_html(stats, layout="tiles")
    minimal_html = render_share_summary_preview_html(stats, layout="minimal")
    assert SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES in tiles_html
    assert SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL in minimal_html


def test_portrait_post_preview_dimensions():
    html = render_share_summary_preview_html(sample_share_summary_stats(), fmt="portrait_post")
    assert "width:1080px" in html
    assert "height:1350px" in html


def test_dark_tile_mockup_has_thirteen_variants_starting_with_current():
    from explorer.presentation.share_summary_dark_tile_mockup import (
        DARK_TILE_VARIANT_IDS,
        dark_tile_variant_scheme,
    )

    assert len(DARK_TILE_VARIANT_IDS) == 13
    assert DARK_TILE_VARIANT_IDS[0] == "current"
    current = dark_tile_variant_scheme("current")
    assert "tile_bg" not in current


def test_dark_tile_mockup_lift_injects_tile_colours_into_grid_html():
    from explorer.presentation.share_summary_dark_tile_mockup import (
        render_dark_tile_mockup_preview_html,
    )

    stats = sample_share_summary_stats()
    html = render_dark_tile_mockup_preview_html(stats, variant="lift_medium")
    assert "#1e2a24" in html
    assert "#243229" in html
    assert "tile_bg" in html


def test_share_summary_scheme_override_tile_keys():
    from explorer.presentation.share_summary_preview import (
        share_summary_scheme_override,
    )
    from explorer.core.share_summary_defaults import SHARE_SUMMARY_COLOR_SCHEMES

    scheme = {
        **SHARE_SUMMARY_COLOR_SCHEMES[1],
        "tile_bg": "#243229",
        "tile_bg_alt": "#1e2a24",
    }
    with share_summary_scheme_override(scheme):
        html = render_share_summary_preview_html(
            sample_share_summary_stats(),
            layout="tiles",
            color_scheme_index=1,
        )
    assert "#243229" in html
    assert "#1e2a24" in html


def test_dark_tile_mockup_circle_cluster_uses_tile_palette():
    from explorer.presentation.share_summary_dark_tile_mockup import (
        render_dark_tile_mockup_preview_html,
    )

    stats = sample_share_summary_stats()
    html = render_dark_tile_mockup_preview_html(
        stats,
        variant="lift_strong",
        tiles_presentation="circles",
        show_scheme_reference=False,
    )
    assert "#2d3d35" in html
    assert "#25332c" in html

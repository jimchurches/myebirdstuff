"""Tests for circular share summary cluster layout."""

import re

from explorer.presentation.share_summary_circles_preview import (
    CIRCLE_VARIANT_IDS,
    CIRCLE_VARIANT_SPECS,
    HERO_CIRCLE_CLUSTER_VARIANT,
    TILES_CIRCLE_CLUSTER_VARIANT,
    _circle_canvas_size,
    _hero_circle_canvas_size,
    _tiles_circle_canvas_size,
    _centres_in_grid_reading_order,
    _circle_diameter,
    _circle_value_font_px,
    _story_zigzag_centres,
    _story_zigzag_diameter,
    _story_zigzag_non_overlapping,
    circles_layout_non_overlapping,
    circles_within_canvas,
    largest_cluster_diameter,
    layout_hero_circle,
    layout_tiles_circle_cluster,
    layout_spotlight_circle,
    place_circle_centers,
    _spotlight_circle_diameter,
)
from explorer.presentation.share_summary_preview import (
    FormatId,
    render_share_summary_preview_html,
    sample_share_summary_stats,
)


def _diameter_for_variant(count: int, canvas_w: int, canvas_h: int, variant: str) -> int:
    spec = CIRCLE_VARIANT_SPECS[variant]  # type: ignore[index]
    return _circle_diameter(
        count,
        canvas_w,
        canvas_h,
        gap_px=spec.gap_px,
        ring_step=spec.ring_step,
    )


def _placed_diameter(
    count: int,
    canvas_w: int,
    canvas_h: int,
    variant: str,
) -> int:
    return largest_cluster_diameter(
        count,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        variant=variant,  # type: ignore[arg-type]
    )


def test_circle_variant_ids_count():
    assert len(CIRCLE_VARIANT_IDS) == 8


def test_grid_reading_order_does_not_start_with_centre():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    diameter = _placed_diameter(6, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
    centres, _ = place_circle_centers(
        6,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
        variant=TILES_CIRCLE_CLUSTER_VARIANT,
    )
    ordered = _centres_in_grid_reading_order(centres)
    target_x = canvas_w / 2
    target_y = canvas_h / 2 - canvas_h * 0.07
    centre_circle = min(
        centres,
        key=lambda c: (c[0] - target_x) ** 2 + (c[1] - target_y) ** 2,
    )
    assert ordered[0] != centre_circle


def test_radial_cluster_centre_circle_is_shifted_up():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    diameter = _placed_diameter(6, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
    centres = place_circle_centers(
        6,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
        variant=TILES_CIRCLE_CLUSTER_VARIANT,
    )[0]
    cx, cy = centres[0]
    expected_cy = canvas_h / 2 - canvas_h * 0.07
    assert abs(cx - canvas_w / 2) < 1.0
    assert abs(cy - expected_cy) < 1.0


def test_circles_non_overlapping_for_six_and_seven():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    for count in (6, 7):
        diameter = _placed_diameter(count, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
        assert circles_layout_non_overlapping(
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=diameter,
            variant=TILES_CIRCLE_CLUSTER_VARIANT,
            period_label="2025",
        )


def test_circles_non_overlapping_for_tiles_counts_four_to_seven():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    for count in range(4, 8):
        diameter = _placed_diameter(count, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
        assert circles_layout_non_overlapping(
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=diameter,
            variant=TILES_CIRCLE_CLUSTER_VARIANT,
            period_label="2025",
        )


def test_circles_non_overlapping_for_hero_four():
    canvas_w, canvas_h = _hero_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    diameter = _placed_diameter(4, canvas_w, canvas_h, HERO_CIRCLE_CLUSTER_VARIANT)
    assert circles_layout_non_overlapping(
        4,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
        variant=HERO_CIRCLE_CLUSTER_VARIANT,
        period_label="2025",
    )


def test_hero_circle_square_uses_larger_diameter_than_before():
    canvas_w, canvas_h = _hero_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    diameter = _placed_diameter(4, canvas_w, canvas_h, HERO_CIRCLE_CLUSTER_VARIANT)
    assert diameter >= 180


def test_tiles_circle_square_six_stats_uses_larger_diameter_than_before():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    diameter = _placed_diameter(6, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
    assert diameter >= 165


def test_tiles_circle_diameter_scales_down_with_more_stats_on_square():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    by_count = {
        count: _placed_diameter(count, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
        for count in range(4, 8)
    }
    assert by_count[4] >= by_count[7]


def test_tiles_circle_diameter_all_formats():
    formats: tuple[FormatId, ...] = ("square", "portrait_post", "story")
    for fmt in formats:
        w, h = (1080, 1080) if fmt == "square" else ((1080, 1350) if fmt == "portrait_post" else (1080, 1920))
        canvas_w, canvas_h = _tiles_circle_canvas_size(w, h, fmt, scope_label="World")
        for count in (6, 7):
            if fmt == "story":
                spec = CIRCLE_VARIANT_SPECS[TILES_CIRCLE_CLUSTER_VARIANT]
                assert _story_zigzag_non_overlapping(
                    count,
                    canvas_w=canvas_w,
                    canvas_h=canvas_h,
                    diameter=180,
                    gap_px=spec.gap_px,
                )
                continue
            diameter = _placed_diameter(
                count, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT
            )
            assert circles_within_canvas(
                count,
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                diameter=diameter,
                variant=TILES_CIRCLE_CLUSTER_VARIANT,
                period_label="2026",
            )


def test_story_zigzag_weaves_horizontally():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1920, "story", scope_label="World"
    )
    spec = CIRCLE_VARIANT_SPECS[TILES_CIRCLE_CLUSTER_VARIANT]
    diameter = _story_zigzag_diameter(6, canvas_w, canvas_h, gap_px=spec.gap_px)
    centres = _story_zigzag_centres(
        6,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        diameter=diameter,
        gap_px=spec.gap_px,
    )
    xs = [x for x, _ in centres]
    ys = [y for _, y in centres]
    assert min(xs) < canvas_w * 0.35
    assert max(xs) > canvas_w * 0.65
    left = sum(1 for x in xs if x < canvas_w * 0.4)
    right = sum(1 for x in xs if x > canvas_w * 0.6)
    assert left >= 2 and right >= 2
    assert ys == sorted(ys)
    gaps = [ys[i] - ys[i - 1] for i in range(1, len(ys))]
    assert len(set(round(g, 0) for g in gaps)) > 1


def test_story_zigzag_keeps_circles_above_footer_clearance():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1920, "story", scope_label="World"
    )
    spec = CIRCLE_VARIANT_SPECS[TILES_CIRCLE_CLUSTER_VARIANT]
    for count in (6, 7):
        diameter = _story_zigzag_diameter(count, canvas_w, canvas_h, gap_px=spec.gap_px)
        assert _story_zigzag_non_overlapping(
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=diameter,
            gap_px=spec.gap_px,
        )
        centres = _story_zigzag_centres(
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=diameter,
            gap_px=spec.gap_px,
        )
        bottom = max(y for _, y in centres) + diameter / 2 + 12
        assert bottom <= canvas_h - 52
        assert min(y for _, y in centres) - diameter / 2 >= 20


def test_story_scatter_maintains_minimum_edge_padding():
    import math

    from explorer.presentation.share_summary_circles_preview import (
        _SHADOW_PAD_PX,
        _STORY_SCATTER_MIN_EDGE_GAP_PX,
    )

    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1920, "story", scope_label="World"
    )
    spec = CIRCLE_VARIANT_SPECS[TILES_CIRCLE_CLUSTER_VARIANT]
    min_edge_gap = max(spec.gap_px, _STORY_SCATTER_MIN_EDGE_GAP_PX)
    min_dist = min_edge_gap + 2 * _SHADOW_PAD_PX
    for count in (6, 7):
        diameter = _story_zigzag_diameter(count, canvas_w, canvas_h, gap_px=spec.gap_px)
        centres = _story_zigzag_centres(
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=diameter,
            gap_px=spec.gap_px,
        )
        for i, (x1, y1) in enumerate(centres):
            for x2, y2 in centres[i + 1 :]:
                dist = math.hypot(x1 - x2, y1 - y2)
                assert dist - diameter + 1e-6 >= min_dist


def test_layout_tiles_circle_cluster_story_zigzag_renders():
    stats = sample_share_summary_stats()
    html = layout_tiles_circle_cluster(
        stats,
        1080,
        1920,
        "story",
        scope_label="World",
    )
    assert html.count("border-radius:50%") == 6
    sizes = re.findall(r"width:(\d+)px;height:\1px;border-radius:50%", html)
    assert len(sizes) == 6
    assert int(sizes[0]) >= 260


def test_circles_within_canvas_for_six_and_seven():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080, 1080, "square", scope_label="World"
    )
    for count in (6, 7):
        diameter = _placed_diameter(count, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
        assert circles_within_canvas(
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=diameter,
            variant=TILES_CIRCLE_CLUSTER_VARIANT,
            period_label="2026",
        )


def test_layout_tiles_circle_cluster_renders():
    stats = sample_share_summary_stats()
    html = layout_tiles_circle_cluster(
        stats,
        1080,
        1080,
        "square",
        scope_label="World",
    )
    assert "border-radius:50%" in html
    assert "box-shadow:0 8px 18px" in html
    assert "Species" in html
    sizes = re.findall(r"width:(\d+)px;height:\1px;border-radius:50%", html)
    assert len(sizes) == 6
    assert min(int(size) for size in sizes) >= 165


def test_layout_tiles_circle_cluster_defaults_to_six_not_seven():
    stats = sample_share_summary_stats()
    html = layout_tiles_circle_cluster(
        stats,
        1080,
        1080,
        "square",
        scope_label="World",
        card_stat_labels=(),
    )
    assert html.count("border-radius:50%") == 6


def test_layout_tiles_circle_cluster_supports_seventh_user_stat():
    stats = sample_share_summary_stats()
    labels = (
        "Total species",
        "Lifers",
        "Total checklists",
        "Unique locations",
        "Countries",
        "Birding days",
        "Total individuals",
    )
    html = layout_tiles_circle_cluster(
        stats,
        1080,
        1080,
        "square",
        scope_label="World",
        card_stat_labels=labels,
    )
    assert html.count("border-radius:50%") == 7


def test_layout_hero_circle_renders():
    stats = sample_share_summary_stats()
    html = layout_hero_circle(
        stats,
        1080,
        1080,
        "square",
        scope_label="World",
    )
    assert "border-radius:50%" in html
    assert "box-shadow:0 8px 18px" in html
    assert "Species" in html
    assert html.count("border-radius:50%") == 4


def test_circle_value_font_shrinks_for_long_numbers():
    assert _circle_value_font_px("312", 48, diameter=170) == 48
    assert _circle_value_font_px("12,450", 48, diameter=170) == 36
    assert _circle_value_font_px("475,781", 48, diameter=170) == 30
    assert _circle_value_font_px("475,781", 40, diameter=148) == 25


def test_share_summary_preview_tiles_circle_cluster():
    stats = sample_share_summary_stats()
    html = render_share_summary_preview_html(
        stats,
        layout="tiles",
        tiles_style="circles",
        fmt="square",
        scale=1.0,
        scope_label="World",
    )
    assert "pebird-share-preview-wrap" in html
    assert html.count("border-radius:50%") == 6


def test_share_summary_preview_hero_circle_all_formats():
    stats = sample_share_summary_stats()
    formats: tuple[FormatId, ...] = ("square", "portrait_post", "story")
    for fmt in formats:
        html = render_share_summary_preview_html(
            stats,
            layout="hero",
            hero_style="circle",
            fmt=fmt,
            scale=1.0,
            scope_label="World",
        )
        assert "pebird-share-preview-wrap" in html
        assert html.count("border-radius:50%") == 4


def test_spotlight_circle_is_larger_than_tiles_cluster_circle():
    canvas_w, canvas_h = _circle_canvas_size(1080, 1080, "square", scope_label="World")
    tiles_d = _placed_diameter(6, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
    spotlight_d = _spotlight_circle_diameter(canvas_w, canvas_h, "square")
    assert spotlight_d > tiles_d * 1.5


def test_spotlight_circle_value_font_matches_classic_for_short_numbers():
    from explorer.presentation.share_summary_circles_preview import (
        _spotlight_circle_value_base_px,
    )

    canvas_w, canvas_h = _circle_canvas_size(1080, 1080, "square", scope_label="World")
    diameter = _spotlight_circle_diameter(canvas_w, canvas_h, "square")
    base = _spotlight_circle_value_base_px(diameter, width=1080, height=1080)
    assert base == 160
    assert _circle_value_font_px("47", base, diameter=diameter) == 160
    assert _circle_value_font_px("312", base, diameter=diameter) == 160
    assert _circle_value_font_px("12,450", base, diameter=diameter) < 160


def test_share_summary_preview_spotlight_circle():
    stats = sample_share_summary_stats()
    html = render_share_summary_preview_html(
        stats,
        layout="spotlight",
        spotlight_style="circle",
        fmt="square",
        scale=1.0,
        spotlight_label="Lifers",
        scope_label="World",
    )
    assert "pebird-share-preview-wrap" in html
    assert html.count("border-radius:50%") == 1
    assert "47" in html
    assert "Lifers" in html


def test_layout_spotlight_circle_renders():
    stats = sample_share_summary_stats()
    html = layout_spotlight_circle(
        stats,
        1080,
        1080,
        "square",
        spotlight_label="Lifers",
        scope_label="World",
    )
    assert "border-radius:50%" in html
    assert "47" in html

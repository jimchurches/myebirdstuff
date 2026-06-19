"""Tests for circular share summary cluster layout."""

from explorer.presentation.share_summary_circles_preview import (
    CIRCLE_VARIANT_IDS,
    CIRCLE_VARIANT_SPECS,
    TILES_CIRCLE_CLUSTER_VARIANT,
    _circle_canvas_size,
    _centres_in_grid_reading_order,
    _circle_diameter,
    _circle_value_font_px,
    _centres_in_grid_reading_order,
    _circle_diameter,
    circles_layout_non_overlapping,
    circles_within_canvas,
    layout_tiles_circle_cluster,
    place_circle_centers,
)
from explorer.presentation.share_summary_preview import (
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


def test_circle_variant_ids_count():
    assert len(CIRCLE_VARIANT_IDS) == 6


def test_grid_reading_order_does_not_start_with_centre():
    canvas_w, canvas_h = _circle_canvas_size(1080, 1080, "square", scope_label="World")
    diameter = _diameter_for_variant(6, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
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
    canvas_w, canvas_h = _circle_canvas_size(1080, 1080, "square", scope_label="World")
    diameter = _diameter_for_variant(6, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
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
    canvas_w, canvas_h = _circle_canvas_size(1080, 1080, "square", scope_label="World")
    for count in (6, 7):
        diameter = _diameter_for_variant(count, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
        assert circles_layout_non_overlapping(
            count,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            diameter=diameter,
            variant=TILES_CIRCLE_CLUSTER_VARIANT,
            period_label="2025",
        )


def test_circles_within_canvas_for_six_and_seven():
    canvas_w, canvas_h = _circle_canvas_size(1080, 1080, "square", scope_label="World")
    for count in (6, 7):
        diameter = _diameter_for_variant(count, canvas_w, canvas_h, TILES_CIRCLE_CLUSTER_VARIANT)
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
    assert html.count("border-radius:50%") >= 6

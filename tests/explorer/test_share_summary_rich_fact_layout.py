"""Tests for Interesting Insights layout specs (#285)."""

from explorer.presentation.share_summary_rich_fact_layout import (
    RichFactLineStyle,
    rich_fact_layout_spec,
    rich_fact_line_style_css,
)


def test_rich_fact_layout_spec_shared_typography():
    story = rich_fact_layout_spec("story")
    portrait = rich_fact_layout_spec("portrait_post")
    square = rich_fact_layout_spec("square")
    for spec in (story, portrait, square):
        assert spec.label.font_size_px == 52
        assert spec.label.margin_bottom_px == 48
        assert spec.primary.font_size_px == 60
        assert spec.metric.font_size_px == 46
        assert spec.metric.margin_top_px == 48


def test_rich_fact_layout_spec_block_offset_by_format():
    assert rich_fact_layout_spec("square").block_offset_y_px == -110
    assert rich_fact_layout_spec("portrait_post").block_offset_y_px == -160
    assert rich_fact_layout_spec("story").block_offset_y_px == -220


def test_rich_fact_layout_spec_tile_frame_enabled():
    for fmt in ("square", "portrait_post", "story"):
        assert rich_fact_layout_spec(fmt).tile_frame is True


def test_rich_fact_line_style_css_includes_only_set_margins():
    style = RichFactLineStyle(
        font_size_px=46,
        font_weight=700,
        color_role="text",
        line_height=1.1,
        margin_top_px=48,
    )
    css = rich_fact_line_style_css(style, colour="#111827")
    assert css == (
        "font-size:46px;"
        "font-weight:700;"
        "line-height:1.1;"
        "color:#111827;"
        "margin-top:48px"
    )
    assert "margin-bottom" not in css

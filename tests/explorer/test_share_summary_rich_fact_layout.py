"""Tests for rich Spotlight fact layout specs and playground (#285)."""

from explorer.presentation.share_summary_rich_fact_layout import rich_fact_layout_spec
from explorer.presentation.share_summary_rich_fact_layout_playground import (
    _offset_range_for_format,
    render_rich_fact_layout_playground_html,
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
    assert rich_fact_layout_spec("square").block_offset_y_px == -280
    assert rich_fact_layout_spec("portrait_post").block_offset_y_px == 0
    assert rich_fact_layout_spec("story").block_offset_y_px == 0


def test_rich_fact_layout_spec_tile_frame_enabled():
    for fmt in ("square", "portrait_post", "story"):
        assert rich_fact_layout_spec(fmt).tile_frame is True


def test_offset_range_story_exceeds_legacy_cap():
    low, high = _offset_range_for_format("story")
    assert low <= -360
    assert high >= 360


def test_offset_range_square_covers_midline():
    low, high = _offset_range_for_format("square")
    assert high >= 300
    assert low <= -300


def test_rich_fact_layout_playground_html_includes_controls():
    html = render_rich_fact_layout_playground_html()
    assert "Rich fact layout" in html
    assert "blockOffsetY" in html
    assert "offsetMin" in html
    assert "Rectangular tile frame" in html
    assert "share_summary_rich_fact_layout.py" in html
    assert "Most common checklist species" in html

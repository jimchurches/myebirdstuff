"""Tests for the share-summary circle layout playground HTML."""

from __future__ import annotations

from explorer.presentation.share_summary_circle_layout_playground import (
    render_circle_layout_playground_html,
    story_circle_body_bounds_for_playground,
)
from explorer.presentation.share_summary_circles_preview import (
    STORY_CIRCLE_LAYOUTS,
    _tiles_circle_canvas_size,
)


def test_circle_layout_playground_html_includes_story_config():
    html = render_circle_layout_playground_html(fmt="story", initial_count=9)
    assert "STORY_CIRCLE_LAYOUTS" in html
    assert '"canvas_w": 984' in html or '"canvas_w":984' in html
    assert '"canvas_h":' in html
    assert "pointerdown" in html
    assert "Copy Python tuple" in html
    assert "diameter_px:" in html
    assert '"10": 255' in html
    for count in STORY_CIRCLE_LAYOUTS:
        assert f'"{count}":' in html


def test_story_circle_body_bounds_for_playground_matches_preview():
    canvas_w, canvas_h = _tiles_circle_canvas_size(
        1080,
        1920,
        "story",
        scope_label="World",
    )
    bounds = story_circle_body_bounds_for_playground(canvas_w, canvas_h, diameter=200)
    x_min, x_max, y_min, y_max = bounds
    assert x_min < x_max
    assert y_min < y_max
    assert y_max < canvas_h

"""Tests for the share-summary circle layout playground HTML."""

from __future__ import annotations

from explorer.presentation.share_summary_circle_layout_playground import (
    PLAYGROUND_CARD_TYPES,
    PLAYGROUND_FORMATS,
    render_circle_layout_playground_html,
    story_circle_body_bounds_for_playground,
)
from explorer.presentation.share_summary_circles_preview import (
    STORY_CIRCLE_LAYOUTS,
    _tiles_circle_canvas_size,
)


def test_circle_layout_playground_html_includes_all_modes():
    html = render_circle_layout_playground_html()
    assert "Statistics Grid" in html
    assert "Hero Grid" in html
    assert "Spotlight" in html
    assert '"modes"' in html
    assert "pointerdown" in html
    assert "Copy export" in html
    assert "card_type:" in html
    assert "target_code:" in html
    assert '"layout_label": "Statistics Grid"' in html
    assert "Implement this card design" in html
    assert "diameter_px:" in html
    assert '"10": 255' in html
    for card_type in PLAYGROUND_CARD_TYPES:
        assert f'"{card_type}"' in html
    for fmt in PLAYGROUND_FORMATS:
        assert f'"{fmt}"' in html
    for count in STORY_CIRCLE_LAYOUTS:
        assert f'"{count}":' in html


def test_circle_layout_playground_spotlight_is_not_draggable():
    html = render_circle_layout_playground_html(
        initial_card_type="spotlight",
        initial_fmt="square",
    )
    assert '"draggable": false' in html
    assert "fixed centre" in html


def test_circle_layout_playground_portrait_tiles_uses_code_layout():
    html = render_circle_layout_playground_html(
        initial_card_type="tiles",
        initial_fmt="portrait_post",
    )
    assert "PORTRAIT_TILES_CIRCLE_LAYOUTS" in html
    assert '"6": 255' in html
    assert "0.46" in html


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

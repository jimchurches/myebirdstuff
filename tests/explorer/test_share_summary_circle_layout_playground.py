"""Tests for the share-summary circle layout playground HTML."""

from __future__ import annotations

from explorer.presentation.share_summary_circle_layout_playground import (
    PLAYGROUND_CARD_TYPES,
    PLAYGROUND_FORMATS,
    PLAYGROUND_TILES_DEFAULT_COUNT,
    PLAYGROUND_TILES_MIN_COUNT,
    render_circle_layout_playground_html,
    story_circle_body_bounds_for_playground,
)
from explorer.presentation.share_summary_circles_preview import (
    _HAND_TUNED_CIRCLE_MAX_DIAMETER_PX,
    _SINGLE_CIRCLE_DIAMETER_PX,
    CIRCLE_CARD_TEMPLATES,
    STORY_CIRCLE_LAYOUTS,
    TILES_CIRCLE_CLUSTER_PORTRAIT_MAX,
    TILES_CIRCLE_CLUSTER_SQUARE_MAX,
    TILES_CIRCLE_CLUSTER_STORY_MAX,
    _tiles_circle_canvas_size,
)


def test_circle_layout_playground_html_includes_all_modes():
    html = render_circle_layout_playground_html()
    assert "Statistics Tiles" in html
    assert "Spotlight" in html
    assert '"modes"' in html
    assert "pointerdown" in html
    assert "Copy export" in html
    assert "card_type:" in html
    assert "target_code:" in html
    assert '"layout_label": "Statistics Tiles"' in html
    assert "Implement this card design" in html
    assert "diameter_px:" in html
    assert '"10": 255' in html
    for card_type in PLAYGROUND_CARD_TYPES:
        assert f'"{card_type}"' in html
    for fmt in PLAYGROUND_FORMATS:
        assert f'"{fmt}"' in html
    for count in STORY_CIRCLE_LAYOUTS:
        assert f'"{count}":' in html


def test_circle_layout_playground_tiles_uses_format_specific_count_limits():
    html = render_circle_layout_playground_html(
        initial_card_type="tiles",
        initial_fmt="story",
    )
    assert f'"min_count": {PLAYGROUND_TILES_MIN_COUNT}' in html
    assert f'"max_count": {TILES_CIRCLE_CLUSTER_STORY_MAX}' in html
    assert f'"default_count": {PLAYGROUND_TILES_DEFAULT_COUNT}' in html
    assert '"1":' in html
    assert '"5":' in html
    expected_max = {
        "square": TILES_CIRCLE_CLUSTER_SQUARE_MAX,
        "portrait_post": TILES_CIRCLE_CLUSTER_PORTRAIT_MAX,
        "story": TILES_CIRCLE_CLUSTER_STORY_MAX,
    }
    for fmt in PLAYGROUND_FORMATS:
        fmt_html = render_circle_layout_playground_html(initial_card_type="tiles", initial_fmt=fmt)
        assert f'"min_count": {PLAYGROUND_TILES_MIN_COUNT}' in fmt_html
        assert f'"max_count": {expected_max[fmt]}' in fmt_html
        assert f'"default_count": {PLAYGROUND_TILES_DEFAULT_COUNT}' in fmt_html


def test_circle_layout_playground_count_change_loads_code_defaults_when_untouched():
    html = render_circle_layout_playground_html(
        initial_card_type="tiles",
        initial_fmt="portrait_post",
    )
    assert "const sessionEdits = new Map();" in html
    assert "function layoutKeyFor(" in html
    assert "function codeDefaults(n)" in html
    assert "function applyDiameterWithoutSessionSave(d)" in html
    assert "function loadLayoutState(n)" in html
    assert "sessionEdits.get(key)" in html
    assert "clearSessionEdit(layoutKey());" in html
    assert "loadLayoutState(count);" in html
    assert "if (drag.moved) saveSessionEdit();" in html
    assert "if (!applyingDefaults) saveSessionEdit();" in html


def test_circle_layout_playground_spotlight_is_not_draggable():
    html = render_circle_layout_playground_html(
        initial_card_type="spotlight",
        initial_fmt="square",
    )
    assert '"draggable": false' in html
    assert "fixed centre" in html


def test_circle_layout_playground_story_tiles_uses_code_layout():
    html = render_circle_layout_playground_html(
        initial_card_type="tiles",
        initial_fmt="story",
    )
    assert "CIRCLE_CARD_TEMPLATES" in html
    assert f'"max_diameter": {_HAND_TUNED_CIRCLE_MAX_DIAMETER_PX}' in html
    assert f'"1": {_SINGLE_CIRCLE_DIAMETER_PX}' in html
    assert '"2": 380' in html
    assert '"3": 380' in html
    assert '"6": 340' in html
    assert '"7": 295' in html
    assert '"canvas_h": 1490' in html
    assert "0.29" in html


def test_circle_layout_playground_portrait_tiles_uses_code_layout():
    html = render_circle_layout_playground_html(
        initial_card_type="tiles",
        initial_fmt="portrait_post",
    )
    assert "CIRCLE_CARD_TEMPLATES" in html
    assert "portrait_post" in html
    assert f'"1": {_SINGLE_CIRCLE_DIAMETER_PX}' in html
    assert '"6": 255' in html
    assert '"7": 255' in html
    assert '"8": 245' in html
    assert '"canvas_h": 968' in html
    assert "0.46" in html


def test_circle_layout_playground_square_tiles_uses_code_layout():
    html = render_circle_layout_playground_html(
        initial_card_type="tiles",
        initial_fmt="square",
    )
    assert "CIRCLE_CARD_TEMPLATES" in html
    assert f'"max_diameter": {_HAND_TUNED_CIRCLE_MAX_DIAMETER_PX}' in html
    assert f'"1": {_SINGLE_CIRCLE_DIAMETER_PX}' in html
    assert '"2": 360' in html
    assert '"3": 285' in html
    assert '"4": 275' in html
    assert '"5": 265' in html
    assert '"6": 250' in html
    assert '"7": 237' not in html
    assert '"canvas_h": 698' in html


def test_circle_card_templates_registry_has_story_and_portrait():
    assert ("tiles", "story") in CIRCLE_CARD_TEMPLATES
    assert ("tiles", "portrait_post") in CIRCLE_CARD_TEMPLATES
    assert ("tiles", "square") in CIRCLE_CARD_TEMPLATES
    assert CIRCLE_CARD_TEMPLATES[("tiles", "story")].bounds == "story"
    assert CIRCLE_CARD_TEMPLATES[("tiles", "portrait_post")].bounds == "cluster"
    assert CIRCLE_CARD_TEMPLATES[("tiles", "square")].bounds == "cluster"


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

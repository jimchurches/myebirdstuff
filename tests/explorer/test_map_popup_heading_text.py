"""Tests for universal popup title text helpers."""

from __future__ import annotations

from explorer.presentation.map_popup_heading_text import prevent_orphan_closing_punctuation


def test_orphan_closing_paren_at_end_of_title():
    raw = "Kimba ( -33.146269, 136.414773 )"
    out = prevent_orphan_closing_punctuation(raw)
    assert out.endswith("\u00a0)")
    assert " (\u00a0" not in out


def test_orphan_fix_does_not_touch_open_paren_space():
    raw = "Lake Gilles ( -33.0, 136.6 )"
    out = prevent_orphan_closing_punctuation(raw)
    assert " (" in out
    assert out.endswith("\u00a0)")


def test_orphan_fix_skips_titles_without_trailing_close_punct():
    raw = "Lake Gilles Conservation Park--Track at -33.0"
    assert prevent_orphan_closing_punctuation(raw) == raw

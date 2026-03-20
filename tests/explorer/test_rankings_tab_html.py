"""Tests for Rankings tab HTML shell (refs #69)."""

from personal_ebird_explorer.checklist_stats_display import format_rankings_tab_html


def test_format_rankings_tab_html_structure_and_top_n_heading():
    html = format_rankings_tab_html(
        [("Section A", "<p>alpha</p>")],
        [("Section B", "<p>beta</p>")],
        top_n_limit=42,
    )
    assert "<h3 " in html
    assert "Top 42</h3>" in html
    assert "Interesting Lists</h3>" in html
    assert "<summary>Section A</summary>" in html
    assert "<summary>Section B</summary>" in html
    assert "<p>alpha</p>" in html
    assert "<p>beta</p>" in html
    assert ".maint-section" in html

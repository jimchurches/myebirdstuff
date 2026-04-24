"""Tests for checklist-style HTML table helpers (refs #117)."""

import html as html_module

from explorer.presentation.stats_html_helpers import (
    METRIC_CELL_STYLE,
    a_external,
    esc_attr,
    esc_text,
    td_plain,
    th_plain,
    tr_row,
)


def test_esc_text_escapes_markup():
    assert esc_text("<b>x</b>") == html_module.escape("<b>x</b>", quote=False)


def test_esc_attr_for_href():
    s = 'https://x.com/a?b="'
    assert esc_attr(s) == html_module.escape(s, quote=True)


def test_tr_row_and_td_plain():
    row = tr_row(td_plain("a"), td_plain(42, style=METRIC_CELL_STYLE))
    assert row == (
        "<tr><td>a</td>"
        f'<td style="{METRIC_CELL_STYLE}">42</td>'
        "</tr>"
    )


def test_th_plain():
    assert "<script>" not in th_plain("<script>")
    assert "text-align:right" in th_plain("Y", style="text-align:right;")


def test_a_external_escapes_and_attributes():
    html = a_external("https://ebird.org/species/foo", "Bird & co")
    assert 'href="https://ebird.org/species/foo"' in html
    assert "Bird &amp; co" in html
    assert 'target="_blank"' in html
    assert "noopener" in html

"""Tests for checklist-style HTML table helpers (refs #117)."""

import html as html_module

from explorer.presentation.stats_html_helpers import (
    METRIC_CELL_STYLE,
    a_external,
    esc_attr,
    esc_text,
    safe_http_url,
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


def test_safe_http_url_accepts_http_and_https():
    assert safe_http_url("https://ebird.org/checklist/S1") == "https://ebird.org/checklist/S1"
    assert safe_http_url("  http://example.com/x  ") == "http://example.com/x"


def test_safe_http_url_rejects_non_http_schemes():
    assert safe_http_url("") == ""
    assert safe_http_url("javascript:alert(1)") == ""
    assert safe_http_url("data:text/html,hi") == ""
    assert safe_http_url("//evil.example/") == ""
    assert safe_http_url("/relative/path") == ""


def test_a_external_unsafe_href_renders_plain_text():
    html = a_external("javascript:alert(1)", "Click me")
    assert "<a " not in html
    assert html == "Click me"

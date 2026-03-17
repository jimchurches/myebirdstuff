"""Unit tests for personal_ebird_explorer.rankings_display (rankings table HTML builders)."""

import pytest

from personal_ebird_explorer.rankings_display import (
    rankings_scroll_wrapper,
    rankings_table,
    rankings_table_location_5col,
    rankings_table_with_rank,
    rankings_visited_table,
    rankings_seen_once_table,
)


def test_rankings_scroll_wrapper_structure():
    """Scroll wrapper contains expected classes and max-height from visible_rows."""
    html = rankings_scroll_wrapper("<table></table>", scroll_hint="shading", visible_rows=16)
    assert "rankings-scroll-wrapper" in html
    assert "rankings-scroll-inner" in html
    assert "max-height:608px" in html  # 16 * 38
    assert "<table></table>" in html


def test_rankings_scroll_wrapper_max_height_scales():
    """Max-height scales with visible_rows (38px per row)."""
    html = rankings_scroll_wrapper("<table></table>", scroll_hint="shading", visible_rows=10)
    assert "max-height:380px" in html


def test_rankings_table_empty_rows_no_data():
    """Empty rows produce No data. message."""
    out = rankings_table("My Title", ["A", "B", "C"], [], include_heading=True)
    assert "No data." in out
    assert "My Title" in out
    assert "<tbody>" not in out or "<tr>" not in out


def test_rankings_table_one_row_has_one_tr():
    """Single row produces one tbody row with expected content."""
    out = rankings_table("Title", ["Col1", "Col2", "Col3"], [("a", "b", "42")], include_heading=True)
    assert out.count("<tr>") >= 2  # header + body
    assert "a</td>" in out
    assert "b</td>" in out
    assert "42</td>" in out


def test_rankings_table_location_5col_empty_no_data():
    """Empty rows produce No data."""
    out = rankings_table_location_5col("Locations", ["Loc", "State", "Country", "X", "Y"], [])
    assert "No data." in out


def test_rankings_table_location_5col_one_row_structure():
    """One row produces table with Location, State, Country columns (region_display may resolve codes)."""
    row = ("Place One", "NSW", "AU", "3", "12")
    out = rankings_table_location_5col("Title", ["Location", "State", "Country", "Checklists", "Species"], [row])
    assert "Place One" in out
    assert "3</td>" in out
    assert "12</td>" in out
    assert "location-cols-tbl" in out


def test_rankings_table_with_rank_empty_no_data():
    """Empty rows_3col produce No data."""
    out = rankings_table_with_rank("Species", ["Species", "", "N"], [])
    assert "No data." in out


def test_rankings_table_with_rank_one_row_has_rank_one():
    """Single row gets Rank 1 and content in output."""
    out = rankings_table_with_rank("Top", ["Name", "X", "Count"], [("Grey Teal", "—", "5")])
    assert "1</td>" in out
    assert "Grey Teal" in out
    assert "5</td>" in out
    assert "rank-tbl" in out


def test_rankings_visited_table_empty_no_data():
    """Empty rows produce No data. for visited table."""
    out = rankings_visited_table([], include_heading=True)
    assert "No data." in out
    assert "Most visited" in out


def test_rankings_seen_once_table_empty_no_data():
    """Empty rows produce No data. for seen-once table."""
    out = rankings_seen_once_table([], include_heading=True)
    assert "No data." in out
    assert "Seen only once" in out


def test_rankings_table_with_rank_species_url_fn_injects_links():
    """When species_url_fn is provided and returns a URL, species name is linked (refs #56)."""
    def url_fn(name):
        return "https://ebird.org/species/grtea" if name == "Grey Teal" else None
    out = rankings_table_with_rank(
        "Top",
        ["Species", "", "Count"],
        [("Grey Teal", "—", "10")],
        species_url_fn=url_fn,
    )
    assert "Grey Teal" in out
    assert 'href="https://ebird.org/species/grtea"' in out


def test_rankings_table_with_rank_lifelist_url_fn_injects_link():
    """When lifelist_url_fn is provided, the count number is the lifelist link (refs #56)."""
    def lifelist_fn(name):
        return "https://ebird.org/lifelist?spp=grtea" if name == "Grey Teal" else None
    out = rankings_table_with_rank(
        "Checklists",
        ["Species", "", "Checklists"],
        [("Grey Teal", "—", "5")],
        lifelist_url_fn=lifelist_fn,
    )
    assert "lifelist?spp=grtea" in out
    assert ">5</a>" in out  # count is the link text


def test_rankings_seen_once_table_species_url_fn_injects_links():
    """When species_url_fn is provided, Species column is linked (refs #56)."""
    def url_fn(name):
        return "https://ebird.org/species/grtea" if name == "Grey Teal" else None
    out = rankings_seen_once_table(
        [("Grey Teal", "Loc", "NSW", "AU", "2024-01-01", "1")],
        include_heading=False,
        species_url_fn=url_fn,
    )
    assert 'href="https://ebird.org/species/grtea"' in out
    assert "Grey Teal" in out

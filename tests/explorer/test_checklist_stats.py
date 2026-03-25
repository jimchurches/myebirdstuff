import pandas as pd
import pytest
from personal_ebird_explorer.checklist_stats_compute import compute_checklist_stats_payload
from personal_ebird_explorer.checklist_stats_display import format_checklist_stats_bundle


def _compute_checklist_stats(df: pd.DataFrame):
    payload = compute_checklist_stats_payload(df, top_n_limit=10)
    return format_checklist_stats_bundle(payload, scroll_hint=0, visible_rows=200)


def make_minimal_df():
    # Single checklist with a single species, with just enough columns
    data = {
        "Submission ID": ["S1"],
        "Date": [pd.Timestamp("2025-01-01")],
        "Time": ["06:15"],
        "Count": [3],
        "Location ID": ["L1"],
        "Location": ["Test Location"],
        "Scientific Name": ["Anas gracilis"],
        "Common Name": ["Grey Teal"],
        "Latitude": [-35.0],
        "Longitude": [149.0],
        "Protocol": ["Traveling"],
        "Duration (Min)": [30],
        "Distance Traveled (km)": [1.5],
        "All Obs Reported": [1],
        "Number of Observers": [2],
    }
    return pd.DataFrame(data)


def test_compute_checklist_stats_returns_expected_keys():
    df = make_minimal_df()

    stats = _compute_checklist_stats(df)

    # Basic shape: main HTML, rankings, yearly summary, and incomplete map
    assert "stats_html" in stats
    assert "rankings_sections_top_n" in stats
    assert "rankings_sections_other" in stats
    assert "yearly_summary_html" in stats
    assert "country_summary_html" in stats
    assert "incomplete_by_year" in stats

    html = stats["stats_html"]

    # Overview table: exact rows for total checklists/species/individuals
    # `_table` renders rows as `<tr><td>{label}</td><td>{value}</td></tr>`
    assert "<tr><td>Total checklists</td><td>1</td></tr>" in html
    assert "<tr><td>Total species</td><td>1</td></tr>" in html
    assert "<tr><td>Total individuals</td><td>3</td></tr>" in html

    # Total Distance table: single checklist with 1.5 km traveled
    assert "<tr><td>Kilometers traveled</td><td>1.50</td></tr>" in html


def test_compute_checklist_stats_repeated_species_and_multi_year():
    # Two rows for the same species on the same checklist (repeated species),
    # plus a second checklist in a different year.
    data = {
        "Submission ID": ["S1", "S1", "S2"],
        "Date": [
            pd.Timestamp("2025-01-01"),
            pd.Timestamp("2025-01-01"),
            pd.Timestamp("2026-02-02"),
        ],
        "Time": ["06:15", "07:00", "08:00"],
        "Count": [2, 3, 4],  # S1: total 5, S2: 4 → 9 individuals
        "Location ID": ["L1", "L1", "L2"],
        "Location": ["Loc1", "Loc1", "Loc2"],
        "Scientific Name": ["Anas gracilis", "Anas gracilis", "Anas castanea"],
        "Common Name": ["Grey Teal", "Grey Teal", "Chestnut Teal"],
        "Latitude": [-35.0, -35.0, -36.0],
        "Longitude": [149.0, 149.0, 150.0],
        "Protocol": ["Traveling", "Traveling", "Stationary"],
        "Duration (Min)": [30, 15, 20],
        "Distance Traveled (km)": [1.5, 0.5, 0.0],
        "All Obs Reported": [1, 1, 1],
        "Number of Observers": [2, 2, 1],
    }
    df = pd.DataFrame(data)

    stats = _compute_checklist_stats(df)

    html = stats["stats_html"]
    yearly_html = stats["yearly_summary_html"]

    # Overview: total checklists = 2 (S1, S2), total species = 2, individuals = 9.
    # Distances are at checklist level (drop_duplicates on Submission ID), so
    # S1 contributes 1.5 km (the first row kept), S2 contributes 0.0 km.
    assert "<tr><td>Total checklists</td><td>2</td></tr>" in html
    assert "<tr><td>Total species</td><td>2</td></tr>" in html
    assert "<tr><td>Total individuals</td><td>9</td></tr>" in html

    # Total distance: 1.5 km across both checklists (second S1 row is ignored at checklist level)
    assert "<tr><td>Kilometers traveled</td><td>1.50</td></tr>" in html

    # Yearly summary should include both years as headers
    assert "<th style='text-align:right;'>2025</th>" in yearly_html
    assert "<th style='text-align:right;'>2026</th>" in yearly_html

    # And total checklists row should show 1 in each year column
    assert (
        "<tr><td>Total checklists</td><td style='text-align:right;'>1</td>"
        "<td style='text-align:right;'>1</td></tr>" in yearly_html
    )


def test_country_tab_html_sort_by_metric_changes_accordion_order():
    """Country accordions order by Lifers (world) or Total species when requested."""
    import re

    from personal_ebird_explorer.checklist_stats_display import (
        COUNTRY_TAB_SORT_ALPHABETICAL,
        COUNTRY_TAB_SORT_LIFERS_WORLD,
        COUNTRY_TAB_SORT_TOTAL_SPECIES,
        _format_country_summary_html,
    )

    def _accordion_titles(html: str):
        return re.findall(r"<summary>([^<]+)</summary>", html)

    # Two countries: US has fewer lifers (world) but fewer total species than AU
    rows_us = [
        ("Lifers (world)", ["1"]),
        ("Lifers (country)", ["1"]),
        ("Total species", ["5"]),
        ("Total individuals", ["10"]),
        ("Total checklists", ["1"]),
        ("Days with a checklist", ["1"]),
        ("Cumulative days eBird on", ["1"]),
    ]
    rows_au = [
        ("Lifers (world)", ["3"]),
        ("Lifers (country)", ["3"]),
        ("Total species", ["20"]),
        ("Total individuals", ["100"]),
        ("Total checklists", ["2"]),
        ("Days with a checklist", ["2"]),
        ("Cumulative days eBird on", ["2"]),
    ]
    sections = [("US", [2025], rows_us), ("AU", [2025], rows_au)]

    html_alpha = _format_country_summary_html(sections, country_sort=COUNTRY_TAB_SORT_ALPHABETICAL)
    html_lifers = _format_country_summary_html(sections, country_sort=COUNTRY_TAB_SORT_LIFERS_WORLD)
    html_sp = _format_country_summary_html(sections, country_sort=COUNTRY_TAB_SORT_TOTAL_SPECIES)

    ta = _accordion_titles(html_alpha)
    tl = _accordion_titles(html_lifers)
    ts = _accordion_titles(html_sp)
    assert len(ta) == len(tl) == len(ts) == 2

    # Alphabetical by display name
    assert ta == sorted(ta)

    # By life birds / total species: AU ranks above US (higher metric)
    assert tl[0] in ("Australia", "AU") and tl[1] in ("United States", "US")
    assert ts[0] in ("Australia", "AU") and ts[1] in ("United States", "US")


def test_country_sections_sort_alphabetically_by_display_name():
    """Country accordions follow alphabetical order of resolved country names (refs display sort)."""
    pytest.importorskip("pycountry")
    from personal_ebird_explorer.checklist_stats_display import _country_heading_sort_key

    assert _country_heading_sort_key("AU") < _country_heading_sort_key("US")
    assert _country_heading_sort_key("US") < _country_heading_sort_key("_UNKNOWN")


def test_country_summary_html_includes_total_when_multi_year():
    data = {
        "Submission ID": ["S1", "S2"],
        "Date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2026-02-02")],
        "Time": ["06:15", "08:00"],
        "Count": [1, 1],
        "Location ID": ["L1", "L2"],
        "Location": ["Loc1", "Loc2"],
        "Scientific Name": ["Anas gracilis", "Anas castanea"],
        "Common Name": ["Grey Teal", "Chestnut Teal"],
        "Latitude": [-35.0, -36.0],
        "Longitude": [149.0, 150.0],
        "Protocol": ["Traveling", "Stationary"],
        "Duration (Min)": [30, 20],
        "Distance Traveled (km)": [1.5, 0.0],
        "All Obs Reported": [1, 1],
        "Number of Observers": [1, 1],
        "State/Province": ["AU-NSW", "AU-NSW"],
    }
    df = pd.DataFrame(data)
    stats = _compute_checklist_stats(df)
    assert "<th style='text-align:right;'>Total</th>" in stats["country_summary_html"]


def test_country_summary_html_present_with_state_province():
    data = {
        **{k: v for k, v in make_minimal_df().to_dict("list").items()},
        "State/Province": ["AU-NSW"],
    }
    df = pd.DataFrame(data)
    stats = _compute_checklist_stats(df)
    ch = stats["country_summary_html"]
    assert "By country" in ch
    assert "yearly-maint-section" in ch
    assert "Lifers (world)" in ch
    assert "Days with a checklist" in ch


def test_country_iso_rows_have_ebird_region_links():
    """Lifers (country) and Total checklists rows get ⧉ links when key is ISO alpha-2."""
    from personal_ebird_explorer.checklist_stats_display import _format_country_summary_html

    rows = [
        ("Lifers (world)", ["1"]),
        ("Lifers (country)", ["1"]),
        ("Total species", ["1"]),
        ("Total individuals", ["1"]),
        ("Total checklists", ["1"]),
        ("Days with a checklist", ["1"]),
        ("Cumulative days eBird on", ["1"]),
    ]
    html_fr = _format_country_summary_html([("FR", [2025], rows)])
    assert "Lifers (country)" in html_fr
    assert "Total checklists" in html_fr
    assert 'href="https://ebird.org/lifelist?r=FR"' in html_fr
    assert 'href="https://ebird.org/mychecklists/FR"' in html_fr
    # Two ⧉ links (lifers + checklists)
    assert html_fr.count("⧉") >= 2

    html_unknown = _format_country_summary_html([("_UNKNOWN", [2025], rows)])
    assert "Lifers (country)" in html_unknown
    assert 'href="https://ebird.org/lifelist?r=' not in html_unknown
    assert 'href="https://ebird.org/mychecklists/' not in html_unknown


def test_format_country_yearly_table_html_matches_accordion_markup():
    """Extracted yearly table HTML matches Country-tab accordion table structure (refs #75)."""
    from personal_ebird_explorer.checklist_stats_display import (
        format_country_yearly_table_html,
        _format_country_summary_html,
    )

    rows = [
        ("Lifers (world)", ["1", "2", "3"]),
        ("Lifers (country)", ["0", "1", "1"]),
        ("Total species", ["5", "6", "11"]),
        ("Total individuals", ["10", "20", "30"]),
        ("Total checklists", ["1", "1", "2"]),
        ("Days with a checklist", ["1", "1", "2"]),
        ("Cumulative days eBird on", ["1", "2", "2"]),
    ]
    inner = format_country_yearly_table_html("DE", [2024, 2025], rows)
    full = _format_country_summary_html([("DE", [2024, 2025], rows)])
    assert "<th style='text-align:right;'>Total</th>" in inner
    assert inner in full
    # Same eBird links in first column as full country HTML
    assert 'href="https://ebird.org/lifelist?r=DE"' in inner
    assert 'href="https://ebird.org/mychecklists/DE"' in inner


def test_country_yearly_links_bar_html_for_iso():
    from personal_ebird_explorer.checklist_stats_display import country_yearly_links_bar_html

    h = country_yearly_links_bar_html("NZ")
    assert "Country page" in h
    assert "Country lifers" in h
    assert "Country checklists" in h
    assert 'href="https://ebird.org/region/NZ"' in h
    assert 'href="https://ebird.org/lifelist?r=NZ"' in h
    assert 'href="https://ebird.org/mychecklists/NZ"' in h
    assert h.index("Country page") < h.index("Country lifers") < h.index("Country checklists")

    assert country_yearly_links_bar_html("_UNKNOWN") == ""


def test_format_country_yearly_table_html_inline_links_optional():
    from personal_ebird_explorer.checklist_stats_display import format_country_yearly_table_html

    rows = [
        ("Lifers (country)", ["1"]),
        ("Total checklists", ["1"]),
    ]
    with_links = format_country_yearly_table_html("FR", [2025], rows, inline_statistic_links=True)
    without = format_country_yearly_table_html("FR", [2025], rows, inline_statistic_links=False)
    assert "⧉" in with_links
    assert 'href="https://ebird.org/lifelist?r=FR"' in with_links
    assert "⧉" not in without
    assert 'href="https://ebird.org/lifelist' not in without
    assert 'href="https://ebird.org/mychecklists' not in without


def test_compute_checklist_stats_country_displayed_as_name():
    """Country codes are shown as country names in rankings tables (refs #43)."""
    pytest.importorskip("pycountry")

    data = {
        **{k: v for k, v in make_minimal_df().to_dict("list").items()},
        "State/Province": ["AU-NSW"],
    }
    df = pd.DataFrame(data)

    stats = _compute_checklist_stats(df)

    rankings_html = " ".join(
        html for _, html in stats["rankings_sections_top_n"] + stats["rankings_sections_other"]
    )
    assert "Australia" in rankings_html, "ISO code AU should be displayed as Australia"


def test_compute_checklist_stats_unknown_country_code_shown_as_code():
    """Unknown/invalid country codes are shown as-is (display fallback, refs #43)."""
    pytest.importorskip("pycountry")

    data = {
        "Submission ID": ["S1", "S2"],
        "Date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")],
        "Time": ["06:15", "07:00"],
        "Count": [1, 1],
        "Location ID": ["L1", "L2"],
        "Location": ["Loc AU", "Loc XX"],
        "Scientific Name": ["Anas gracilis", "Anas platyrhynchos"],
        "Common Name": ["Grey Teal", "Mallard"],
        "Latitude": [-35.0, -36.0],
        "Longitude": [149.0, 150.0],
        "Protocol": ["Traveling", "Traveling"],
        "Duration (Min)": [30, 30],
        "Distance Traveled (km)": [1.0, 1.0],
        "All Obs Reported": [1, 1],
        "Number of Observers": [1, 1],
        "State/Province": ["AU-NSW", "XX-YY"],
    }
    df = pd.DataFrame(data)

    stats = _compute_checklist_stats(df)

    rankings_html = " ".join(
        html for _, html in stats["rankings_sections_top_n"] + stats["rankings_sections_other"]
    )
    assert "Australia" in rankings_html
    assert "XX" in rankings_html, "Unknown code XX should be shown as-is"


def test_compute_checklist_stats_state_displayed_as_name():
    """State/subdivision codes are shown as names in rankings tables (refs #43)."""
    pytest.importorskip("pycountry")

    data = {
        **{k: v for k, v in make_minimal_df().to_dict("list").items()},
        "State/Province": ["AU-NSW"],
    }
    df = pd.DataFrame(data)

    stats = _compute_checklist_stats(df)

    rankings_html = " ".join(
        html for _, html in stats["rankings_sections_top_n"] + stats["rankings_sections_other"]
    )
    assert "New South Wales" in rankings_html, "AU-NSW should be displayed as New South Wales"


def test_compute_checklist_stats_unknown_state_code_shown_as_code():
    """Unknown subdivision codes are shown as-is (display fallback, refs #43)."""
    pytest.importorskip("pycountry")

    data = {
        "Submission ID": ["S1", "S2"],
        "Date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")],
        "Time": ["06:15", "07:00"],
        "Count": [1, 1],
        "Location ID": ["L1", "L2"],
        "Location": ["Loc NSW", "Loc X9"],
        "Scientific Name": ["Anas gracilis", "Anas platyrhynchos"],
        "Common Name": ["Grey Teal", "Mallard"],
        "Latitude": [-35.0, -36.0],
        "Longitude": [149.0, 150.0],
        "Protocol": ["Traveling", "Traveling"],
        "Duration (Min)": [30, 30],
        "Distance Traveled (km)": [1.0, 1.0],
        "All Obs Reported": [1, 1],
        "Number of Observers": [1, 1],
        "State/Province": ["AU-NSW", "AU-X9"],
    }
    df = pd.DataFrame(data)

    stats = _compute_checklist_stats(df)

    rankings_html = " ".join(
        html for _, html in stats["rankings_sections_top_n"] + stats["rankings_sections_other"]
    )
    assert "New South Wales" in rankings_html
    assert "X9" in rankings_html, "Unknown state code X9 should be shown as-is"



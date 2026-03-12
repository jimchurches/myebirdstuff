import pandas as pd

from notebooks.personal_ebird_explorer import _compute_checklist_stats


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



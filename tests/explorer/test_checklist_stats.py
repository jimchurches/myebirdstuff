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

    # Basic shape: should have main HTML and both rankings collections
    assert "stats_html" in stats
    assert "rankings_sections_top_n" in stats
    assert "rankings_sections_other" in stats
    assert "yearly_summary_html" in stats
    assert "incomplete_by_year" in stats

    # Sanity check: overview HTML mentions total checklists = 1
    assert "Total checklists" in stats["stats_html"]
    assert "1" in stats["stats_html"]


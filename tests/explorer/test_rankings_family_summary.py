"""Family coverage overview metrics (refs Family Lists tab)."""

from __future__ import annotations

import pandas as pd


def test_family_coverage_summary_metrics_df_counts():
    from explorer.app.streamlit.rankings_streamlit_html import _family_coverage_summary_metrics_df

    summary = pd.DataFrame(
        {
            "group_name": ["A", "B", "C", "D"],
            "seen_species": [2, 0, 5, 3],
            "total_species": [2, 5, 5, 10],
            "percent_seen": [100.0, 0.0, 100.0, 30.0],
        }
    )
    out = _family_coverage_summary_metrics_df(summary)
    assert len(out) == 5
    # Total 4; ≥1 species: A,B,C,D with seen>0 -> A,C,D = 3; B has 0 -> 3 families
    assert out.loc[0, "Value"] == "4"
    assert out.loc[1, "Value"] == "3"
    # Fully recorded: A (2/2), C (5/5) = 2
    assert out.loc[2, "Value"] == "2"
    assert out.loc[3, "Value"] == "75.0%"
    assert out.loc[4, "Value"] == "50.0%"


def test_family_coverage_summary_metrics_df_empty():
    from explorer.app.streamlit.rankings_streamlit_html import _family_coverage_summary_metrics_df

    out = _family_coverage_summary_metrics_df(pd.DataFrame())
    assert out.empty

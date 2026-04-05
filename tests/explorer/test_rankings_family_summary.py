"""Family coverage overview metrics (refs Families tab)."""

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
    assert len(out) == 12
    assert list(out.columns) == ["Section", "Metric", "Value"]
    assert out.loc[0, "Section"] == "Taxonomy"
    assert out.loc[0, "Metric"] == "Total families"
    assert out.loc[0, "Value"] == "4"
    # Coverage: observed count, observed %, fully recorded count, fully recorded %
    assert out.loc[1, "Section"] == "Coverage"
    assert out.loc[1, "Value"] == "3"  # A,C,D seen>0
    assert out.loc[2, "Value"] == "75.0%"
    assert out.loc[3, "Value"] == "2"  # A,C fully recorded
    assert out.loc[4, "Value"] == "50.0%"
    # Progress
    assert out.loc[5, "Section"] == "Progress"
    assert out.loc[5, "Value"] == "2"  # ≥90%: A, C
    assert out.loc[6, "Value"] == "2"  # ≥75%: A, C
    assert out.loc[7, "Value"] == "2"  # ≥50%: A, C (D is 30%)
    # Distribution: percent_seen mean / median
    assert out.loc[8, "Section"] == "Distribution"
    assert out.loc[8, "Value"] == "57.5%"
    assert out.loc[9, "Value"] == "65.0%"
    # Edge case
    assert out.loc[10, "Section"] == "Edge case"
    assert out.loc[10, "Value"] == "0"  # total_species == 1
    assert out.loc[11, "Value"] == "1"  # seen == 0: B


def test_family_coverage_summary_metrics_df_empty():
    from explorer.app.streamlit.rankings_streamlit_html import _family_coverage_summary_metrics_df

    out = _family_coverage_summary_metrics_df(pd.DataFrame())
    assert out.empty


def test_family_coverage_summary_metrics_html_group_rows():
    from explorer.app.streamlit.rankings_streamlit_html import _family_coverage_summary_metrics_html

    summary = pd.DataFrame(
        {
            "group_name": ["A"],
            "seen_species": [1],
            "total_species": [1],
            "percent_seen": [100.0],
        }
    )
    html_out = _family_coverage_summary_metrics_html(summary)
    assert "family-coverage-overview" in html_out
    assert "family-coverage-group" in html_out
    assert "Taxonomy" in html_out
    assert "Coverage" in html_out
    assert "<th colspan=\"2\">" in html_out

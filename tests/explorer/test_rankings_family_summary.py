"""Family coverage overview metrics (refs Bird Families tab)."""

from __future__ import annotations

import pandas as pd
import pytest


def test_family_coverage_summary_metrics_df_counts():
    from explorer.app.streamlit.bird_families_streamlit_html import family_coverage_summary_metrics_df

    summary = pd.DataFrame(
        {
            "group_name": ["A", "B", "C", "D"],
            "seen_species": [2, 0, 5, 3],
            "total_species": [2, 5, 5, 10],
            "percent_seen": [100.0, 0.0, 100.0, 30.0],
        }
    )
    out = family_coverage_summary_metrics_df(summary)
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
    from explorer.app.streamlit.bird_families_streamlit_html import family_coverage_summary_metrics_df

    out = family_coverage_summary_metrics_df(pd.DataFrame())
    assert out.empty


def test_family_coverage_summary_metrics_html_group_rows():
    from explorer.app.streamlit.bird_families_streamlit_html import family_coverage_summary_metrics_html

    summary = pd.DataFrame(
        {
            "group_name": ["A"],
            "seen_species": [1],
            "total_species": [1],
            "percent_seen": [100.0],
        }
    )
    html_out = family_coverage_summary_metrics_html(summary)
    assert "family-coverage-overview" in html_out
    assert "family-coverage-group" in html_out
    assert "Taxonomy" in html_out
    assert "Coverage" in html_out
    assert "<th colspan=\"2\">" in html_out


def test_family_coverage_summary_metrics_integrates_world_species_rows():
    from explorer.app.streamlit.bird_families_streamlit_html import family_coverage_summary_metrics_df

    summary = pd.DataFrame(
        {
            "group_name": ["A"],
            "seen_species": [1],
            "total_species": [1],
            "percent_seen": [100.0],
        }
    )
    out = family_coverage_summary_metrics_df(summary, world_coverage=(752, 11062, 6.8))
    assert "World species coverage" not in set(out["Section"])
    taxonomy = out[out["Section"] == "Taxonomy"]
    assert list(taxonomy["Metric"]) == ["Total families", "Total species"]
    assert taxonomy.iloc[1]["Value"] == "11,062"
    coverage = out[out["Section"] == "Coverage"]
    assert list(coverage["Metric"]) == [
        "Observed families (at least one species)",
        "Observed species",
        "Observed families (%)",
        "Observed species (%)",
        "Fully recorded families (all species observed)",
        "Fully recorded families (%)",
    ]
    assert coverage.iloc[1]["Value"] == "752"
    assert coverage.iloc[3]["Value"] == "6.8%"


def test_world_species_coverage_list_html_footnote_excludes_extinct_by_default(monkeypatch):
    from explorer.app.streamlit import bird_families_streamlit_html as bf

    monkeypatch.setattr(bf, "TAXONOMY_INCLUDE_EXTINCT_SPECIES_IN_COVERAGE", False)
    html_out = bf.world_species_coverage_list_html(10, 100, 10.0)
    assert "Species in eBird taxonomy" in html_out
    assert "Observed species (%)" in html_out
    assert "excluded" in html_out.lower()


def test_world_species_coverage_list_html_footnote_includes_extinct_when_enabled(monkeypatch):
    from explorer.app.streamlit import bird_families_streamlit_html as bf

    monkeypatch.setattr(bf, "TAXONOMY_INCLUDE_EXTINCT_SPECIES_IN_COVERAGE", True)
    html_out = bf.world_species_coverage_list_html(10, 100, 10.0)
    assert "included" in html_out.lower()


def test_compute_world_species_coverage_counts_seen_base_species():
    from explorer.app.streamlit.bird_families_streamlit_html import compute_world_species_coverage

    detail = pd.DataFrame(
        {
            "base_species": ["anas gracilis", "corvus corax", "falco peregrinus"],
            "seen": [True, True, False],
        }
    )
    assert compute_world_species_coverage(detail) == (2, 3, pytest.approx(200 / 3))


def test_build_group_coverage_tables_excludes_extinct_species_by_default(monkeypatch):
    from explorer.app.streamlit import bird_families_streamlit_html as bf

    tax = pd.DataFrame(
        [
            {
                "scientific_name": "Aves vivus",
                "common_name": "Living Bird",
                "species_code": "livbrd",
                "taxon_order": 10.0,
                "base_species": "aves vivus",
                "is_extinct": False,
            },
            {
                "scientific_name": "Aves extinctus",
                "common_name": "Extinct Bird",
                "species_code": "extbrd",
                "taxon_order": 11.0,
                "base_species": "aves extinctus",
                "is_extinct": True,
            },
        ]
    )
    groups = [{"group_name": "All Birds", "group_order": 1, "bounds": [(0.0, 100.0)]}]
    df_full = pd.DataFrame(
        {
            "Scientific Name": ["Aves vivus", "Aves extinctus subsp."],
            "Common Name": ["Living Bird", "Extinct Bird"],
            "Count": [1, 1],
            "Submission ID": ["s1", "s2"],
            "Date": ["2020-01-01", "2020-01-02"],
        }
    )

    monkeypatch.setattr(bf, "_load_taxonomy_species_rows", lambda _loc: tax)
    monkeypatch.setattr(bf, "_load_taxonomy_groups", lambda _loc: groups)
    monkeypatch.setattr(bf, "TAXONOMY_INCLUDE_EXTINCT_SPECIES_IN_COVERAGE", False)

    summary, detail = bf.build_group_coverage_tables(df_full, "en_AU")
    assert summary.iloc[0]["total_species"] == 1
    assert len(detail) == 1
    assert bf.compute_world_species_coverage(detail) == (1, 1, 100.0)


def test_attach_group_coverage_stores_world_metrics_once(monkeypatch):
    from explorer.app.streamlit import bird_families_streamlit_html as bf

    tax = pd.DataFrame(
        [
            {
                "scientific_name": "Aves vivus",
                "common_name": "Living Bird",
                "species_code": "livbrd",
                "taxon_order": 10.0,
                "base_species": "aves vivus",
                "is_extinct": False,
            },
        ]
    )
    groups = [{"group_name": "All Birds", "group_order": 1, "bounds": [(0.0, 100.0)]}]
    df_full = pd.DataFrame(
        {
            "Scientific Name": ["Aves vivus"],
            "Common Name": ["Living Bird"],
            "Count": [1],
            "Submission ID": ["s1"],
            "Date": ["2020-01-01"],
        }
    )
    calls: list[str] = []
    original = bf.compute_world_species_coverage

    def _counting_compute(detail):
        calls.append("compute")
        return original(detail)

    monkeypatch.setattr(bf, "_load_taxonomy_species_rows", lambda _loc: tax)
    monkeypatch.setattr(bf, "_load_taxonomy_groups", lambda _loc: groups)
    monkeypatch.setattr(bf, "compute_world_species_coverage", _counting_compute)

    bundle = bf.attach_group_coverage_to_bundle({}, df_full, "en_AU")
    assert bundle[bf.WORLD_SPECIES_COVERAGE_METRICS_KEY] == (1, 1, 100.0)
    assert bundle[bf.WORLD_SPECIES_COVERAGE_SECTION_KEY][0] == "World species coverage"
    assert calls == ["compute"]

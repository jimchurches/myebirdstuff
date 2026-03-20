"""Tests for personal_ebird_explorer.working_set (refs #66)."""

import tempfile

import pandas as pd
from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import TEXT, Schema
from whoosh.index import create_in

from personal_ebird_explorer.working_set import WorkingSet, rebuild_working_set_from_date_filter


def _minimal_df():
    return pd.DataFrame(
        {
            "Location ID": ["L1", "L1", "L2", "L2"],
            "Location": ["A", "A", "B", "B"],
            "Latitude": [-33.0, -33.0, -34.0, -34.0],
            "Longitude": [151.0, 151.0, 150.0, 150.0],
            "Submission ID": ["S1", "S2", "S3", "S4"],
            "Date": pd.to_datetime(["2024-01-10", "2024-06-15", "2024-03-01", "2024-08-01"]),
            "Count": [1, 2, 1, 3],
            "Common Name": ["Grey Teal", "Grey Teal", "Pacific Black Duck", "Pacific Black Duck"],
            "Scientific Name": ["Anas gracilis", "Anas gracilis", "Anas superciliosa", "Anas superciliosa"],
        }
    )


def test_rebuild_no_filter_matches_full_for_locations():
    df_full = _minimal_df()
    lids = set(df_full["Location ID"].unique())
    popup, filtered = {}, __import__("collections").OrderedDict()
    ws = rebuild_working_set_from_date_filter(
        df_full,
        lids,
        filter_by_date=False,
        filter_start_date="2024-01-01",
        filter_end_date="2024-12-31",
        whoosh_index=None,
        map_caches=(popup, filtered),
    )
    assert ws is not None
    assert isinstance(ws, WorkingSet)
    assert len(ws.df) == 4
    assert set(ws.species_list) == {"Grey Teal", "Pacific Black Duck"}
    assert ws.total_checklists == 4
    assert ws.records_by_loc_full == {}
    assert ws.total_checklists_full == ws.total_checklists
    assert popup == {} and len(filtered) == 0


def test_rebuild_date_filter_subsets_rows():
    df_full = _minimal_df()
    lids = set(df_full["Location ID"].unique())
    ws = rebuild_working_set_from_date_filter(
        df_full,
        lids,
        filter_by_date=True,
        filter_start_date="2024-01-01",
        filter_end_date="2024-02-01",
        whoosh_index=None,
        map_caches=None,
    )
    assert ws is not None
    assert len(ws.df) == 1
    assert ws.species_list == ["Grey Teal"]
    assert ws.total_checklists == 1
    assert len(ws.records_by_loc_full) == 2
    assert ws.total_checklists_full == 4


def test_rebuild_invalid_dates_returns_none():
    df_full = _minimal_df()
    lids = set(df_full["Location ID"].unique())
    ws = rebuild_working_set_from_date_filter(
        df_full,
        lids,
        filter_by_date=True,
        filter_start_date="not-a-date",
        filter_end_date="2024-12-31",
        whoosh_index=None,
        map_caches=None,
    )
    assert ws is None


def test_rebuild_whoosh_index_updated():
    df_full = _minimal_df()
    lids = set(df_full["Location ID"].unique())
    schema = Schema(common_name=TEXT(stored=True, analyzer=StemmingAnalyzer()))
    index_dir = tempfile.mkdtemp()
    ix = create_in(index_dir, schema)
    w = ix.writer()
    w.add_document(common_name="Old Name")
    w.commit()

    ws = rebuild_working_set_from_date_filter(
        df_full,
        lids,
        filter_by_date=True,
        filter_start_date="2024-01-01",
        filter_end_date="2024-02-01",
        whoosh_index=ix,
        map_caches=None,
    )
    assert ws is not None
    with ix.searcher() as searcher:
        assert searcher.doc_count() == 1
        assert list(searcher.all_stored_fields()) == [{"common_name": "Grey Teal"}]


def test_map_caches_cleared_on_success():
    df_full = _minimal_df()
    lids = set(df_full["Location ID"].unique())
    popup = {"k": "v"}
    filtered = __import__("collections").OrderedDict([("a", 1)])
    rebuild_working_set_from_date_filter(
        df_full,
        lids,
        filter_by_date=False,
        filter_start_date="",
        filter_end_date="",
        map_caches=(popup, filtered),
    )
    assert popup == {}
    assert len(filtered) == 0

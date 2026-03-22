"""Tests for personal_ebird_explorer.species_search (refs #69, #70)."""

import tempfile

from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import TEXT, Schema
from whoosh.index import create_in

from personal_ebird_explorer.species_search import (
    build_ram_species_whoosh_index,
    whoosh_common_name_suggestions,
    whoosh_species_suggestions,
)


def test_whoosh_suggestions_short_query():
    schema = Schema(common_name=TEXT(stored=True, analyzer=StemmingAnalyzer()))
    ix = create_in(tempfile.mkdtemp(), schema)
    w = ix.writer()
    w.add_document(common_name="Grey Teal")
    w.commit()
    assert whoosh_common_name_suggestions(ix, "gr", min_query_len=3) == []
    assert whoosh_common_name_suggestions(ix, "gre", min_query_len=3) == ["Grey Teal"]


def test_whoosh_suggestions_ranking():
    schema = Schema(common_name=TEXT(stored=True, analyzer=StemmingAnalyzer()))
    ix = create_in(tempfile.mkdtemp(), schema)
    w = ix.writer()
    for name in ("Great Egret", "Great Cormorant", "Green Pygmy-goose"):
        w.add_document(common_name=name)
    w.commit()
    out = whoosh_common_name_suggestions(ix, "gre", max_options=6, min_query_len=3)
    assert len(out) >= 1
    assert all(isinstance(s, str) for s in out)


def test_whoosh_species_suggestions_matches_scientific_name():
    ix = build_ram_species_whoosh_index(
        ["Golden-hooded Tanager", "Grey Teal"],
        {"Golden-hooded Tanager": "Stilpnia larvata", "Grey Teal": "Anas gracilis"},
    )
    out = whoosh_species_suggestions(ix, "larv", min_query_len=3)
    assert "Golden-hooded Tanager" in out

    out2 = whoosh_species_suggestions(ix, "anas gra", min_query_len=3)
    assert "Grey Teal" in out2

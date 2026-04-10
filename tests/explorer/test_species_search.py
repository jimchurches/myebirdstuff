"""Tests for explorer.core.species_search (refs #69, #70)."""

import tempfile

from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import TEXT, Schema
from whoosh.index import create_in

from explorer.core.species_search import (
    build_ram_species_whoosh_index,
    normalize_query_for_group_filtered_mode,
    species_in_group_search_suggestions,
    species_whoosh_schema,
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


def test_normalize_query_for_group_filtered_mode_strips_submitted_group_row():
    g = "Australasian Robins"
    assert normalize_query_for_group_filtered_mode(f"{g} (group)", g) == ""
    assert normalize_query_for_group_filtered_mode(g, g) == ""
    assert normalize_query_for_group_filtered_mode("Flame", g) == "Flame"


def test_species_in_group_search_suggestions_empty_query_and_filter():
    names = ["Scarlet Robin", "Flame Robin", "Pink Robin"]
    assert species_in_group_search_suggestions(names, "", max_options=2) == ["Flame Robin", "Pink Robin"]
    assert species_in_group_search_suggestions(names, "scar", max_options=6) == ["Scarlet Robin"]
    assert species_in_group_search_suggestions(names, "rob", max_options=6) == [
        "Flame Robin",
        "Pink Robin",
        "Scarlet Robin",
    ]


def test_whoosh_species_suggestions_includes_taxonomy_group_row():
    ix = build_ram_species_whoosh_index(
        ["Grey Teal"],
        {"Grey Teal": "Anas gracilis"},
        taxonomy_group_names=["Ducks"],
    )
    out = whoosh_species_suggestions(ix, "duc", min_query_len=3)
    assert "Ducks (group)" in out


def test_whoosh_species_suggestions_restrict_taxonomy_group_token_search():
    """After picking a group, narrowing uses Whoosh tokens (common/sci), not raw substring (#73)."""
    ix = create_in(tempfile.mkdtemp(), species_whoosh_schema())
    w = ix.writer()
    grp = "Australian Treecreepers"
    w.add_document(
        common_name="Brown Treecreeper",
        scientific_name="Climacteris picumnus",
        taxonomy_group=grp,
        taxonomy_group_key=grp,
        kind="species",
    )
    w.add_document(
        common_name="Rufous Treecreeper",
        scientific_name="Climacteris rufa",
        taxonomy_group=grp,
        taxonomy_group_key=grp,
        kind="species",
    )
    w.commit()
    out = whoosh_species_suggestions(
        ix, "pic", restrict_taxonomy_group=grp, min_query_len=3
    )
    assert "Brown Treecreeper" in out
    assert "Rufous Treecreeper" not in out

    cleared = whoosh_species_suggestions(
        ix, f"{grp} (group)", restrict_taxonomy_group=grp, min_query_len=3
    )
    assert set(cleared) == {"Brown Treecreeper", "Rufous Treecreeper"}

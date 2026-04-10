"""Tests for explorer.core.species_search (refs #69, #70)."""

import tempfile

from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import TEXT, Schema
from whoosh.index import create_in

from explorer.core.species_search import (
    build_ram_species_whoosh_index,
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


def test_whoosh_species_suggestions_uses_taxonomy_group_helper_weight():
    ix = create_in(tempfile.mkdtemp(), species_whoosh_schema())
    w = ix.writer()
    w.add_document(
        common_name="Scarlet Robin",
        scientific_name="Petroica boodang",
        taxonomy_group="Australian Robins",
    )
    w.add_document(
        common_name="Australian Pipit",
        scientific_name="Anthus australis",
        taxonomy_group="Pipits and Wagtails",
    )
    w.commit()
    out = whoosh_species_suggestions(ix, "aus", min_query_len=3)
    assert out
    assert "Scarlet Robin" in out


def test_whoosh_species_suggestions_has_no_synthetic_group_rows():
    ix = create_in(tempfile.mkdtemp(), species_whoosh_schema())
    w = ix.writer()
    w.add_document(
        common_name="Brown Treecreeper",
        scientific_name="Climacteris picumnus",
        taxonomy_group="Australian Treecreepers",
    )
    w.add_document(
        common_name="Australian Pipit",
        scientific_name="Anthus australis",
        taxonomy_group="Pipits and Wagtails",
    )
    w.commit()
    out = whoosh_species_suggestions(ix, "aus tree", min_query_len=3)
    assert "Brown Treecreeper" in out
    assert all(not s.endswith(" (group)") for s in out)


def test_whoosh_species_suggestions_prefers_multi_token_coverage():
    ix = create_in(tempfile.mkdtemp(), species_whoosh_schema())
    w = ix.writer()
    w.add_document(
        common_name="Eastern Yellow Robin",
        scientific_name="Eopsaltria australis",
        taxonomy_group="Australasian Robins",
    )
    w.add_document(
        common_name="Australian Pipit",
        scientific_name="Anthus australis",
        taxonomy_group="Pipits and Wagtails",
    )
    w.commit()
    out = whoosh_species_suggestions(ix, "aus rob", min_query_len=3)
    assert out
    assert out[0] == "Eastern Yellow Robin"


def test_whoosh_species_suggestions_prefers_common_name_token_over_sci_only():
    ix = create_in(tempfile.mkdtemp(), species_whoosh_schema())
    w = ix.writer()
    w.add_document(
        common_name="Eastern Yellow Robin",
        scientific_name="Eopsaltria australis",
        taxonomy_group="Australasian Robins",
    )
    w.add_document(
        common_name="Australian Pipit",
        scientific_name="Anthus australis",
        taxonomy_group="Pipits and Wagtails",
    )
    w.commit()
    out = whoosh_species_suggestions(ix, "austr", min_query_len=3)
    assert out
    assert out[0] == "Australian Pipit"


def test_whoosh_species_suggestions_deprioritizes_spuh_sp_suffix():
    ix = create_in(tempfile.mkdtemp(), species_whoosh_schema())
    w = ix.writer()
    w.add_document(
        common_name="Australian Treecreeper sp.",
        scientific_name="Climacteris sp.",
        taxonomy_group="Australian Treecreepers",
    )
    w.add_document(
        common_name="Brown Treecreeper",
        scientific_name="Climacteris picumnus",
        taxonomy_group="Australian Treecreepers",
    )
    w.commit()
    out = whoosh_species_suggestions(ix, "aus tree", min_query_len=3)
    assert out
    assert out[0] == "Brown Treecreeper"


def test_whoosh_species_suggestions_deprioritizes_trailing_paren_subspecies_form():
    ix = create_in(tempfile.mkdtemp(), species_whoosh_schema())
    w = ix.writer()
    w.add_document(
        common_name="Eastern Yellow Robin (Southeastern)",
        scientific_name="Eopsaltria australis chrysorrhos",
        taxonomy_group="Australasian Robins",
    )
    w.add_document(
        common_name="Eastern Yellow Robin",
        scientific_name="Eopsaltria australis",
        taxonomy_group="Australasian Robins",
    )
    w.commit()
    out = whoosh_species_suggestions(ix, "east yell rob", min_query_len=3)
    assert out
    assert out[0] == "Eastern Yellow Robin"


def test_whoosh_species_suggestions_hyphenated_query_matches_plain_text():
    ix = create_in(tempfile.mkdtemp(), species_whoosh_schema())
    w = ix.writer()
    w.add_document(
        common_name="Noisy Scrub-bird",
        scientific_name="Atrichornis clamosus",
        taxonomy_group="Scrub-birds and Bowerbirds",
    )
    w.commit()
    out_plain = whoosh_species_suggestions(ix, "scrub", min_query_len=3)
    out_hyphen = whoosh_species_suggestions(ix, "scrub-bird", min_query_len=3)
    assert "Noisy Scrub-bird" in out_plain
    assert "Noisy Scrub-bird" in out_hyphen

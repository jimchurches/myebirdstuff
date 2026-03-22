"""
Whoosh-backed species name suggestions for autocomplete-style search (refs #69, #70).

Pure helper: no ipywidgets; notebook/Streamlit wire results to UI.

Indexes store **common_name** and **scientific_name** so queries can match either field
(eBird-like multi-token search).
"""

from __future__ import annotations

import tempfile
from typing import Any, Dict, List, Sequence

from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import Schema, TEXT
from whoosh.index import create_in
from whoosh.qparser import MultifieldParser, OrGroup, QueryParser


def species_whoosh_schema() -> Schema:
    """Schema for species autocomplete (common + scientific names)."""
    ana = StemmingAnalyzer()
    return Schema(
        common_name=TEXT(stored=True, analyzer=ana),
        scientific_name=TEXT(stored=True, analyzer=ana),
    )


def build_ram_species_whoosh_index(
    species_list: Sequence[str],
    name_map: Dict[str, str],
) -> Any:
    """
    Build a small Whoosh index from unique common names and common→scientific map.

    Uses a temporary directory (cleaned up by the OS); fine for Streamlit session use
    per working-set rebuild. Notebook uses a persistent temp dir with the same schema.
    """
    index_dir = tempfile.mkdtemp()
    ix = create_in(index_dir, species_whoosh_schema())
    w = ix.writer()
    for common in species_list:
        sci = str(name_map.get(common, "") or "")
        w.add_document(common_name=common, scientific_name=sci)
    w.commit()
    return ix


def whoosh_common_name_suggestions(
    whoosh_index: Any,
    raw_query: str,
    *,
    field_name: str = "common_name",
    max_options: int = 6,
    min_query_len: int = 3,
) -> List[str]:
    """Return up to *max_options* common-name strings matching *raw_query* (prefix-style per token).

    Uses a single field (default ``common_name``). For indexes with both fields, prefer
    :func:`whoosh_species_suggestions`.

    Empty list when query is too short, parse fails, or there are no hits.
    """
    q = (raw_query or "").strip().lower()
    if len(q) < min_query_len:
        return []
    tokens = q.split()
    if not tokens:
        return []
    with whoosh_index.searcher() as searcher:
        qp = QueryParser(field_name, whoosh_index.schema, group=OrGroup)
        try:
            parsed = qp.parse(" ".join(f"{t}*" for t in tokens))
        except Exception:
            return []
        results = searcher.search(parsed, limit=None)

        def score(r):
            name = r[field_name].lower()
            base = 100 - r.rank
            if name.startswith(tokens[0]):
                base += 50
            return base

        ranked = sorted(results, key=score, reverse=True)
        return [r[field_name] for r in ranked[:max_options]]


def whoosh_species_suggestions(
    whoosh_index: Any,
    raw_query: str,
    *,
    max_options: int = 12,
    min_query_len: int = 3,
) -> List[str]:
    """
    Return common names matching *raw_query* across **common** and **scientific** name fields.

    Token query uses prefix matching per token (``token*``), combined with OR across fields
    via :class:`~whoosh.qparser.MultifieldParser`. Results are ranked to prefer:

    - stronger Whoosh score
    - common name starting with the first token
    - shorter common names (slight tie-break)
    """
    q = (raw_query or "").strip().lower()
    if len(q) < min_query_len:
        return []
    tokens = q.split()
    if not tokens:
        return []
    fields = ["common_name", "scientific_name"]
    with whoosh_index.searcher() as searcher:
        mp = MultifieldParser(fields, whoosh_index.schema, group=OrGroup)
        try:
            parsed = mp.parse(" ".join(f"{t}*" for t in tokens))
        except Exception:
            return []
        results = searcher.search(parsed, limit=None)

        def rank_key(r):
            common = (r["common_name"] or "").lower()
            sci = (r.get("scientific_name") or "").lower()
            # Base: Whoosh relevance (higher is better for BM25F default scoring)
            base = getattr(r, "score", None)
            if base is None:
                base = 100.0 - float(r.rank)
            else:
                base = float(base)
            if common.startswith(tokens[0]):
                base += 50.0
            elif sci.startswith(tokens[0]) or any(
                sci.startswith(t) or f" {t}" in sci for t in tokens
            ):
                base += 35.0
            # Prefer shorter display names when scores tie
            base -= len(common) * 0.001
            return base

        ranked = sorted(results, key=rank_key, reverse=True)
        out: List[str] = []
        seen = set()
        for r in ranked:
            cn = r["common_name"]
            if cn and cn not in seen:
                seen.add(cn)
                out.append(cn)
            if len(out) >= max_options:
                break
        return out

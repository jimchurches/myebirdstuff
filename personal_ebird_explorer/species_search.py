"""
Whoosh-backed species name suggestions for autocomplete-style search (refs #69).

Pure helper: no ipywidgets; notebook/Streamlit wire results to UI.
"""

from __future__ import annotations

from typing import Any, List

from whoosh.qparser import OrGroup, QueryParser


def whoosh_common_name_suggestions(
    whoosh_index: Any,
    raw_query: str,
    *,
    field_name: str = "common_name",
    max_options: int = 6,
    min_query_len: int = 3,
) -> List[str]:
    """Return up to *max_options* common-name strings matching *raw_query* (prefix-style per token).

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

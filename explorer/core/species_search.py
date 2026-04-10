"""
Whoosh-backed species name suggestions for the map species picker (autocomplete-style).

Pure helper with no UI imports: the app feeds suggestions into Streamlit widgets. Indexes store
**common_name**, **scientific_name**, and per-species **taxonomy_group** tokens so global search can
surface groups the same way as names. **taxonomy_group_key** (ID) scopes constrained search after the
user picks a ``… (group)`` row so suggestions use the same Whoosh token logic as unrestricted search
(refs #73).
"""

from __future__ import annotations

import tempfile
from typing import Any, Dict, List, Sequence

from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import ID, Schema, TEXT
from whoosh.index import create_in
from whoosh.qparser import MultifieldParser, OrGroup, QueryParser
from whoosh.query import And, Every, Term
from whoosh.sorting import FieldFacet

from explorer.core.species_family import build_base_species_to_family_map
from explorer.core.species_logic import base_species_name

GROUP_ROW_SUFFIX = " (group)"

# Bump when the RAM index schema or document shape changes (Streamlit map sidebar).
SPECIES_WHOOSH_INDEX_VERSION = 2


def species_whoosh_schema() -> Schema:
    """Schema for species autocomplete (common + scientific + group tokens) and group picker rows."""
    ana = StemmingAnalyzer()
    return Schema(
        common_name=TEXT(stored=True, analyzer=ana),
        scientific_name=TEXT(stored=True, analyzer=ana),
        # Indexed group label on **species** rows for global multifield search; same on group rows.
        taxonomy_group=TEXT(stored=True, analyzer=ana),
        # Exact eBird species-group label for post-pick filtering (ID = single token, no stemming).
        taxonomy_group_key=ID(stored=True),
        kind=ID(stored=True),
    )


def taxonomy_group_names_in_working_set(
    species_list: Sequence[str],
    name_map: Dict[str, str],
    taxonomy_locale: str,
) -> List[str]:
    """Distinct eBird species-group names that have at least one species in *species_list*.

    Uses the same base-species → group mapping as Rankings **Families**. Returns sorted
    display names (excludes *Unmapped*). Empty when taxonomy cannot be loaded.
    """
    base_to_f = build_base_species_to_family_map(taxonomy_locale)
    if not base_to_f:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for common in species_list:
        sci = str(name_map.get(common, "") or "")
        base = base_species_name(sci)
        if not base:
            continue
        g = base_to_f.get(base)
        if not g or str(g).strip() == "Unmapped":
            continue
        gn = str(g).strip()
        if gn not in seen:
            seen.add(gn)
            out.append(gn)
    out.sort(key=str.casefold)
    return out


def species_common_names_in_group(
    species_list: Sequence[str],
    name_map: Dict[str, str],
    taxonomy_locale: str,
    group_name: str,
) -> List[str]:
    """Common names in *species_list* whose taxonomy group equals *group_name*."""
    base_to_f = build_base_species_to_family_map(taxonomy_locale)
    if not base_to_f:
        return []
    want = str(group_name).strip()
    out: list[str] = []
    for common in species_list:
        sci = str(name_map.get(common, "") or "")
        base = base_species_name(sci)
        if not base:
            continue
        g = base_to_f.get(base)
        if g and str(g).strip() == want:
            out.append(common)
    out.sort(key=str.casefold)
    return out


def _common_to_taxonomy_group_key(
    species_list: Sequence[str],
    name_map: Dict[str, str],
    taxonomy_locale: str,
) -> Dict[str, str]:
    """Map common name → eBird species-group label (empty string if unmapped)."""
    base_to_f = build_base_species_to_family_map(taxonomy_locale)
    out: Dict[str, str] = {}
    if not base_to_f:
        return {str(c).strip(): "" for c in species_list}
    for common in species_list:
        cn = str(common).strip()
        sci = str(name_map.get(cn, "") or "")
        base = base_species_name(sci)
        if not base:
            out[cn] = ""
            continue
        g = base_to_f.get(base)
        if not g or str(g).strip() == "Unmapped":
            out[cn] = ""
        else:
            out[cn] = str(g).strip()
    return out


def build_ram_species_whoosh_index(
    species_list: Sequence[str],
    name_map: Dict[str, str],
    *,
    taxonomy_group_names: Sequence[str] | None = None,
    taxonomy_locale: str | None = None,
) -> Any:
    """
    Build a small Whoosh index from unique common names and common→scientific map.

    When *taxonomy_locale* is set, each species row stores its eBird species-group label on
    **taxonomy_group** / **taxonomy_group_key** so global search can match group words and
    constrained search can filter with Whoosh (refs #73).

    When *taxonomy_group_names* is non-empty, each label is indexed as a synthetic row
    ``"{label} (group)"`` so it appears in the same type-ahead as species.

    Uses a temporary directory (cleaned up by the OS); fine for Streamlit session use
    per working-set rebuild. Notebook uses a persistent temp dir with the same schema.
    """
    index_dir = tempfile.mkdtemp()
    ix = create_in(index_dir, species_whoosh_schema())
    w = ix.writer()
    loc = (taxonomy_locale or "").strip()
    common_to_grp: Dict[str, str] = (
        _common_to_taxonomy_group_key(species_list, name_map, loc) if loc else {}
    )
    for common in species_list:
        sci = str(name_map.get(common, "") or "")
        gkey = common_to_grp.get(str(common).strip(), "") if loc else ""
        w.add_document(
            common_name=common,
            scientific_name=sci,
            taxonomy_group=gkey,
            taxonomy_group_key=gkey,
            kind="species",
        )
    for g in taxonomy_group_names or ():
        label = str(g).strip()
        if not label:
            continue
        display = f"{label}{GROUP_ROW_SUFFIX}"
        w.add_document(
            common_name=display,
            scientific_name=label,
            taxonomy_group=label,
            taxonomy_group_key=label,
            kind="group",
        )
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


def normalize_query_for_group_filtered_mode(
    raw_query: str,
    selected_group_label: str,
    *,
    group_row_suffix: str = GROUP_ROW_SUFFIX,
) -> str:
    """Map searchbox text to the query used for in-group species suggestions (refs #73 Prototype 2).

    After the user picks a taxonomy group, the widget often keeps the submitted row
    ``"{label} (group)"`` in the field. That string must not be used as a filter substring or
    no species names match — treat it (and a bare *selected_group_label* match) as **no** filter
    so the dropdown can show the alphabetical species list.
    """
    want = (selected_group_label or "").strip()
    if not want:
        return (raw_query or "").strip()
    t = (raw_query or "").strip()
    if not t:
        return ""
    if t.casefold() == want.casefold():
        return ""
    if t.endswith(group_row_suffix):
        base = t[: -len(group_row_suffix)].strip()
        if base.casefold() == want.casefold():
            return ""
    return t


def species_in_group_search_suggestions(
    species_common_names: Sequence[str],
    raw_query: str,
    *,
    max_options: int = 12,
) -> List[str]:
    """Filter *species_common_names* for Prototype 2 group-filtered search (refs #73).

    Sorted alphabetically. Empty query returns the first *max_options* names so the dropdown is
    usable without typing. Non-empty query keeps names whose common name contains the query
    (case-insensitive).
    """
    names = sorted({str(x).strip() for x in species_common_names if str(x).strip()}, key=str.casefold)
    q = (raw_query or "").strip().lower()
    if not q:
        return names[:max_options]
    matched = [n for n in names if q in n.lower()]
    return matched[:max_options]


def whoosh_species_suggestions(
    whoosh_index: Any,
    raw_query: str,
    *,
    max_options: int = 12,
    min_query_len: int = 3,
    restrict_taxonomy_group: str | None = None,
) -> List[str]:
    """
    Return common names matching *raw_query* across **common** and **scientific** name fields.

    Global mode also searches **taxonomy_group** so tokens from the eBird species-group label
    match species rows (and the synthetic ``… (group)`` row) in one pass.

    When *restrict_taxonomy_group* is set (after the user picks a group row), only **species**
    documents in that group are considered; the same token/prefix rules apply to common and
    scientific names. Short queries inside a group use ``min_query_len`` of 1 so typing can
    narrow without the global 3-character gate.

    Token query uses prefix matching per token (``token*``), combined with OR across fields
    via :class:`~whoosh.qparser.MultifieldParser`. Results are ranked to prefer:

    - stronger Whoosh score
    - common name starting with the first token
    - shorter common names (slight tie-break)
    """
    rg = str(restrict_taxonomy_group or "").strip()
    if rg:
        raw_query = normalize_query_for_group_filtered_mode(raw_query, rg)
        eff_min = 1
    else:
        eff_min = min_query_len

    q = (raw_query or "").strip().lower()
    if rg:
        species_filter = And([Term("kind", "species"), Term("taxonomy_group_key", rg)])
        with whoosh_index.searcher() as searcher:
            if not q:
                try:
                    q_all = And([Every(), species_filter])
                    results = searcher.search(
                        q_all,
                        limit=max_options,
                        sortedby=FieldFacet("common_name"),
                    )
                except Exception:
                    return []
                return [r["common_name"] for r in results if r.get("common_name")]

            if len(q) < eff_min:
                return []
            tokens = q.split()
            if not tokens:
                return []
            mp = MultifieldParser(
                ["common_name", "scientific_name"],
                whoosh_index.schema,
                group=OrGroup,
            )
            try:
                parsed = mp.parse(" ".join(f"{t}*" for t in tokens))
            except Exception:
                return []
            try:
                combined = And([parsed, species_filter])
                results = searcher.search(combined, limit=None)
            except Exception:
                return []

            def rank_key(r):
                common = (r["common_name"] or "").lower()
                sci = (r.get("scientific_name") or "").lower()
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
                base -= len(common) * 0.001
                return base

            ranked = sorted(results, key=rank_key, reverse=True)
            out: List[str] = []
            seen: set[str] = set()
            for r in ranked:
                cn = r["common_name"]
                if cn and cn not in seen:
                    seen.add(cn)
                    out.append(cn)
                if len(out) >= max_options:
                    break
            return out

    # --- global (unrestricted) ---
    if len(q) < eff_min:
        return []
    tokens = q.split()
    if not tokens:
        return []
    fields = ["common_name", "scientific_name", "taxonomy_group"]
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
            kind = (r.get("kind") or "species").strip()
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
            # Slight preference for species rows over taxonomy-group rows when scores are close
            if kind == "group":
                base -= 1.5
            # Prefer shorter display names when scores tie
            base -= len(common) * 0.001
            return base

        ranked = sorted(results, key=rank_key, reverse=True)
        out2: List[str] = []
        seen2: set[str] = set()
        for r in ranked:
            cn = r["common_name"]
            if cn and cn not in seen2:
                seen2.add(cn)
                out2.append(cn)
            if len(out2) >= max_options:
                break
        return out2

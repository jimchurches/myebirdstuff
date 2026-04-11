"""Whoosh-backed species suggestions for the map species picker (autocomplete-style).

Pure helper with no UI imports: the app feeds suggestions into Streamlit widgets. Indexes store
**common_name**, **scientific_name**, and derived per-species **taxonomy_group** text so global
search can behave as a weighted helper (refs #73).
"""

from __future__ import annotations

import re
import tempfile
from typing import Any, Dict, List, Sequence

from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import Schema, TEXT
from whoosh.index import create_in
from whoosh.qparser import MultifieldParser, OrGroup

from explorer.core.species_family import build_base_species_to_family_map
from explorer.core.species_logic import base_species_name

# Bump when the RAM index schema or document shape changes (Streamlit map sidebar).
SPECIES_WHOOSH_INDEX_VERSION = 3

# --- Map species suggestion ranking (``whoosh_species_suggestions``) ---
# Whoosh returns a BM25-ish *base* score per document. We then add hand-tuned bonuses so behavior
# matches “helper” expectations: prefer multi-token coverage, then visible common-name matches, then
# scientific / taxonomy-group hints. Rough magnitudes (same unit, summed):
#   base score        — from Whoosh (field weights + term frequency; not a fixed scale).
#   coverage          — reward rows that match more query tokens anywhere (+/- below).
#   common name       — small extra when a token hits **common_name** (user-visible) vs only sci/group.
#   field hints       — starts-with / substring boosts for common, sci, taxonomy_group.
#   length            — tiny tie-break (shorter common name).
#   spuh-style name   — penalty when common name looks like ``… sp.`` / ``… spp.`` (still shown).
#   trailing (…)      — subtle penalty for ``Name (Qualifier)`` (subspecies / regional eBird forms)
#                       so nominate ``Name`` ranks slightly ahead when both match the same query.
# Tune constants below to shift behavior without changing query logic; add tests when fixing a
# specific ranking regression.
RANK_COVERAGE_PER_MATCHED_TOKEN = 20.0
RANK_COVERAGE_PER_MISSING_TOKEN = 18.0
RANK_COMMON_STARTSWITH_FIRST_TOKEN = 30.0
RANK_SCI_PREFIX_OR_SUBTOKEN = 22.0
# Slightly lower than common-name substring bonus so “Australian …” in the visible name wins over
# “Australasian …” in taxonomy_group alone for prefixes like ``austr``.
RANK_GROUP_STARTSWITH_FIRST_TOKEN = 10.0
RANK_GROUP_ANY_TOKEN_SUBSTRING = 8.0
# Prefer matches users see in the picker label (mitigates e.g. *australis* ranking without “Australian” in common).
RANK_COMMON_PER_TOKEN_SUBSTRING = 18.0
RANK_LENGTH_TIEBREAK_PER_CHAR = 0.001
# Deprioritize eBird-style species spuhs in the picker; does not remove them from results.
RANK_SPUH_STYLE_COMMON_NAME_PENALTY = 52.0
# Subtle vs spuh: nominate vs ``Eastern Yellow Robin (Southeastern)`` when both hit the same tokens.
RANK_TRAILING_PAREN_QUALIFIER_PENALTY = 10.0


def species_whoosh_schema() -> Schema:
    """Schema for weighted species autocomplete (common + scientific + taxonomy-group)."""
    ana = StemmingAnalyzer()
    return Schema(
        common_name=TEXT(stored=True, analyzer=ana),
        scientific_name=TEXT(stored=True, analyzer=ana),
        taxonomy_group=TEXT(stored=True, analyzer=ana),
    )


def _common_name_is_species_spuh_style(common: str) -> bool:
    """True for typical eBird species-level spuh labels (``… sp.``, ``… spp.``)."""
    c = (common or "").strip().lower()
    return c.endswith(" sp.") or c.endswith(" spp.")


def _common_name_has_trailing_parenthetical_qualifier(common: str) -> bool:
    """True for common names ending with a parenthetical qualifier (subspecies, regional, etc.)."""
    c = (common or "").strip()
    if not c or "(" not in c:
        return False
    return bool(re.search(r".+\([^)]+\)\s*$", c))


def _query_tokens(raw_query: str) -> List[str]:
    """Normalize user query into prefix-search tokens (hyphen-safe)."""
    q = (raw_query or "").strip().lower()
    if not q:
        return []
    # Treat punctuation (e.g. scrub-bird) as separators, not query operators.
    return [t for t in re.findall(r"[a-z0-9]+", q) if t]


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
    taxonomy_locale: str | None = None,
) -> Any:
    """
    Build a small Whoosh index from unique common names and common→scientific map.

    When *taxonomy_locale* is set, each species row stores its eBird species-group label on
    **taxonomy_group** so global search can give helper-style weight to family/group words.

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
        )
    w.commit()
    return ix


def whoosh_species_suggestions(
    whoosh_index: Any,
    raw_query: str,
    *,
    max_options: int = 12,
    min_query_len: int = 3,
) -> List[str]:
    """
    Return common names matching *raw_query* across **common** and **scientific** name fields.

    Also searches **taxonomy_group** so family/group terms act as a weighted helper for species
    suggestions in a single control.

    Token query uses prefix matching per token (``token*``), combined with OR across fields
    via :class:`~whoosh.qparser.MultifieldParser`. Ranking is documented in module constants
    ``RANK_*`` (see :mod:`explorer.core.species_search`): Whoosh base score plus coverage,
    a small **common-name** preference, then scientific/taxonomy-group hints and a length tie-break.

    **Reasoning about behavior:** compare relative constant sizes — e.g. raising
    ``RANK_COMMON_PER_TOKEN_SUBSTRING`` pulls results whose **display name** contains query
    fragments ahead of rows that only match *Eopsaltria australis*-style scientific names.
    """
    q = (raw_query or "").strip().lower()
    if len(q) < min_query_len:
        return []
    tokens = _query_tokens(q)
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
            grp = (r.get("taxonomy_group") or "").lower()
            combined = f"{common} {sci} {grp}"
            # Base: Whoosh relevance (higher is better for BM25F default scoring)
            base = getattr(r, "score", None)
            if base is None:
                base = 100.0 - float(r.rank)
            else:
                base = float(base)
            matched_tokens = sum(1 for t in tokens if t in combined)
            # Prefer suggestions that satisfy more typed tokens, not just the first token.
            base += matched_tokens * RANK_COVERAGE_PER_MATCHED_TOKEN
            base -= (len(tokens) - matched_tokens) * RANK_COVERAGE_PER_MISSING_TOKEN
            common_token_hits = sum(1 for t in tokens if t in common)
            base += common_token_hits * RANK_COMMON_PER_TOKEN_SUBSTRING
            if common.startswith(tokens[0]):
                base += RANK_COMMON_STARTSWITH_FIRST_TOKEN
            elif sci.startswith(tokens[0]) or any(
                sci.startswith(t) or f" {t}" in sci for t in tokens
            ):
                base += RANK_SCI_PREFIX_OR_SUBTOKEN
            # Family/group is helper intent: boost if query tokens clearly match taxonomy group text.
            if grp.startswith(tokens[0]):
                base += RANK_GROUP_STARTSWITH_FIRST_TOKEN
            if any(t in grp for t in tokens):
                base += RANK_GROUP_ANY_TOKEN_SUBSTRING
            if _common_name_is_species_spuh_style(r["common_name"]):
                base -= RANK_SPUH_STYLE_COMMON_NAME_PENALTY
            if _common_name_has_trailing_parenthetical_qualifier(r["common_name"]):
                base -= RANK_TRAILING_PAREN_QUALIFIER_PENALTY
            # Prefer shorter display names when scores tie
            base -= len(common) * RANK_LENGTH_TIEBREAK_PER_CHAR
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

"""Shared eBird species page URL resolution for map banners."""

from __future__ import annotations

from collections.abc import Callable

from explorer.core.family_map_compute import species_url_for_base_species
from explorer.core.settings_schema_defaults import TAXONOMY_LOCALE_DEFAULT
from explorer.core.taxonomy_bundle import load_taxonomy_bundle, taxonomy_locale_key


def species_banner_url(
    *,
    base_species: str | None,
    taxonomy_locale: str,
    display_name: str,
    species_url_fn: Callable[[str], str | None],
) -> str | None:
    """Resolve a map banner link: base scientific name → ``species_code`` → URL.

    Uses taxonomy rows for the given locale; falls back to *species_url_fn* with
    *display_name* when base → code lookup fails (same rules as map popups).
    """
    base = (base_species or "").strip()
    if not base:
        return None
    tax_loc = taxonomy_locale_key(taxonomy_locale) or TAXONOMY_LOCALE_DEFAULT
    tax_rows = load_taxonomy_bundle(tax_loc).species_rows
    return species_url_for_base_species(
        base,
        tax_rows,
        fallback_fn=species_url_fn,
        fallback_common_name=(display_name or "").strip() or None,
    )

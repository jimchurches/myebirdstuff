"""Structured family-map popup payloads for the Leaflet component.

Parallels :func:`~explorer.core.family_map_compute.format_family_location_popup_html`
without pre-rendered HTML per pin.
"""

from __future__ import annotations

from typing import Any

from explorer.core.family_map_compute import FamilyLocationPin
from explorer.presentation.map_renderer import esc_text


def family_popup_v1_payload(
    pin: FamilyLocationPin,
    *,
    species_url_by_common: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Location heading + species lines for ``family_popup_v1`` in GeoJSON properties."""
    url_map = species_url_by_common or {}
    lines: list[dict[str, str]] = []
    for name in pin.common_name_lines:
        u = url_map.get(name) or url_map.get(name.strip())
        href = ""
        if u and str(u).strip():
            href = str(u).strip()
        lines.append({"name": esc_text(name), "species_href": href})
    return {"v": 1, "species_lines": lines}

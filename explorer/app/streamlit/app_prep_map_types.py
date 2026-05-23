"""Shared types for map prep / Leaflet payload assembly (R13)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LeafletMapPrepBundle:
    """Outputs from per-mode Leaflet GeoJSON prep (one active mode per run)."""

    use_all_locations_leaflet: bool = False
    use_lifer_leaflet: bool = False
    use_species_leaflet: bool = False
    use_family_leaflet: bool = False
    leaflet_revision: str | None = None
    leaflet_geojson: dict[str, Any] | None = None
    leaflet_cluster_opts: dict[str, Any] | None = None
    leaflet_circle_style: dict[str, Any] = field(default_factory=dict)
    leaflet_cluster_icon_style: dict[str, Any] = field(default_factory=dict)
    leaflet_viewport: dict[str, Any] | None = None
    all_locations_leaflet_banner_html: str = ""
    all_locations_leaflet_legend_html: str = ""
    result_warning: str | None = None

    def has_embeddable_leaflet(self) -> bool:
        return bool(
            (
                self.use_all_locations_leaflet
                or self.use_lifer_leaflet
                or self.use_species_leaflet
                or self.use_family_leaflet
            )
            and self.leaflet_revision
            and self.leaflet_geojson is not None
            and self.leaflet_cluster_opts is not None
            and self.leaflet_circle_style is not None
        )

    def embed_kind(self) -> str:
        if self.use_lifer_leaflet:
            return "lifer_leaflet"
        if self.use_species_leaflet:
            return "species_leaflet"
        if self.use_family_leaflet:
            return "family_leaflet"
        return "all_locations_leaflet"

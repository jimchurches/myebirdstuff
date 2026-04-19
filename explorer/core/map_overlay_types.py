"""Shared types for the species / lifer Folium overlay pipeline.

Used by :mod:`explorer.core.map_controller` and the split overlay helpers
(:mod:`explorer.core.map_overlay_lifer_map`, :mod:`explorer.core.map_overlay_visit_map`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import folium

SpeciesUrlFn = Optional[Callable[[str], Optional[str]]]
BaseSpeciesFn = Callable[[str], Optional[str]]

VALID_MAP_VIEWS = frozenset({"all", "species", "lifers"})


@dataclass
class MapOverlayResult:
    """Outcome of :func:`~explorer.core.map_controller.build_species_overlay_map`."""

    map: Optional[folium.Map]
    """Folium map when build succeeds; ``None`` when *warning* is set."""

    warning: Optional[str] = None
    """User-facing message (e.g. no sightings for species in current data)."""

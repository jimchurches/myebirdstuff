"""Shared callback types for map GeoJSON builders."""

from __future__ import annotations

from typing import Callable, Optional

SpeciesUrlFn = Optional[Callable[[str], Optional[str]]]
BaseSpeciesFn = Callable[[str], Optional[str]]

VALID_MAP_VIEWS = frozenset({"all", "species", "lifers", "families"})

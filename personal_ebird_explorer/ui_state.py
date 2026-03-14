"""
Lightweight structured application state for Personal eBird Explorer.

Replaces scattered notebook globals with a single inspectable object.
Widget instances and read-only data (DataFrames, config) stay in the
notebook — this module holds only shared mutable state that callbacks
read and write at runtime.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExplorerState:
    """Core mutable application state shared across notebook callbacks.

    Fields
    ------
    selected_species_scientific : str
        Scientific name of the currently selected species (empty = all species).
    selected_species_common : str
        Common name of the currently selected species (empty = all species).
    species_map : Any
        The current ``folium.Map`` instance displayed in the notebook.
        Typed as ``Any`` to avoid a hard dependency on folium at import time.

    Re-entry guards
    ---------------
    updating_suggestions : bool
        True while ``update_suggestions`` is running; prevents
        ``on_species_selected`` from acting on intermediate dropdown changes.
    skip_next_suggestion_update : bool
        When True, the next ``update_suggestions`` call returns immediately
        and resets the flag. Used after programmatic ``search_box.value``
        changes that should not trigger a search.
    suppress_toggle_redraw : bool
        When True, ``on_toggle_change`` skips its map redraw. Set
        temporarily by ``_clear_to_all_species`` while resetting the
        checkbox value.
    """

    selected_species_scientific: str = ""
    selected_species_common: str = ""
    species_map: Any = None

    updating_suggestions: bool = False
    skip_next_suggestion_update: bool = False
    suppress_toggle_redraw: bool = False

    def clear_selection(self):
        """Reset species selection to the all-species view."""
        self.selected_species_scientific = ""
        self.selected_species_common = ""

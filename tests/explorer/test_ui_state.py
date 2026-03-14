"""Tests for personal_ebird_explorer.ui_state.ExplorerState."""

from personal_ebird_explorer.ui_state import ExplorerState


def test_default_state():
    s = ExplorerState()
    assert s.selected_species_scientific == ""
    assert s.selected_species_common == ""
    assert s.species_map is None
    assert s.updating_suggestions is False
    assert s.skip_next_suggestion_update is False
    assert s.suppress_toggle_redraw is False


def test_clear_selection_resets_species():
    s = ExplorerState(
        selected_species_scientific="anas gracilis",
        selected_species_common="Grey Teal",
    )
    s.clear_selection()
    assert s.selected_species_scientific == ""
    assert s.selected_species_common == ""


def test_clear_selection_does_not_reset_guards_or_map():
    s = ExplorerState(
        selected_species_scientific="anas gracilis",
        selected_species_common="Grey Teal",
        species_map="<fake map>",
        updating_suggestions=True,
        skip_next_suggestion_update=True,
        suppress_toggle_redraw=True,
    )
    s.clear_selection()
    assert s.species_map == "<fake map>"
    assert s.updating_suggestions is True
    assert s.skip_next_suggestion_update is True
    assert s.suppress_toggle_redraw is True


def test_instances_are_independent():
    """Two ExplorerState instances must not share mutable state."""
    s1 = ExplorerState()
    s2 = ExplorerState()
    s1.selected_species_scientific = "corvus coronoides"
    s1.updating_suggestions = True
    assert s2.selected_species_scientific == ""
    assert s2.updating_suggestions is False


def test_guard_flag_round_trip():
    """Re-entry guard flags can be set and cleared as the callbacks would."""
    s = ExplorerState()
    s.updating_suggestions = True
    assert s.updating_suggestions is True
    s.updating_suggestions = False
    assert s.updating_suggestions is False


def test_species_map_accepts_any_object():
    sentinel = object()
    s = ExplorerState(species_map=sentinel)
    assert s.species_map is sentinel

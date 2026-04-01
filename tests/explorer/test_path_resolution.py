"""Tests for explorer.core.path_resolution.find_data_file."""

import os
import pytest
import tempfile

from explorer.core.path_resolution import find_data_file


def test_find_data_file_returns_first_candidate_where_file_exists():
    """First candidate dir that contains the file wins."""
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        # Put file only in second dir
        filename = "data.csv"
        path2 = os.path.join(d2, filename)
        with open(path2, "w") as f:
            f.write("x\n1")
        path, folder = find_data_file(filename, [d1, d2])
        assert path == os.path.normpath(path2)
        assert folder == os.path.normpath(d2)


def test_find_data_file_returns_first_match_when_multiple_have_file():
    """When multiple candidates contain the file, the first in list is returned."""
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        filename = "data.csv"
        for d in (d1, d2):
            with open(os.path.join(d, filename), "w") as f:
                f.write("x\n1")
        path, folder = find_data_file(filename, [d1, d2])
        assert path == os.path.normpath(os.path.join(d1, filename))
        assert folder == os.path.normpath(d1)


def test_find_data_file_returns_none_when_file_not_in_any_candidate():
    """When no candidate contains the file, returns (None, None)."""
    with tempfile.TemporaryDirectory() as d1:
        # Dir exists but file doesn't
        path, folder = find_data_file("nonexistent.csv", [d1])
        assert path is None
        assert folder is None


def test_find_data_file_empty_candidate_list_returns_none():
    """Empty list of candidates returns (None, None)."""
    path, folder = find_data_file("anything.csv", [])
    assert path is None
    assert folder is None


def test_find_data_file_normalizes_paths():
    """Returned path and folder are normalized (e.g. resolve ..)."""
    with tempfile.TemporaryDirectory() as parent:
        child = os.path.join(parent, "subdir")
        os.makedirs(child, exist_ok=True)
        filename = "data.csv"
        with open(os.path.join(child, filename), "w") as f:
            f.write("x\n1")
        # Use a path with .. so normpath does something
        candidate_with_dotdot = os.path.join(parent, "subdir", "..", "subdir")
        path, folder = find_data_file(filename, [candidate_with_dotdot])
        assert path == os.path.normpath(os.path.join(child, filename))
        assert folder == os.path.normpath(child)

import os
import sys


def _add_repo_root_to_path():
    """Ensure the repo root is on sys.path so tests can import notebooks.*"""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    # tests/ → repo root
    repo_root = os.path.dirname(repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_add_repo_root_to_path()


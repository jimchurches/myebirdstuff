"""
Shared CSV path resolution for the Personal eBird Explorer (notebook + Streamlit).

Introduced for the Streamlit UI prototype; migration plan: issue #70
(https://github.com/jimchurches/myebirdstuff/issues/70).

Search order matches the historical notebook behaviour:

1. Optional hardcoded folder (``DATA_FOLDER_HARDCODED`` or ``STREAMLIT_EBIRD_DATA_FOLDER``)
2. ``scripts/config_secret.py`` → ``DATA_FOLDER``
3. ``scripts/config_template.py`` → ``DATA_FOLDER``
4. *anchor* directory (notebook folder or ``streamlit_app/``)

Streamlit Cloud typically has no local CSV; use **file upload** or set secrets (see ``streamlit_app`` README).
"""

from __future__ import annotations

import importlib.util
import os
from typing import List, Optional, Tuple

from personal_ebird_explorer.path_resolution import find_data_file


def data_folder_from_config_file(config_path: str) -> Optional[str]:
    """Load a one-off config module and return ``DATA_FOLDER`` if set and non-empty."""
    if not os.path.exists(config_path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("explorer_config_module", config_path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        folder = getattr(mod, "DATA_FOLDER", None)
        if folder and str(folder).strip():
            return os.path.normpath(str(folder).strip())
    except Exception:
        return None
    return None


def build_explorer_candidate_dirs(
    *,
    repo_root: str,
    anchor_dir: str,
    data_folder_hardcoded: Optional[str] = None,
    anchor_label: str = "notebook folder",
) -> Tuple[List[str], List[str]]:
    """
    Build parallel lists: candidate folders and short source labels (for UI / debugging).

    *anchor_dir* is the directory treated as “drop your CSV here” (notebook dir or Streamlit app dir).
    *anchor_label* is the human-readable name for that slot (e.g. ``notebook folder``, ``streamlit app folder``).
    """
    folders: List[str] = []
    sources: List[str] = []

    if data_folder_hardcoded and str(data_folder_hardcoded).strip():
        folders.append(os.path.normpath(str(data_folder_hardcoded).strip()))
        sources.append("hardcoded")

    scripts_dir = os.path.join(repo_root, "scripts")
    for label, name in (
        ("config_secret", "config_secret.py"),
        ("config_template", "config_template.py"),
    ):
        cfg_path = os.path.join(scripts_dir, name)
        dfolder = data_folder_from_config_file(cfg_path)
        if dfolder:
            folders.append(dfolder)
            sources.append(label)

    folders.append(os.path.normpath(anchor_dir))
    sources.append(anchor_label)

    return folders, sources


def resolve_ebird_data_file(
    filename: str,
    candidate_folders: List[str],
    path_sources: List[str],
) -> Tuple[str, str, str]:
    """
    Find *filename* under the first matching candidate folder.

    Returns ``(file_path, data_folder, source_label)``.

    Raises ``FileNotFoundError`` with guidance if the file is missing.
    """
    file_path, data_folder = find_data_file(filename, candidate_folders)
    if not file_path or not data_folder:
        raise FileNotFoundError(
            f"Data file not found: {filename}\n\n"
            f"Tried locations:\n  " + "\n  ".join(candidate_folders) + "\n\n"
            "Options:\n"
            "  1. Set DATA_FOLDER_HARDCODED (notebook) or STREAMLIT_EBIRD_DATA_FOLDER (Streamlit)\n"
            "  2. Create scripts/config_secret.py with DATA_FOLDER = \"your/path\"\n"
            "  3. Put the CSV in the notebook or streamlit_app folder, or use Streamlit file upload\n"
            "  4. On Binder: upload your .csv to the notebook folder\n\n"
            f"Expected filename: {filename}"
        )

    source = path_sources[-1] if path_sources else "unknown"
    for i, cand in enumerate(candidate_folders):
        if os.path.normpath(cand) == os.path.normpath(data_folder):
            source = path_sources[i] if i < len(path_sources) else source
            break
    return file_path, data_folder, source


def settings_yaml_path_for_source(repo_root: str, source_label: str) -> Optional[str]:
    """Primary settings store path for a resolved config source (or ``None``)."""
    scripts_dir = os.path.join(repo_root, "scripts")
    src = (source_label or "").strip().lower()
    if src == "config_secret":
        return os.path.join(scripts_dir, "config_secret.py")
    if src == "config_template":
        return os.path.join(scripts_dir, "config_template.py")
    return None

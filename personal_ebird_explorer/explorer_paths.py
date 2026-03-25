"""
CSV path resolution for the Personal eBird Explorer (Streamlit app).

Migration plan: issue #70 (https://github.com/jimchurches/myebirdstuff/issues/70).

Search order (first folder that contains the filename wins):

1. ``scripts/config_secret.py`` → ``DATA_FOLDER`` (if set)
2. ``scripts/config.py`` → ``DATA_FOLDER`` (if set)
3. **Working directory** — ``cwd`` argument, default ``os.getcwd()`` (where the process started)

``scripts/config_template.py`` is **never** read by this module — it exists only as a **copy-paste template** into ``config_secret.py`` or ``config.py``.

No env-based data folder: use config files, CWD, or Streamlit **file upload**. Streamlit Cloud: upload on the landing page.
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
    cwd: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """Return ``(folders, source_labels)`` for :func:`resolve_ebird_data_file`."""
    folders: List[str] = []
    sources: List[str] = []
    scripts_dir = os.path.join(repo_root, "scripts")

    for label, name in (
        ("config_secret", "config_secret.py"),
        ("config", "config.py"),
    ):
        cfg_path = os.path.join(scripts_dir, name)
        dfolder = data_folder_from_config_file(cfg_path)
        if dfolder:
            folders.append(dfolder)
            sources.append(label)

    cwd_norm = os.path.normpath(cwd or os.getcwd())
    folders.append(cwd_norm)
    sources.append("cwd")

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
            "  • Set DATA_FOLDER in scripts/config_secret.py or scripts/config.py (create from config_template.py; the template is not loaded at runtime).\n"
            "  • Put the CSV in the process working directory, or use the Streamlit landing-page file upload.\n\n"
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
    if src == "config":
        return os.path.join(scripts_dir, "config.py")
    return None

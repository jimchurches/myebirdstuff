"""
CSV path resolution for the Personal eBird Explorer (Streamlit app).

Migration plan: issue #70 (https://github.com/jimchurches/myebirdstuff/issues/70).

Search order (first folder that contains the filename wins):

1. ``config/config_secret.yaml`` → ``data_folder`` (if set)
2. ``config/config.yaml`` → ``data_folder`` (if set)
3. **Working directory** — ``cwd`` argument, default ``os.getcwd()`` (where the process started)

``config/config_template.yaml`` is a tracked template; secret configs are gitignored.

No env-based data folder: use config files, CWD, or Streamlit **file upload**. Streamlit Cloud: upload on the landing page.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from explorer.core.path_resolution import find_data_file


def _safe_load_yaml_mapping(path: str) -> dict:
    """Best-effort YAML mapping loader (returns {} on any failure)."""
    if not (path and os.path.exists(path)):
        return {}
    try:
        import yaml
    except Exception:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def data_folder_from_yaml_config(config_path: str) -> Optional[str]:
    """Load ``data_folder`` from a YAML config file."""
    raw = _safe_load_yaml_mapping(config_path)
    folder = raw.get("data_folder", None)
    if folder and str(folder).strip():
        return os.path.normpath(str(folder).strip())
    return None


def build_explorer_candidate_dirs(
    *,
    repo_root: str,
    cwd: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """Return ``(folders, source_labels)`` for :func:`resolve_ebird_data_file`."""
    folders: List[str] = []
    sources: List[str] = []
    config_dir = os.path.join(repo_root, "config")

    for label, name in (
        ("config_secret", "config_secret.yaml"),
        ("config", "config.yaml"),
    ):
        cfg_path = os.path.join(config_dir, name)
        dfolder = data_folder_from_yaml_config(cfg_path)
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
            "  • Set data_folder in config/config_secret.yaml or config/config.yaml (create from config/config_template.yaml).\n"
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
    """Active config path for a resolved source (or ``None``)."""
    src = (source_label or "").strip().lower()
    config_dir = os.path.join(repo_root, "config")
    if src == "config_secret":
        return os.path.join(config_dir, "config_secret.yaml")
    if src == "config":
        return os.path.join(config_dir, "config.yaml")
    return None

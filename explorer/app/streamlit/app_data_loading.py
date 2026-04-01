"""Load the eBird export DataFrame from disk or upload (refs #98)."""

from __future__ import annotations

import io
import os
from typing import Any

import pandas as pd
import streamlit as st

from explorer.core.data_loader import load_dataset
from explorer.core.explorer_paths import build_explorer_candidate_dirs, resolve_ebird_data_file

from explorer.app.streamlit.app_constants import DEFAULT_EBIRD_FILENAME, REPO_ROOT


def load_dataframe(
    *,
    uploaded: Any | None = None,
    upload_cache: tuple[bytes, str] | None = None,
) -> tuple[pd.DataFrame | None, str | None, str | None, str | None, str | None]:
    """
    Return ``(df, provenance_html, source_label, data_abs_path, data_basename)``.

    *data_abs_path* is set only for on-disk resolution (``None`` for landing / session upload).
    *data_basename* is the CSV file name for display.
    """
    if uploaded is not None:
        try:
            raw = uploaded.getvalue()
            df = load_dataset(io.BytesIO(raw))
            name = uploaded.name
            return df, f"Upload: **{name}**", None, None, name
        except Exception as e:
            st.error(f"Could not load CSV: {e}")
            return None, None, None, None, None

    try:
        folders, sources = build_explorer_candidate_dirs(
            repo_root=REPO_ROOT,
            cwd=os.getcwd(),
        )
        path, _folder, src = resolve_ebird_data_file(DEFAULT_EBIRD_FILENAME, folders, sources)
        df = load_dataset(path)
        label = src.replace("_", " ").title()
        base = os.path.basename(path)
        return df, f"Disk: `{path}` (_{label}_)", src, path, base
    except FileNotFoundError:
        pass

    if upload_cache is not None:
        raw, name = upload_cache
        try:
            df = load_dataset(io.BytesIO(raw))
            return df, f"Upload: **{name}**", None, None, name
        except Exception as e:
            st.error(f"Could not load CSV: {e}")
            return None, None, None, None, None

    return None, None, None, None, None

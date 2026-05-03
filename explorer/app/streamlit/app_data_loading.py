"""Load the eBird export DataFrame from disk or upload (refs #98)."""

from __future__ import annotations

import io
import hashlib
import os
from typing import Any

import pandas as pd
import streamlit as st

from explorer.core.data_loader import load_dataset
from explorer.core.explorer_paths import build_explorer_candidate_dirs, resolve_ebird_data_file

from explorer.app.streamlit.app_constants import DEFAULT_EBIRD_FILENAME, REPO_ROOT
from explorer.app.streamlit.perf_instrumentation import perf_span


@st.cache_data(show_spinner=False)
def _cached_load_dataset_from_disk(path: str, file_sig: tuple[int, int]) -> pd.DataFrame:
    """Disk dataset cache keyed by path + (mtime_ns, size) for fast warm reruns."""
    _ = file_sig
    return load_dataset(path)


@st.cache_data(show_spinner=False)
def _cached_load_dataset_from_bytes(raw: bytes, content_sha256: str) -> pd.DataFrame:
    """Upload/session-bytes dataset cache keyed by content hash."""
    _ = content_sha256
    return load_dataset(io.BytesIO(raw))


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
            with perf_span("dataset.load", extra={"route": "upload_widget"}):
                raw = uploaded.getvalue()
                raw_hash = hashlib.sha256(raw).hexdigest()
                df = _cached_load_dataset_from_bytes(raw, raw_hash)
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
        with perf_span("dataset.load", extra={"route": "disk"}):
            try:
                st_path = os.stat(path)
                file_sig = (int(st_path.st_mtime_ns), int(st_path.st_size))
            except OSError:
                # Test doubles and some virtualized paths may not support ``os.stat``.
                file_sig = (0, 0)
            df = _cached_load_dataset_from_disk(path, file_sig)
        label = src.replace("_", " ").title()
        base = os.path.basename(path)
        return df, f"Disk: `{path}` (_{label}_)", src, path, base
    except FileNotFoundError:
        pass

    if upload_cache is not None:
        raw, name = upload_cache
        try:
            with perf_span("dataset.load", extra={"route": "session_upload_cache"}):
                raw_hash = hashlib.sha256(raw).hexdigest()
                df = _cached_load_dataset_from_bytes(raw, raw_hash)
            return df, f"Upload: **{name}**", None, None, name
        except Exception as e:
            st.error(f"Could not load CSV: {e}")
            return None, None, None, None, None

    return None, None, None, None, None

"""Optional Explorer performance instrumentation (refs #179, Phase 0).

Enable with environment variable ``EXPLORER_PERF=1`` (or ``true`` / ``yes`` / ``on``) or the same
key in Streamlit **Secrets** on Community Cloud. Off by default; no session churn when disabled.

Set ``EXPLORER_PERF_LOG_FILE`` to append each event as JSON Lines to a writable path (same payload
as the sidebar download buffer).
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import streamlit as st

from explorer.app.streamlit.app_constants import (
    EBIRD_DATA_SIG_KEY,
    EXPLORER_MAIN_SCRIPT_RUN_ID_KEY,
    EXPLORER_PERF_CLEAR_BTN_KEY,
    EXPLORER_PERF_DATASET_CTX_KEY,
    EXPLORER_PERF_DOWNLOAD_BTN_KEY,
    EXPLORER_PERF_EVENTS_KEY,
    EXPLORER_PERF_MAX_EVENTS,
)
from explorer.core.repo_git import github_blob_ref_for_readme

PERF_ENV_KEY = "EXPLORER_PERF"
PERF_LOG_ENV_KEY = "EXPLORER_PERF_LOG"
# Append-only JSONL path (same records as sidebar buffer). Reliable for subprocess E2E; empty = off.
PERF_LOG_FILE_ENV_KEY = "EXPLORER_PERF_LOG_FILE"
_LOG = logging.getLogger(__name__)

# Stages compared side-by-side in the sidebar when EXPLORER_PERF=1 (#221 vs Folium).
_MAP_EMBED_COMPARE_STAGES: tuple[str, ...] = (
    "prep.map_iframe_embed",
    "map.experimental.payload",
    "map.experimental.component_embed",
)
_MAP_EMBED_COMPARE_LABELS: dict[str, str] = {
    "prep.map_iframe_embed": "Classic · Folium iframe (st_folium)",
    "map.experimental.payload": "Experimental · GeoJSON + revision (Python)",
    "map.experimental.component_embed": "Experimental · Streamlit component embed",
}


def _secrets_raw(key: str) -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return ""


def explorer_perf_enabled() -> bool:
    raw = _secrets_raw(PERF_ENV_KEY) or str(os.environ.get(PERF_ENV_KEY, "")).strip()
    return raw.lower() in {"1", "true", "yes", "on"}


def explorer_perf_log_json_lines() -> bool:
    raw = _secrets_raw(PERF_LOG_ENV_KEY) or str(os.environ.get(PERF_LOG_ENV_KEY, "")).strip()
    return raw.lower() in {"1", "true", "yes", "on"}


def _secrets_or_env_trim(key: str) -> str:
    return _secrets_raw(key) or str(os.environ.get(key, "")).strip()


def _append_perf_log_file(rec: dict[str, Any]) -> None:
    """When ``EXPLORER_PERF_LOG_FILE`` is set, append one JSON object per line (local / tests)."""
    path = _secrets_or_env_trim(PERF_LOG_FILE_ENV_KEY)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(rec, default=str) + "\n")
    except OSError:
        pass


def _main_run_id() -> int | None:
    try:
        v = st.session_state.get(EXPLORER_MAIN_SCRIPT_RUN_ID_KEY)
        return int(v) if v is not None else None
    except Exception:
        return None


def _session_warm_label() -> str:
    """Rough cold vs warm: first full dashboard run in session is *cold*."""
    rid = _main_run_id()
    if rid is None:
        return "unknown"
    return "cold" if rid <= 1 else "warm"


def perf_dataset_context_dict(df: Any) -> dict[str, Any]:
    """Dataset shape and cardinalities for perf records (#179)."""
    out: dict[str, Any] = {"rows": 0, "cols": 0}
    if df is None:
        return out
    try:
        empty = bool(getattr(df, "empty", True))
        out["rows"] = 0 if empty else int(len(df))
        out["cols"] = 0 if empty else int(len(getattr(df, "columns", [])))
        if empty:
            return out
        cols = set(df.columns)
        if "Common Name" in cols:
            out["unique_species"] = int(df["Common Name"].nunique())
        if "Location ID" in cols:
            out["unique_locations"] = int(df["Location ID"].nunique())
        if "Submission ID" in cols:
            out["unique_checklists"] = int(df["Submission ID"].nunique())
    except Exception as exc:
        out["context_error"] = str(exc)
    return out


def perf_set_dataset_context(df: Any) -> None:
    """Store latest dataset summary on session for merged perf events."""
    if not explorer_perf_enabled():
        return
    st.session_state[EXPLORER_PERF_DATASET_CTX_KEY] = perf_dataset_context_dict(df)


def _trim_events(events: list[dict[str, Any]]) -> None:
    over = len(events) - int(EXPLORER_PERF_MAX_EVENTS)
    if over > 0:
        del events[0:over]


def _append_event(rec: dict[str, Any]) -> None:
    if not explorer_perf_enabled():
        return
    events = st.session_state.get(EXPLORER_PERF_EVENTS_KEY)
    if not isinstance(events, list):
        events = []
    events.append(rec)
    _trim_events(events)
    st.session_state[EXPLORER_PERF_EVENTS_KEY] = events
    _append_perf_log_file(rec)
    if explorer_perf_log_json_lines():
        try:
            _LOG.info(json.dumps(rec, default=str))
        except Exception:
            pass


def _base_record(
    *,
    stage: str,
    elapsed_ms: float,
    run_kind: str,
    fragment: str | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    ds = st.session_state.get(EXPLORER_PERF_DATASET_CTX_KEY)
    if not isinstance(ds, dict):
        ds = {}
    rec: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "elapsed_ms": round(float(elapsed_ms), 3),
        "run_kind": run_kind,
        "fragment": fragment,
        "main_run_id": _main_run_id(),
        "session_warmth": _session_warm_label(),
        "git_ref": github_blob_ref_for_readme(),
        "dataset_sig": st.session_state.get(EBIRD_DATA_SIG_KEY),
        "dataset": dict(ds),
    }
    if extra:
        rec["extra"] = extra
    return rec


@contextmanager
def perf_span(stage: str, *, extra: dict[str, Any] | None = None) -> Iterator[None]:
    """Time a block as a *full_run* span (use inside ``main()`` / prep path)."""
    if not explorer_perf_enabled():
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        _append_event(_base_record(stage=stage, elapsed_ms=elapsed_ms, run_kind="full_run", fragment=None, extra=extra))


@contextmanager
def perf_fragment(fragment_name: str, *, extra: dict[str, Any] | None = None) -> Iterator[None]:
    """Time an entire ``@st.fragment`` body (#179)."""
    if not explorer_perf_enabled():
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        _append_event(
            _base_record(
                stage=f"fragment.{fragment_name}",
                elapsed_ms=elapsed_ms,
                run_kind="fragment",
                fragment=fragment_name,
                extra=extra,
            )
        )


def perf_record_point(stage: str, *, extra: dict[str, Any] | None = None) -> None:
    """Single instant event (elapsed_ms 0)."""
    if not explorer_perf_enabled():
        return
    _append_event(_base_record(stage=stage, elapsed_ms=0.0, run_kind="point", fragment=None, extra=extra))


def perf_events_jsonl() -> str:
    """Buffered events as JSON Lines (may be empty)."""
    events = st.session_state.get(EXPLORER_PERF_EVENTS_KEY)
    if not isinstance(events, list):
        return ""
    lines = []
    for row in events:
        try:
            lines.append(json.dumps(row, default=str))
        except Exception:
            continue
    return "\n".join(lines) + ("\n" if lines else "")


def perf_recent_summary_rows(limit: int = 40) -> list[dict[str, Any]]:
    """Narrow dicts for ``st.dataframe`` (most recent first)."""
    events = st.session_state.get(EXPLORER_PERF_EVENTS_KEY)
    if not isinstance(events, list) or not events:
        return []
    tail = events[-limit:]
    rows: list[dict[str, Any]] = []
    for e in reversed(tail):
        rows.append(
            {
                "stage": e.get("stage"),
                "elapsed_ms": e.get("elapsed_ms"),
                "run_kind": e.get("run_kind"),
                "fragment": e.get("fragment"),
                "main_run_id": e.get("main_run_id"),
                "session_warmth": e.get("session_warmth"),
            }
        )
    return rows


def perf_latest_main_run_map_embed_rows() -> list[dict[str, Any]]:
    """Summarise Folium vs experimental map spans for the latest rerun that recorded either (#221).

    Elapsed times are **Python-side** ``perf_counter`` around Streamlit embed calls, in **script
    order** for one full run — not time-to-visible in the browser.
    """
    events = st.session_state.get(EXPLORER_PERF_EVENTS_KEY)
    if not isinstance(events, list) or not events:
        return []
    want = frozenset(_MAP_EMBED_COMPARE_STAGES)
    latest_rid: Any | None = None
    for e in reversed(events):
        if isinstance(e, dict) and e.get("stage") in want:
            latest_rid = e.get("main_run_id")
            break
    if latest_rid is None:
        return []
    picked: list[dict[str, Any]] = []
    order_index = {s: i for i, s in enumerate(_MAP_EMBED_COMPARE_STAGES)}
    for e in events:
        if not isinstance(e, dict):
            continue
        if e.get("main_run_id") != latest_rid:
            continue
        stg = e.get("stage")
        if stg not in want:
            continue
        extra = e.get("extra") if isinstance(e.get("extra"), dict) else {}
        notes_parts: list[str] = []
        mv = extra.get("map_view_mode")
        if mv is not None:
            notes_parts.append(f"map_view={mv}")
        nf = extra.get("n_features")
        if nf is not None:
            notes_parts.append(f"n_pins={nf}")
        rp = extra.get("revision_prefix")
        if rp:
            notes_parts.append(f"rev={rp}")
        picked.append(
            {
                "_order": order_index.get(str(stg), 99),
                "step": _MAP_EMBED_COMPARE_LABELS.get(str(stg), str(stg)),
                "elapsed_ms": e.get("elapsed_ms"),
                "notes": "; ".join(notes_parts),
            }
        )
    picked.sort(key=lambda r: int(r.get("_order", 99)))
    for r in picked:
        del r["_order"]
    return picked


def render_explorer_perf_sidebar_panel() -> None:
    """Sidebar expander: summary table + JSONL download + clear (only when perf is on)."""
    if not explorer_perf_enabled():
        return
    with st.expander("Performance / debug", expanded=False):
        st.caption(
            "Instrumentation for [issue #179](https://github.com/jimchurches/myebirdstuff/issues/179). "
            "Set `EXPLORER_PERF=1` locally or in Cloud secrets."
        )
        map_cmp = perf_latest_main_run_map_embed_rows()
        st.markdown("**Map embed timings (latest rerun)**")
        if map_cmp:
            st.caption(
                "Python time around each embed, in script order (Folium runs before the experimental "
                "tab on the same rerun). Not browser paint — use DevTools if you care about pixels."
            )
            st.dataframe(map_cmp, hide_index=True, use_container_width=True)
        else:
            st.info(
                "No **map** timings in the buffer yet — only stages like `dataset.load` will appear "
                "until Streamlit finishes a full dashboard run **after** your CSV is loaded.\n\n"
                "**Try:** open the **Map** tab once (classic map must build successfully), set sidebar "
                "**Map view** to **All locations** if you want experimental rows too, then change any "
                "sidebar control (or press **R**) to force a **rerun** and reopen this expander.",
                icon="ℹ️",
            )
        rows = perf_recent_summary_rows(50)
        if rows:
            st.dataframe(rows, hide_index=True, use_container_width=True)
        else:
            st.caption("No events recorded yet in this session.")
        j = perf_events_jsonl()
        st.download_button(
            "Download metrics (JSONL)",
            data=j.encode("utf-8") if j else b"",
            file_name="explorer_perf_events.jsonl",
            mime="application/x-ndjson",
            key=EXPLORER_PERF_DOWNLOAD_BTN_KEY,
            disabled=not bool(j.strip()),
        )
        if st.button("Clear session buffer", key=EXPLORER_PERF_CLEAR_BTN_KEY):
            st.session_state[EXPLORER_PERF_EVENTS_KEY] = []
            st.rerun()

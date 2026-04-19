"""Shared helpers for checklist-style HTML tables (escaping, cells, rows, external links) (refs #117).

Call sites own table structure and classes; helpers standardize *how* plain text and links are escaped
and how common cell styles are expressed.
"""

from __future__ import annotations

import html as html_module
from typing import Any

# Right-aligned numeric / emphasis cells used across rankings-style tables.
METRIC_CELL_STYLE = "text-align:right;font-weight:600;"


def esc_text(value: Any) -> str:
    """Escape plain text for HTML element content (not attribute context)."""
    return html_module.escape(str(value) if value is not None else "", quote=False)


def esc_attr(value: Any) -> str:
    """Escape for HTML attribute values (e.g. ``href``)."""
    return html_module.escape(str(value) if value is not None else "", quote=True)


def tr_row(*cells_html: str) -> str:
    """One ``<tr>`` wrapping already-rendered cell HTML strings."""
    return f"<tr>{''.join(cells_html)}</tr>"


def td_plain(value: Any, *, style: str | None = None) -> str:
    """``<td>`` with escaped plain-text content."""
    inner = esc_text(value)
    if style:
        return f'<td style="{style}">{inner}</td>'
    return f"<td>{inner}</td>"


def td_html(inner_html: str, *, style: str | None = None) -> str:
    """``<td>`` with caller-built inner HTML (caller responsible for escaping)."""
    if style:
        return f'<td style="{style}">{inner_html}</td>'
    return f"<td>{inner_html}</td>"


def th_plain(value: Any, *, style: str | None = None) -> str:
    """``<th>`` with escaped plain-text content."""
    inner = esc_text(value)
    if style:
        return f'<th style="{style}">{inner}</th>'
    return f"<th>{inner}</th>"


def a_external(
    href: str,
    visible_text: Any,
    *,
    rel: str = "noopener noreferrer",
    target: str = "_blank",
) -> str:
    """Standard external link: escaped ``href`` and visible text, ``target`` + ``rel`` on anchor."""
    return (
        f'<a href="{esc_attr(href)}" target="{esc_attr(target)}" rel="{esc_attr(rel)}">'
        f"{esc_text(visible_text)}</a>"
    )

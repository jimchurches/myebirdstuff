"""Parse and compare Personal eBird Explorer release ids (calver + optional same-day suffix). Refs #189."""

from __future__ import annotations

import re
from typing import Optional, Tuple

# First release of a day: YYYY-MM-DD only. Same-day follow-ups: .2, .3, … (never .0 or .1).
_EXPLORER_RELEASE_ID_RE = re.compile(
    r"^v?(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})(?:\.(?P<s>\d+))?$",
    re.IGNORECASE,
)


def normalize_release_tag(raw: str) -> str:
    """Strip surrounding whitespace, a leading ``v``, and optional trailing ``Beta`` marker (GitHub release naming)."""
    s = (raw or "").strip()
    if len(s) > 1 and s[0].lower() == "v" and s[1].isdigit():
        s = s[1:].strip()
    # e.g. tags ``2026-04-24 Beta`` or ``2026-04-24-Beta`` — calver compare uses the date part only.
    s = re.sub(r"(?:[\s_-]+beta)?\s*$", "", s, flags=re.IGNORECASE).strip()
    return s


def parse_explorer_release_tuple(version: str) -> Optional[Tuple[int, int, int, int]]:
    """
    Return ``(year, month, day, revision)`` with ``revision == 0`` for bare ``YYYY-MM-DD``,
    or ``revision >= 2`` when a same-day suffix is present. ``None`` if invalid or ``.0`` / ``.1``.
    """
    s = normalize_release_tag(version)
    m = _EXPLORER_RELEASE_ID_RE.match(s)
    if not m:
        return None
    y, mo, d = int(m.group("y")), int(m.group("m")), int(m.group("d"))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    suffix = m.group("s")
    if suffix is None:
        return (y, mo, d, 0)
    rev = int(suffix, 10)
    if rev < 2:
        return None
    return (y, mo, d, rev)


def explorer_build_version_is_valid_format(version: str) -> bool:
    """True if *version* matches the documented release id shape (for CI / guards)."""
    return parse_explorer_release_tuple(version) is not None


def remote_release_is_newer_than_embedded(remote_tag: str, embedded_version: str) -> bool:
    """True iff *remote_tag* parses and sorts strictly after *embedded_version*."""
    a = parse_explorer_release_tuple(remote_tag)
    b = parse_explorer_release_tuple(embedded_version)
    if a is None or b is None:
        return False
    return a > b

"""Plain-text helpers for map popup location titles (not HTML)."""

from __future__ import annotations

import re

# Trailing close punctuation often orphans onto its own line when the card is a few px too narrow.
_ORPHAN_CLOSING_PUNCT_RE = re.compile(r"\s+([)\]\}\"'»])\s*$")


def prevent_orphan_closing_punctuation(text: str) -> str:
    """Use a non-breaking space before final ``)`` / ``]`` / similar so ``…773 )`` does not wrap as ``…773`` + ``)``."""
    return _ORPHAN_CLOSING_PUNCT_RE.sub("\u00a0\\1", str(text))

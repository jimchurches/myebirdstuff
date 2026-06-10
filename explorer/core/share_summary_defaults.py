"""
Default colour schemes and stat selections for share-summary cards (#157).

Framework-neutral: no Streamlit imports. Presentation and PNG export read from here;
``explorer.app.streamlit.defaults`` re-exports these for developer tuning.
"""

from __future__ import annotations

# Index into :data:`SHARE_SUMMARY_COLOR_SCHEMES` used by card HTML previews / PNG export.
SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT = 0

# Each scheme: ``bg``, ``bg_alt``, ``text``, ``muted``, ``border``, ``accent``.
# Add entries here to trial themes; flip ``SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT`` to test.
SHARE_SUMMARY_COLOR_SCHEMES: tuple[dict[str, str], ...] = (
    {
        "id": "light",
        "bg": "#ffffff",
        "bg_alt": "#f9fafb",
        "text": "#111827",
        "muted": "#6b7280",
        "border": "#e5e7eb",
        "accent": "#2d6a4f",
    },
)

# Default stat labels per layout (user-selectable stats planned for v1 integration).
SHARE_SUMMARY_HERO_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_TILES_DEFAULT_STATS: tuple[str, ...] = SHARE_SUMMARY_HERO_DEFAULT_STATS + (
    "Countries",
    "Birding days",
)
SHARE_SUMMARY_SPOTLIGHT_STAT_DEFAULT = "lifers"

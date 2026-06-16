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
        "name": "Light",
        "bg": "#ffffff",
        "bg_alt": "#f9fafb",
        "text": "#111827",
        "muted": "#6b7280",
        "border": "#e5e7eb",
        "accent": "#2d6a4f",
    },
    {
        "id": "dark",
        "name": "Dark",
        "bg": "#0d120f",
        "bg_alt": "#161f19",
        "text": "#f0f3f1",
        "muted": "#8fa79a",
        "border": "#263329",
        "accent": "#74c69d",
    },
)


def share_summary_color_scheme_index(scheme_id: str) -> int:
    """Resolve a scheme id (e.g. ``light``) to its index in :data:`SHARE_SUMMARY_COLOR_SCHEMES`."""
    for i, scheme in enumerate(SHARE_SUMMARY_COLOR_SCHEMES):
        if scheme["id"] == scheme_id:
            return i
    return SHARE_SUMMARY_COLOR_SCHEME_INDEX_DEFAULT


def share_summary_color_scheme_label(scheme_id: str) -> str:
    """Human label for a scheme id."""
    for scheme in SHARE_SUMMARY_COLOR_SCHEMES:
        if scheme["id"] == scheme_id:
            return scheme.get("name") or scheme_id
    return scheme_id


SHARE_SUMMARY_COLOR_SCHEME_IDS: tuple[str, ...] = tuple(
    scheme["id"] for scheme in SHARE_SUMMARY_COLOR_SCHEMES
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
# Lifetime (all data) — hero omits lifers; tiles/list share the same six-stat order.
SHARE_SUMMARY_LIFETIME_HERO_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Countries",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_LIFETIME_TILES_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Countries",
    "Birding days",
    "Total checklists",
    "Total individuals",
    "Longest streak (days)",
)
# Story format (1080×1920) — statistics grid and list may show up to this many stats.
SHARE_SUMMARY_STORY_MAX_STATS = 10
SHARE_SUMMARY_SPOTLIGHT_STAT_DEFAULT = "lifers"
# Display label on spotlight cards (matches Available statistics / card picker).
SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT = "Lifers"

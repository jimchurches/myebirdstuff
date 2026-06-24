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

# Default stat label order for share cards (user-selectable stats planned for v1 integration).
# Four-stat set is the core period picker default; tiles/list extend it to six stats.
SHARE_SUMMARY_FOUR_STAT_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Total checklists",
    "Unique locations",
)
# Country/region scope — omits world-only stats such as Countries.
SHARE_SUMMARY_COUNTRY_FOUR_STAT_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_COUNTRY_LIFETIME_FOUR_STAT_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Total individuals",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_COUNTRY_TILES_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Birding days",
    "Total individuals",
    "Total checklists",
    "Unique locations",
)
SHARE_SUMMARY_TILES_DEFAULT_STATS: tuple[str, ...] = SHARE_SUMMARY_FOUR_STAT_DEFAULT_STATS + (
    "Countries",
    "Birding days",
)
# Lifetime (all data) — four-stat fallback omits lifers; tiles/list share the same six-stat order.
SHARE_SUMMARY_LIFETIME_FOUR_STAT_DEFAULT_STATS: tuple[str, ...] = (
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
SHARE_SUMMARY_COUNTRY_LIFETIME_TILES_DEFAULT_STATS: tuple[str, ...] = (
    "Total species",
    "Lifers",
    "Birding days",
    "Total individuals",
    "Total checklists",
    "Unique locations",
)
# Story format (1080×1920) — statistics grid may show up to this many stats.
SHARE_SUMMARY_STORY_MAX_STATS = 10
# Statistics List (minimal) on story — cap 18; slot count is min(available, cap).
SHARE_SUMMARY_MINIMAL_STORY_MAX_STATS = 18
# Display label on spotlight cards (matches Available statistics / card picker).
SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT = "Lifers"

# Card green subtitle headings (tunable without editing layout code).
# Tiles / minimal / spotlight use layout subtitles unless period_kind is ``lifetime``,
# when :data:`SHARE_SUMMARY_LIFETIME_SUBTITLE` applies to all layouts.
SHARE_SUMMARY_PERIOD_SUBTITLE_YEAR = "Birding year in review"
SHARE_SUMMARY_PERIOD_SUBTITLE_MONTH = "Monthly birding summary"
SHARE_SUMMARY_PERIOD_SUBTITLE_WEEK = "Weekly birding summary"
SHARE_SUMMARY_PERIOD_SUBTITLE_LIFETIME = "My Birding Stats"
SHARE_SUMMARY_PERIOD_SUBTITLE_CUSTOM = "Birding summary"
SHARE_SUMMARY_LIFETIME_SUBTITLE = "My Birding Stats"
SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES = "My birding stats"
SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL = "Summary"
SHARE_SUMMARY_LAYOUT_SUBTITLE_SPOTLIGHT = "My birding stats"

_PERIOD_SUBTITLE_BY_KIND: dict[str, str] = {
    "year": SHARE_SUMMARY_PERIOD_SUBTITLE_YEAR,
    "month": SHARE_SUMMARY_PERIOD_SUBTITLE_MONTH,
    "week": SHARE_SUMMARY_PERIOD_SUBTITLE_WEEK,
    "lifetime": SHARE_SUMMARY_PERIOD_SUBTITLE_LIFETIME,
    "custom": SHARE_SUMMARY_PERIOD_SUBTITLE_CUSTOM,
}

_LAYOUT_SUBTITLE_BY_LAYOUT: dict[str, str] = {
    "tiles": SHARE_SUMMARY_LAYOUT_SUBTITLE_TILES,
    "minimal": SHARE_SUMMARY_LAYOUT_SUBTITLE_MINIMAL,
    "spotlight": SHARE_SUMMARY_LAYOUT_SUBTITLE_SPOTLIGHT,
}


def share_summary_period_subtitle(period_kind: str) -> str:
    """Period-based green subtitle (year in review, monthly summary, etc.)."""
    if period_kind == "lifetime":
        return SHARE_SUMMARY_LIFETIME_SUBTITLE
    return _PERIOD_SUBTITLE_BY_KIND.get(period_kind, SHARE_SUMMARY_PERIOD_SUBTITLE_CUSTOM)


def share_summary_card_subtitle(
    *,
    layout: str,
    period_kind: str,
    trip_title: str | None = None,
) -> str | None:
    """Green subtitle heading for a card layout; ``None`` when trip title replaces it."""
    if trip_title:
        return None
    if period_kind == "lifetime":
        return SHARE_SUMMARY_LIFETIME_SUBTITLE
    return _LAYOUT_SUBTITLE_BY_LAYOUT.get(layout, SHARE_SUMMARY_PERIOD_SUBTITLE_CUSTOM)

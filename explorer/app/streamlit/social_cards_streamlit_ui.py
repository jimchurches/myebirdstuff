"""Social Cards main-column UI — stat pickers, preview fragment, PNG export."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from explorer.app.streamlit.app_map_ui import inject_auto_click_streamlit_download_js
from explorer.app.streamlit.perf_instrumentation import perf_span
from explorer.app.streamlit.social_cards_session_keys import SocialCardsSessionKeys
from explorer.app.streamlit.social_cards_streamlit_helpers import (
    card_can_accept_stat,
    card_stat_max_slots,
    card_stat_min_slots,
    card_stat_ui_row_count,
    default_card_stat_slot_count,
    effective_card_stat_labels,
    png_export_fingerprint,
    resolve_card_stat_selectbox_value,
    sanitize_card_stat_picks,
    stats_on_card,
    status_metrics_lookup,
    tiles_circle_cluster_picker,
)
from explorer.core.share_summary_compute import (
    PeriodKind,
    ShareSummaryAllTimeStats,
    ShareSummaryGeoScope,
    ShareSummaryStats,
)
from explorer.core.share_summary_defaults import (
    SHARE_SUMMARY_INSIGHT_FACT_DEFAULT,
    SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT,
    share_summary_color_scheme_fingerprint,
)
from explorer.core.share_summary_insight_facts import (
    INSIGHT_FACT_PICKER_LABELS,
    InsightFactId,
    ShareSummaryInsightFact,
    compute_insight_facts,
    insight_fact_requires_species,
)
from explorer.presentation.share_summary_circles_preview import (
    TILES_CIRCLE_CLUSTER_DEFAULT,
    tiles_circle_cluster_max,
)
from explorer.presentation.share_summary_png_export import (
    share_summary_png_filename,
    share_summary_to_png_bytes,
)
from explorer.presentation.share_summary_preview import (
    FormatId,
    LayoutId,
    SpotlightPresentationId,
    TilesPresentationId,
    default_card_stat_labels,
    layout_card_stat_storage_max,
    layout_grid_slot_limits_caption,
    render_share_summary_preview_html,
    resolve_insight_fact,
)

SOCIAL_CARDS_STATISTICS_LABEL = "Card statistics"
SOCIAL_CARDS_CURRENT_CARD_LABEL = "Current card"
_CHIP_STRIP_COLS_PER_ROW = 3


def _rerun_social_cards_fragment() -> None:
    """Rerun only the card fragment — avoids map prep and insight recompute (#328)."""
    st.rerun(scope="fragment")

SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY = "_social_cards_png_export_bytes"
SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY = "_social_cards_png_export_fingerprint"
SOCIAL_CARDS_PNG_EXPORT_ERROR_KEY = "_social_cards_png_export_error"
SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY = "_social_cards_png_auto_download"
SOCIAL_CARDS_PNG_EXPORT_BTN_KEY = "social_cards_export_png_btn"
SOCIAL_CARDS_PNG_DOWNLOAD_BTN_KEY = "social_cards_export_png_download_btn"


@st.cache_data(show_spinner="Generating PNG…")
def cached_share_summary_png(
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    card_stat_labels: tuple[str, ...],
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None,
    color_scheme_index: int,
    color_scheme_fingerprint: tuple[tuple[str, str], ...],
    scope_label: str | None,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId = "grid",
    spotlight_presentation: SpotlightPresentationId = "classic",
    insight_fact: ShareSummaryInsightFact | None = None,
) -> bytes:
    del color_scheme_fingerprint  # cache key only — render reads live scheme by index
    return share_summary_to_png_bytes(
        stats,
        layout=layout,
        fmt=fmt,
        spotlight_label=spotlight_label,
        insight_fact=insight_fact,
        card_stat_labels=card_stat_labels,
        all_time=all_time,
        color_scheme_index=color_scheme_index,
        scope_label=scope_label,
        geo_scope=geo_scope,
        tiles_presentation=tiles_presentation,
        spotlight_presentation=spotlight_presentation,
    )


def _clear_card_stat_selectbox_keys(
    layout: LayoutId, keys: SocialCardsSessionKeys
) -> None:
    """Drop stale selectbox widget state so Reset / session picks take effect."""
    for i in range(layout_card_stat_storage_max(layout)):
        st.session_state.pop(keys.card_stat_selectbox(layout, i), None)


def _sync_card_stat_selectbox_value(
    layout: LayoutId,
    index: int,
    *,
    options: list[str],
    desired: str,
    keys: SocialCardsSessionKeys,
) -> str:
    """Align selectbox session state without clobbering a valid user choice."""
    key = keys.card_stat_selectbox(layout, index)
    value = resolve_card_stat_selectbox_value(
        session_value=st.session_state.get(key),
        desired=desired,
        options=options,
    )
    st.session_state[key] = value
    return value


def _ensure_card_stat_picks(
    layout: LayoutId,
    status_metrics: list[tuple[str, str]],
    fmt: FormatId,
    period_kind: PeriodKind,
    *,
    data_scope: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId,
    keys: SocialCardsSessionKeys,
) -> list[str]:
    """Initialize or sanitize session picks for *layout*; returns UI row values."""
    circle_cluster = tiles_circle_cluster_picker(layout, tiles_presentation)
    max_slots = card_stat_max_slots(
        layout,
        fmt,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )
    storage_max = (
        tiles_circle_cluster_max(fmt)
        if circle_cluster
        else layout_card_stat_storage_max(layout)
    )
    available = frozenset(label for label, _ in status_metrics)
    picks_key = keys.card_stat_picks(layout, period_kind)
    count_key = keys.card_stat_slot_count(layout, period_kind)
    scope_key = keys.card_stat_scope(layout, period_kind)
    defaults = list(
        default_card_stat_labels(
            layout,
            status_metrics,
            period_kind=period_kind,
            geo_scope=geo_scope,
            fmt=fmt,
        )
    )

    if st.session_state.get(scope_key) != data_scope:
        st.session_state[scope_key] = data_scope
        st.session_state.pop(picks_key, None)
        st.session_state.pop(count_key, None)
        _clear_card_stat_selectbox_keys(layout, keys)

    if picks_key not in st.session_state:
        st.session_state[picks_key] = defaults
        st.session_state[count_key] = default_card_stat_slot_count(
            circle_cluster=circle_cluster,
            defaults=defaults,
            max_slots=max_slots,
            layout=layout,
            fmt=fmt,
            tiles_presentation=tiles_presentation,
        )

    if (
        not sanitize_card_stat_picks(
            list(st.session_state[picks_key]),
            available=available,
            max_slots=storage_max,
        )
        and defaults
    ):
        _clear_card_stat_selectbox_keys(layout, keys)
        st.session_state[picks_key] = defaults
        st.session_state[count_key] = default_card_stat_slot_count(
            circle_cluster=circle_cluster,
            defaults=defaults,
            max_slots=max_slots,
            layout=layout,
            fmt=fmt,
            tiles_presentation=tiles_presentation,
        )

    sanitized = sanitize_card_stat_picks(
        list(st.session_state[picks_key]),
        available=available,
        max_slots=storage_max,
    )
    slot_count = int(st.session_state.get(count_key, max(1, len(sanitized))))
    ui_rows = card_stat_ui_row_count(
        layout,
        fmt,
        slot_count=slot_count,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )

    raw = list(st.session_state[picks_key])
    compact = [p for p in raw if p]
    picks = (compact + [""] * ui_rows)[:ui_rows]
    st.session_state[count_key] = ui_rows

    st.session_state[picks_key] = picks
    return picks


def _add_stat_to_card(
    label: str,
    *,
    layout: LayoutId,
    period_kind: PeriodKind,
    fmt: FormatId,
    tiles_presentation: TilesPresentationId,
    keys: SocialCardsSessionKeys,
    available_stat_count: int | None = None,
) -> None:
    """Fill the next empty card slot, or append a row when allowed."""
    picks_key = keys.card_stat_picks(layout, period_kind)
    count_key = keys.card_stat_slot_count(layout, period_kind)
    max_slots = card_stat_max_slots(
        layout,
        fmt,
        tiles_presentation=tiles_presentation,
        available_stat_count=available_stat_count,
    )
    picks = list(st.session_state.get(picks_key, []))
    slot_count = int(st.session_state.get(count_key, 1))
    ui_rows = card_stat_ui_row_count(
        layout,
        fmt,
        slot_count=slot_count,
        tiles_presentation=tiles_presentation,
        available_stat_count=available_stat_count,
    )
    active = (picks + [""] * ui_rows)[:ui_rows]

    for i in range(ui_rows):
        if not active[i]:
            active[i] = label
            st.session_state[picks_key] = active + picks[ui_rows:]
            _clear_card_stat_selectbox_keys(layout, keys)
            return

    if ui_rows < max_slots:
        active.append(label)
        st.session_state[count_key] = ui_rows + 1
        st.session_state[picks_key] = active
        _clear_card_stat_selectbox_keys(layout, keys)


def _add_stat_to_card_on_click(
    stat_label: str,
    layout: LayoutId,
    period_kind: PeriodKind,
    fmt: FormatId,
    tiles_presentation: TilesPresentationId,
    keys: SocialCardsSessionKeys,
    available_stat_count: int,
) -> None:
    """Callback — runs before widgets so selectbox keys can be cleared safely."""
    _add_stat_to_card(
        stat_label,
        layout=layout,
        period_kind=period_kind,
        fmt=fmt,
        tiles_presentation=tiles_presentation,
        keys=keys,
        available_stat_count=available_stat_count,
    )


def _not_on_card_chip_strip(
    *,
    layout: LayoutId,
    period_kind: PeriodKind,
    fmt: FormatId,
    status_metrics: list[tuple[str, str]],
    picks: list[str],
    slot_count: int,
    metrics_lookup: dict[str, str],
    tiles_presentation: TilesPresentationId,
    keys: SocialCardsSessionKeys,
) -> None:
    """Compact chips for stats not yet on the card; click to add."""
    on_card = stats_on_card(picks)
    not_on_card = [
        (stat_label, metrics_lookup[stat_label])
        for stat_label, _ in status_metrics
        if stat_label not in on_card
    ]
    if not not_on_card:
        st.caption("All available stats are on the card.")
        return

    can_add = card_can_accept_stat(
        layout,
        fmt,
        picks,
        slot_count,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )

    available_stat_count = len(status_metrics)
    for row_start in range(0, len(not_on_card), _CHIP_STRIP_COLS_PER_ROW):
        row_items = not_on_card[row_start : row_start + _CHIP_STRIP_COLS_PER_ROW]
        cols = st.columns(_CHIP_STRIP_COLS_PER_ROW)
        for col_index in range(_CHIP_STRIP_COLS_PER_ROW):
            with cols[col_index]:
                if col_index >= len(row_items):
                    continue
                stat_label, value = row_items[col_index]
                chip_index = row_start + col_index
                st.button(
                    f"{stat_label} · {value}",
                    key=keys.stat_chip(layout, period_kind, chip_index),
                    type="tertiary",
                    use_container_width=False,
                    disabled=not can_add,
                    on_click=_add_stat_to_card_on_click,
                    args=(
                        stat_label,
                        layout,
                        period_kind,
                        fmt,
                        tiles_presentation,
                        keys,
                        available_stat_count,
                    ),
                )


def render_card_stat_picker_ui(
    layout: LayoutId,
    status_metrics: list[tuple[str, str]],
    fmt: FormatId,
    period_kind: PeriodKind,
    *,
    data_scope: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId,
    keys: SocialCardsSessionKeys,
) -> tuple[str, ...]:
    """Ordered stat picker for tiles / list; hidden for spotlight."""
    if layout in ("spotlight", "insight"):
        return ()

    max_slots = card_stat_max_slots(
        layout,
        fmt,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )
    circle_cluster = tiles_circle_cluster_picker(layout, tiles_presentation)
    available_labels = [label for label, _ in status_metrics]
    metrics_lookup = status_metrics_lookup(status_metrics)
    if not available_labels:
        st.caption("No statistics available for this period.")
        return ()

    picks_key = keys.card_stat_picks(layout, period_kind)
    count_key = keys.card_stat_slot_count(layout, period_kind)
    picks = _ensure_card_stat_picks(
        layout,
        status_metrics,
        fmt,
        period_kind,
        data_scope=data_scope,
        geo_scope=geo_scope,
        tiles_presentation=tiles_presentation,
        keys=keys,
    )
    ui_rows = card_stat_ui_row_count(
        layout,
        fmt,
        slot_count=int(st.session_state[count_key]),
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )

    if circle_cluster:
        st.caption(
            f"Supports up to {max_slots} stats. "
            f"The default is {TILES_CIRCLE_CLUSTER_DEFAULT} circles."
        )
    elif layout == "tiles":
        min_slots = card_stat_min_slots(
            layout, fmt, tiles_presentation=tiles_presentation
        )
        st.caption(
            f"Statistics Grid: {min_slots}–{max_slots} stats "
            f"({layout_grid_slot_limits_caption()}). "
            "Use Add stat or the chips below to add more."
        )
    else:
        st.caption(
            f"Supports up to {max_slots} stats. "
            "Use Add stat or the chips below to add more."
        )

    stat_row_cols = [0.5, 6, 1.8, 2.2]
    min_slots = card_stat_min_slots(layout, fmt, tiles_presentation=tiles_presentation)

    for i in range(ui_rows):
        current = picks[i] if i < len(picks) else ""
        other = {picks[j] for j in range(len(picks)) if j != i and picks[j]}
        options = [""] + [lab for lab in available_labels if lab not in other]
        current = _sync_card_stat_selectbox_value(
            layout, i, options=options, desired=current, keys=keys
        )
        picks[i] = current
        can_up = i > 0
        can_down = i < ui_rows - 1
        can_remove = ui_rows > min_slots and (i > 0 or bool(current))

        col_num, col_sel, col_val, col_actions = st.columns(
            stat_row_cols,
            vertical_alignment="center",
        )
        with col_num:
            st.markdown(f"**{i + 1}**")
        with col_sel:
            choice = st.selectbox(
                "Stat",
                options=options,
                format_func=lambda x: "—" if x == "" else x,
                key=keys.card_stat_selectbox(layout, i),
                label_visibility="collapsed",
            )
            picks[i] = choice or ""
        with col_val:
            value = metrics_lookup.get(picks[i], "") if picks[i] else ""
            st.markdown(f"**{value}**" if value else "—")
        with col_actions:
            btn_up, btn_down, btn_rm = st.columns(3, gap="small")
            with btn_up:
                if st.button(
                    "↑",
                    key=keys.card_stat_up(layout, i),
                    help="Move up",
                    disabled=not can_up,
                    use_container_width=True,
                ):
                    picks[i - 1], picks[i] = picks[i], picks[i - 1]
                    st.session_state[picks_key] = picks[:ui_rows]
                    _clear_card_stat_selectbox_keys(layout, keys)
                    _rerun_social_cards_fragment()
            with btn_down:
                if st.button(
                    "↓",
                    key=keys.card_stat_down(layout, i),
                    help="Move down",
                    disabled=not can_down,
                    use_container_width=True,
                ):
                    picks[i + 1], picks[i] = picks[i], picks[i + 1]
                    st.session_state[picks_key] = picks[:ui_rows]
                    _clear_card_stat_selectbox_keys(layout, keys)
                    _rerun_social_cards_fragment()
            with btn_rm:
                if st.button(
                    "✕",
                    key=keys.card_stat_rm(layout, i),
                    help="Remove this stat",
                    disabled=not can_remove,
                    use_container_width=True,
                ):
                    if i == 0 and ui_rows == 1:
                        picks[0] = ""
                    elif i == 0:
                        picks.pop(0)
                        st.session_state[count_key] = ui_rows - 1
                    else:
                        picks.pop(i)
                        st.session_state[count_key] = ui_rows - 1
                    st.session_state[picks_key] = picks[:ui_rows]
                    _clear_card_stat_selectbox_keys(layout, keys)
                    _rerun_social_cards_fragment()

    col_num_foot, col_sel_foot, col_val_foot, col_actions_foot = st.columns(
        stat_row_cols,
        vertical_alignment="center",
    )
    with col_sel_foot:
        if ui_rows < max_slots and st.button(
            "Add stat",
            key=keys.card_stat_add(layout),
        ):
            st.session_state[count_key] = ui_rows + 1
            _rerun_social_cards_fragment()
    with col_actions_foot:
        _, foot_down, _ = st.columns(3, gap="small")
        with foot_down:
            if st.button(
                "Reset",
                key=keys.card_stat_reset(layout),
                help="Restore this layout's default stat list",
                use_container_width=True,
            ):
                defaults = list(
                    default_card_stat_labels(
                        layout,
                        status_metrics,
                        period_kind=period_kind,
                        geo_scope=geo_scope,
                        fmt=fmt,
                    )
                )
                _clear_card_stat_selectbox_keys(layout, keys)
                st.session_state[picks_key] = defaults
                st.session_state[count_key] = default_card_stat_slot_count(
                    circle_cluster=circle_cluster,
                    defaults=defaults,
                    max_slots=max_slots,
                    layout=layout,
                    fmt=fmt,
                    tiles_presentation=tiles_presentation,
                )
                _rerun_social_cards_fragment()

    slot_count = int(st.session_state[count_key])
    can_add_more = card_can_accept_stat(
        layout,
        fmt,
        picks[:ui_rows],
        slot_count,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )
    stats_not_on_card = [
        label
        for label in available_labels
        if label not in stats_on_card(picks[:ui_rows])
    ]
    if stats_not_on_card and not can_add_more:
        st.info("Card is full.")

    st.session_state[picks_key] = picks[:ui_rows]
    final = effective_card_stat_labels(
        picks,
        layout,
        fmt,
        tiles_presentation=tiles_presentation,
        status_metrics=status_metrics,
    )
    if not final:
        st.caption("Select at least one stat to show on the card.")

    st.divider()
    _not_on_card_chip_strip(
        layout=layout,
        period_kind=period_kind,
        fmt=fmt,
        status_metrics=status_metrics,
        picks=picks[:ui_rows],
        slot_count=slot_count,
        metrics_lookup=metrics_lookup,
        tiles_presentation=tiles_presentation,
        keys=keys,
    )
    return final


def spotlight_label_from_session(
    status_metrics: list[tuple[str, str]],
    keys: SocialCardsSessionKeys,
) -> str:
    available = {label for label, _ in status_metrics}
    raw = st.session_state.get(keys.spotlight_label)
    if isinstance(raw, str) and raw.strip() in available:
        return raw.strip()
    if SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT in available:
        return SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT
    if status_metrics:
        return status_metrics[0][0]
    return SHARE_SUMMARY_SPOTLIGHT_LABEL_DEFAULT


def _select_spotlight_stat(stat_label: str, keys: SocialCardsSessionKeys) -> None:
    """Callback — runs before widgets so the selectbox key can be updated."""
    st.session_state[keys.spotlight_label] = stat_label


def _spotlight_alternate_chip_strip(
    status_metrics: list[tuple[str, str]],
    *,
    current: str,
    metrics_lookup: dict[str, str],
    keys: SocialCardsSessionKeys,
) -> None:
    """Quick-switch chips for stats not currently spotlighted."""
    others = [
        (label, metrics_lookup[label])
        for label, _ in status_metrics
        if label != current
    ]
    if not others:
        return
    count = len(others)
    st.caption(
        f"{count} other stat{'s' if count != 1 else ''} available — click to spotlight."
    )
    for row_start in range(0, len(others), _CHIP_STRIP_COLS_PER_ROW):
        row_items = others[row_start : row_start + _CHIP_STRIP_COLS_PER_ROW]
        cols = st.columns(len(row_items))
        for col_index, (stat_label, value) in enumerate(row_items):
            with cols[col_index]:
                chip_index = row_start + col_index
                st.button(
                    f"{stat_label} · {value}",
                    key=keys.spotlight_chip(chip_index),
                    use_container_width=True,
                    help=f"Spotlight {stat_label}",
                    on_click=_select_spotlight_stat,
                    args=(stat_label, keys),
                )


def render_spotlight_stat_picker(
    status_metrics: list[tuple[str, str]],
    keys: SocialCardsSessionKeys,
) -> None:
    labels = [label for label, _ in status_metrics]
    if not labels:
        st.caption("No statistics available for this period.")
        return
    metrics_lookup = status_metrics_lookup(status_metrics)
    current = spotlight_label_from_session(status_metrics, keys)
    col_sel, col_val = st.columns([4, 1], vertical_alignment="bottom")
    with col_sel:
        st.selectbox(
            "Spotlight stat",
            options=labels,
            index=labels.index(current) if current in labels else 0,
            key=keys.spotlight_label,
            help="Single highlighted stat for the Spotlight layout.",
        )
    selected = spotlight_label_from_session(status_metrics, keys)
    with col_val:
        st.markdown(f"**{metrics_lookup.get(selected, '—')}**")

    st.divider()
    _spotlight_alternate_chip_strip(
        status_metrics,
        current=selected,
        metrics_lookup=metrics_lookup,
        keys=keys,
    )


def _insight_fact_options(
    facts: list[ShareSummaryInsightFact],
    *,
    species_options: tuple[str, ...] = (),
) -> list[tuple[InsightFactId, str]]:
    auto_ids: tuple[InsightFactId, ...] = (
        "most_common_checklist_species",
        "most_individuals_species",
        "biggest_checklist_count",
    )
    options: list[tuple[InsightFactId, str]] = []
    for fact_id in auto_ids:
        if any(f.fact_id == fact_id for f in facts):
            options.append((fact_id, INSIGHT_FACT_PICKER_LABELS[fact_id]))
    if species_options:
        options.append(
            ("species_individuals", INSIGHT_FACT_PICKER_LABELS["species_individuals"])
        )
    return options


def _insight_fact_id_from_session(
    options: list[tuple[InsightFactId, str]],
    keys: SocialCardsSessionKeys,
) -> InsightFactId:
    valid = {fact_id for fact_id, _ in options}
    raw = st.session_state.get(keys.insight_fact, SHARE_SUMMARY_INSIGHT_FACT_DEFAULT)
    if raw in valid:
        return raw  # type: ignore[return-value]
    if SHARE_SUMMARY_INSIGHT_FACT_DEFAULT in valid:
        return SHARE_SUMMARY_INSIGHT_FACT_DEFAULT
    return options[0][0] if options else SHARE_SUMMARY_INSIGHT_FACT_DEFAULT


def _insight_species_from_session(
    species_options: tuple[str, ...],
    keys: SocialCardsSessionKeys,
) -> str:
    raw = st.session_state.get(keys.insight_species)
    if isinstance(raw, str) and raw in species_options:
        return raw
    return species_options[0] if species_options else ""


def render_insight_fact_picker_ui(
    facts: list[ShareSummaryInsightFact],
    species_options: tuple[str, ...],
    *,
    df: pd.DataFrame,
    period,
    keys: SocialCardsSessionKeys,
) -> ShareSummaryInsightFact | None:
    """Insights fact picker; returns the resolved fact for preview/export."""
    options = _insight_fact_options(facts, species_options=species_options)
    if not options:
        st.caption("No insights available for this period.")
        return None

    fact_ids = [fact_id for fact_id, _ in options]
    current_id = _insight_fact_id_from_session(options, keys)
    st.selectbox(
        "Insights",
        options=fact_ids,
        format_func=lambda fid: INSIGHT_FACT_PICKER_LABELS[fid],
        index=fact_ids.index(current_id) if current_id in fact_ids else 0,
        key=keys.insight_fact,
        help="Species- and checklist-derived highlights for Interesting Insights cards.",
    )
    selected_id = _insight_fact_id_from_session(options, keys)

    species_common = ""
    if insight_fact_requires_species(selected_id):
        if not species_options:
            st.caption("No species in this period for a selected-species fact.")
            return None
        species_common = _insight_species_from_session(species_options, keys)
        st.selectbox(
            "Species",
            options=list(species_options),
            index=list(species_options).index(species_common) if species_common else 0,
            key=keys.insight_species,
        )
        species_common = _insight_species_from_session(species_options, keys)
        refreshed = compute_insight_facts(
            df,
            period,
            species_common=species_common,
        )
        return resolve_insight_fact(refreshed, selected_id)

    return resolve_insight_fact(facts, selected_id)


def centered_card_download_button(
    *,
    label: str,
    data: bytes,
    file_name: str,
    mime: str,
    help_text: str,
    button_key: str | None = None,
) -> None:
    """Download control centred under the scaled card preview."""
    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        st.download_button(
            label,
            data=data,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
            help=help_text,
            key=button_key,
        )


def _clear_stale_png_export(fingerprint: tuple[object, ...]) -> None:
    cached_fp = st.session_state.get(SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY)
    if cached_fp == fingerprint:
        return
    st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY, None)
    st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY, None)
    st.session_state.pop(SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY, None)


def _lazy_png_export_ready(fingerprint: tuple[object, ...]) -> bytes | None:
    if st.session_state.get(SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY) != fingerprint:
        return None
    raw = st.session_state.get(SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY)
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return None


def _generate_share_summary_png_bytes(
    *,
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    card_stat_labels: tuple[str, ...],
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None,
    color_scheme_index: int,
    scope_label: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId,
    spotlight_presentation: SpotlightPresentationId,
    resolved_fact: ShareSummaryInsightFact | None,
) -> bytes:
    """Build PNG on demand — bypasses ``cached_share_summary_png`` spinner/cache."""
    with perf_span("social_cards.png_export"):
        return share_summary_to_png_bytes(
            stats,
            layout=layout,
            fmt=fmt,
            spotlight_label=spotlight_label,
            insight_fact=resolved_fact,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            color_scheme_index=color_scheme_index,
            scope_label=scope_label,
            geo_scope=geo_scope,
            tiles_presentation=tiles_presentation,
            spotlight_presentation=spotlight_presentation,
        )


def render_lazy_png_export_controls(
    *,
    stats: ShareSummaryStats,
    layout: LayoutId,
    fmt: FormatId,
    card_stat_labels: tuple[str, ...],
    spotlight_label: str,
    all_time: ShareSummaryAllTimeStats | None,
    color_scheme_index: int,
    scope_label: str,
    geo_scope: ShareSummaryGeoScope,
    tiles_presentation: TilesPresentationId,
    spotlight_presentation: SpotlightPresentationId,
    resolved_fact: ShareSummaryInsightFact | None,
    export_button_label: str,
    png_filename: str,
) -> None:
    """One user click: build PNG (spinner), rerun, auto-fire Streamlit download."""
    fingerprint = png_export_fingerprint(
        stats=stats,
        layout=layout,
        fmt=fmt,
        card_stat_labels=card_stat_labels,
        spotlight_label=spotlight_label,
        all_time=all_time,
        color_scheme_index=color_scheme_index,
        scope_label=scope_label,
        geo_scope=geo_scope,
        tiles_presentation=tiles_presentation,
        spotlight_presentation=spotlight_presentation,
        insight_fact=resolved_fact,
    )
    _clear_stale_png_export(fingerprint)

    err = st.session_state.get(SOCIAL_CARDS_PNG_EXPORT_ERROR_KEY)
    if err:
        st.warning(str(err))

    if st.session_state.pop(SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY, False):
        ready_png = _lazy_png_export_ready(fingerprint)
        if ready_png is None:
            st.warning(
                "PNG export was prepared but bytes are missing. Try Export again."
            )
            return
        st.caption("Starting download…")
        centered_card_download_button(
            label=export_button_label,
            data=ready_png,
            file_name=png_filename,
            mime="image/png",
            help_text="PNG of the current card above.",
            button_key=SOCIAL_CARDS_PNG_DOWNLOAD_BTN_KEY,
        )
        inject_auto_click_streamlit_download_js(button_label=export_button_label)
        return

    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        if st.button(
            export_button_label,
            key=SOCIAL_CARDS_PNG_EXPORT_BTN_KEY,
            use_container_width=True,
            help="Generate a PNG of the current card.",
        ):
            st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_ERROR_KEY, None)
            try:
                png_bytes = _lazy_png_export_ready(fingerprint)
                if png_bytes is None:
                    with st.spinner("Generating PNG…"):
                        png_bytes = _generate_share_summary_png_bytes(
                            stats=stats,
                            layout=layout,
                            fmt=fmt,
                            card_stat_labels=card_stat_labels,
                            spotlight_label=spotlight_label,
                            all_time=all_time,
                            color_scheme_index=color_scheme_index,
                            scope_label=scope_label,
                            geo_scope=geo_scope,
                            tiles_presentation=tiles_presentation,
                            spotlight_presentation=spotlight_presentation,
                            resolved_fact=resolved_fact,
                        )
            except RuntimeError as exc:
                st.session_state[SOCIAL_CARDS_PNG_EXPORT_ERROR_KEY] = str(exc)
                st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY, None)
                st.session_state.pop(SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY, None)
                return
            st.session_state[SOCIAL_CARDS_PNG_EXPORT_BYTES_KEY] = png_bytes
            st.session_state[SOCIAL_CARDS_PNG_EXPORT_FINGERPRINT_KEY] = fingerprint
            st.session_state[SOCIAL_CARDS_PNG_AUTO_DOWNLOAD_KEY] = True
            _rerun_social_cards_fragment()


@st.fragment
def render_current_card_fragment(
    *,
    stats: ShareSummaryStats,
    all_time: ShareSummaryAllTimeStats | None,
    selected_layout: LayoutId,
    fmt: FormatId,
    scale: float,
    status_metrics: list[tuple[str, str]],
    color_scheme_index: int,
    card_stat_data_scope: str,
    scope_label: str,
    geo_scope: ShareSummaryGeoScope,
    keys: SocialCardsSessionKeys,
    tiles_presentation: TilesPresentationId = "grid",
    spotlight_presentation: SpotlightPresentationId = "classic",
    insight_facts: list[ShareSummaryInsightFact],
    insight_species_options: tuple[str, ...],
    df_scoped: pd.DataFrame,
    resolved_period,
    statistics_label: str = SOCIAL_CARDS_STATISTICS_LABEL,
    current_card_label: str = SOCIAL_CARDS_CURRENT_CARD_LABEL,
    export_button_label: str = "Export card",
    lazy_png_export: bool = False,
) -> None:
    """Card statistics controls, live preview, and PNG export."""
    card_stat_labels: tuple[str, ...] = ()
    resolved_fact: ShareSummaryInsightFact | None = None
    with st.expander(statistics_label, expanded=False):
        if selected_layout == "spotlight":
            render_spotlight_stat_picker(status_metrics, keys)
        elif selected_layout == "insight":
            resolved_fact = render_insight_fact_picker_ui(
                insight_facts,
                insight_species_options,
                df=df_scoped,
                period=resolved_period,
                keys=keys,
            )
        else:
            card_stat_labels = render_card_stat_picker_ui(
                selected_layout,
                status_metrics,
                fmt,
                stats.period_kind,
                data_scope=card_stat_data_scope,
                geo_scope=geo_scope,
                tiles_presentation=tiles_presentation,
                keys=keys,
            )

    spotlight_label = spotlight_label_from_session(status_metrics, keys)

    if (current_card_label or "").strip():
        st.subheader(current_card_label)
    st.markdown(
        render_share_summary_preview_html(
            stats,
            layout=selected_layout,
            fmt=fmt,
            tiles_presentation=tiles_presentation,
            spotlight_presentation=spotlight_presentation,
            scale=scale,
            spotlight_label=spotlight_label,
            insight_fact=resolved_fact,
            card_stat_labels=card_stat_labels,
            all_time=all_time,
            color_scheme_index=color_scheme_index,
            geo_scope=geo_scope,
            scope_label=scope_label,
        ),
        unsafe_allow_html=True,
    )

    png_filename = share_summary_png_filename(stats, layout=selected_layout, fmt=fmt)
    if lazy_png_export:
        render_lazy_png_export_controls(
            stats=stats,
            layout=selected_layout,
            fmt=fmt,
            card_stat_labels=card_stat_labels,
            spotlight_label=spotlight_label,
            all_time=all_time,
            color_scheme_index=color_scheme_index,
            scope_label=scope_label,
            geo_scope=geo_scope,
            tiles_presentation=tiles_presentation,
            spotlight_presentation=spotlight_presentation,
            resolved_fact=resolved_fact,
            export_button_label=export_button_label,
            png_filename=png_filename,
        )
        return

    try:
        png_bytes = cached_share_summary_png(
            stats,
            selected_layout,
            fmt,
            card_stat_labels,
            spotlight_label,
            all_time,
            color_scheme_index,
            share_summary_color_scheme_fingerprint(color_scheme_index),
            scope_label,
            geo_scope,
            tiles_presentation,
            spotlight_presentation,
            resolved_fact,
        )
    except RuntimeError as exc:
        st.warning(str(exc))
    else:
        centered_card_download_button(
            label=export_button_label,
            data=png_bytes,
            file_name=png_filename,
            mime="image/png",
            help_text="PNG of the current card above.",
        )

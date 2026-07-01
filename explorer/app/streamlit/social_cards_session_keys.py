"""Session-state key namespaces for Social Cards Streamlit widgets."""

from __future__ import annotations

from dataclasses import dataclass

from explorer.core.share_summary_compute import PeriodKind
from explorer.presentation.share_summary_preview import LayoutId


@dataclass(frozen=True)
class SocialCardsSessionKeys:
    """Widget keys for one Social Cards surface (design studio vs main app tab)."""

    prefix: str

    @property
    def tiles_presentation(self) -> str:
        return f"{self.prefix}_tiles_presentation"

    @property
    def spotlight_presentation(self) -> str:
        return f"{self.prefix}_spotlight_presentation"

    @property
    def insight_fact(self) -> str:
        return f"{self.prefix}_insight_fact"

    @property
    def insight_species(self) -> str:
        return f"{self.prefix}_insight_species"

    @property
    def color_theme(self) -> str:
        return f"{self.prefix}_color_theme"

    @property
    def spotlight_label(self) -> str:
        return f"{self.prefix}_spotlight_label"

    @property
    def geo_country(self) -> str:
        return f"{self.prefix}_geo_country"

    @property
    def geo_region(self) -> str:
        return f"{self.prefix}_geo_region"

    @property
    def preview_scale(self) -> str:
        return f"{self.prefix}_preview_scale"

    def card_stat_picks(self, layout: LayoutId, period_kind: PeriodKind) -> str:
        return f"{self.prefix}_card_stat_picks_{layout}_{period_kind}"

    def card_stat_slot_count(self, layout: LayoutId, period_kind: PeriodKind) -> str:
        return f"{self.prefix}_card_stat_slot_count_{layout}_{period_kind}"

    def card_stat_scope(self, layout: LayoutId, period_kind: PeriodKind) -> str:
        return f"{self.prefix}_card_stat_scope_{layout}_{period_kind}"

    def card_stat_selectbox(self, layout: LayoutId, index: int) -> str:
        return f"{self.prefix}_card_stat_sel_{layout}_{index}"

    def stat_chip(self, layout: LayoutId, period_kind: PeriodKind, chip_index: int) -> str:
        return f"{self.prefix}_stat_chip_{layout}_{period_kind}_{chip_index}"

    def card_stat_up(self, layout: LayoutId, index: int) -> str:
        return f"{self.prefix}_card_stat_up_{layout}_{index}"

    def card_stat_down(self, layout: LayoutId, index: int) -> str:
        return f"{self.prefix}_card_stat_down_{layout}_{index}"

    def card_stat_rm(self, layout: LayoutId, index: int) -> str:
        return f"{self.prefix}_card_stat_rm_{layout}_{index}"

    def card_stat_add(self, layout: LayoutId) -> str:
        return f"{self.prefix}_card_stat_add_{layout}"

    def card_stat_reset(self, layout: LayoutId) -> str:
        return f"{self.prefix}_card_stat_reset_{layout}"

    def spotlight_chip(self, chip_index: int) -> str:
        return f"{self.prefix}_spotlight_chip_{chip_index}"


DESIGN_SOCIAL_CARDS_KEYS = SocialCardsSessionKeys(prefix="design")

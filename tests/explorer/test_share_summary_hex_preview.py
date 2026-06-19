"""Tests for hex-grid share summary experiments."""

from explorer.presentation.share_summary_hex_preview import (
    HEX_VARIANT_IDS,
    _ORGANIC_HAND_WINDY_A,
    _ORGANIC_HAND_WINDY_B,
    organic_cluster_connected,
    render_hex_grid_preview_html,
)
from explorer.presentation.share_summary_preview import sample_share_summary_stats


def test_hex_variant_ids_count():
    assert len(HEX_VARIANT_IDS) == 12


def test_render_hex_grid_preview_html_all_variants():
    stats = sample_share_summary_stats()
    for variant in HEX_VARIANT_IDS:
        html = render_hex_grid_preview_html(stats, variant=variant, scale=0.3)
        assert "pebird-share-preview-wrap" in html
        assert "312" in html
        assert "Species" in html


def test_hex_grid_overlap_variant_uses_clip_path():
    stats = sample_share_summary_stats(period_kind="year")
    html = render_hex_grid_preview_html(stats, variant="clip_flat_classic")
    assert html.count("clip-path") >= 6


def test_organic_hand_presets_are_connected():
    for preset in _ORGANIC_HAND_WINDY_A.values():
        assert organic_cluster_connected(list(preset))
    for preset in _ORGANIC_HAND_WINDY_B.values():
        assert organic_cluster_connected(list(preset))


def test_organic_hive_variant_uses_absolute_blob():
    stats = sample_share_summary_stats(period_kind="year")
    html = render_hex_grid_preview_html(stats, variant="tessellate_flat")
    assert "position:absolute" in html
    assert "312" in html


def test_organic_hand_windy_variant_renders():
    stats = sample_share_summary_stats(period_kind="year")
    html = render_hex_grid_preview_html(stats, variant="blob_ring")
    assert html.count("clip-path") >= 6

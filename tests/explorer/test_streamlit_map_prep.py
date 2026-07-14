"""Tests for Streamlit map context prep."""


import pandas as pd
import pytest

from explorer.core.map_prep import (
    data_signature_for_caches,
    mean_center_from_location_data,
    prepare_all_locations_map_context,
)


def _tiny_df():
    return pd.DataFrame(
        {
            "Submission ID": ["S1"],
            "Date": [pd.Timestamp("2025-01-01")],
            "Time": ["06:15"],
            "datetime": [pd.Timestamp("2025-01-01 06:15")],
            "Count": [3],
            "Location ID": ["L1"],
            "Location": ["Test Location"],
            "Scientific Name": ["Anas gracilis"],
            "Common Name": ["Grey Teal"],
            "Latitude": [-35.0],
            "Longitude": [149.0],
            "Protocol": ["Traveling"],
            "Duration (Min)": [30],
            "Distance Traveled (km)": [1.5],
            "All Obs Reported": [1],
            "Number of Observers": [2],
        }
    )


def test_prepare_all_locations_map_context_has_location_totals():
    df = _tiny_df()
    ctx = prepare_all_locations_map_context(df)
    assert ctx["effective_totals"] == (1, 1, 1, 3)
    assert set(ctx["records_by_loc"]) == {"L1"}
    pd.testing.assert_frame_equal(ctx["records_by_loc"]["L1"].reset_index(drop=True), df)


def test_prepare_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        prepare_all_locations_map_context(pd.DataFrame())


def test_data_signature_for_caches_stable_for_same_data():
    df = _tiny_df()
    assert data_signature_for_caches(df, "disk") == data_signature_for_caches(df, "disk")


def test_data_signature_for_caches_differs_when_submission_ids_change():
    df_a = _tiny_df()
    df_b = df_a.copy()
    df_b.loc[0, "Submission ID"] = "S2"
    assert data_signature_for_caches(df_a, "disk") != data_signature_for_caches(df_b, "disk")


def test_data_signature_for_caches_includes_disk_file_identity(tmp_path):
    df = _tiny_df()
    csv_path = tmp_path / "MyEBirdData.csv"
    df.to_csv(csv_path, index=False)
    sig = data_signature_for_caches(df, "disk", data_abs_path=str(csv_path))
    assert sig[0] == "disk"
    assert sig[1] == 1
    assert ":" in sig[2]


def test_mean_center_from_location_data():
    df = _tiny_df()
    ctx = prepare_all_locations_map_context(df)
    c = mean_center_from_location_data(ctx["effective_location_data"])
    assert c == pytest.approx((-35.0, 149.0))


def test_mean_center_from_location_data_empty_returns_none():
    assert mean_center_from_location_data(pd.DataFrame()) is None
    assert mean_center_from_location_data(None) is None

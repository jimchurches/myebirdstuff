import pandas as pd

from notebooks.personal_ebird_explorer import _get_map_maintenance_data


def test_get_map_maintenance_data_detects_exact_and_close_locations():
    # Two exact duplicates at same coords, plus two locations within threshold
    data = pd.DataFrame(
        {
            "Location ID": ["L1", "L2", "L3", "L4"],
            "Location": ["Alpha", "Alpha duplicate", "Bravo", "Bravo-near"],
            # L1/L2 share exact coords; L3/L4 are nearby but not identical
            "Latitude": [-35.0, -35.0, -35.0010, -35.00105],
            "Longitude": [149.0, 149.0, 149.0010, 149.00105],
        }
    )

    exact_rows, near_pairs = _get_map_maintenance_data(data, threshold_m=10)

    # Exact duplicates: two rows, one per name, both with count=2 and same coords
    assert len(exact_rows) == 2
    names = {row[0] for row in exact_rows}
    assert names == {"Alpha", "Alpha duplicate"}
    for name, loc_id, count, lat, lon in exact_rows:
        assert count == 2
        assert lat == -35.0
        assert lon == 149.0

    # Close locations: exactly one pair for Bravo/Bravo-near within threshold
    assert len(near_pairs) == 1
    pair = near_pairs[0]
    assert {pair[0][0], pair[1][0]} == {"L3", "L4"}


def test_get_map_maintenance_data_respects_threshold():
    data = pd.DataFrame(
        {
            "Location ID": ["L1", "L2"],
            "Location": ["Far1", "Far2"],
            "Latitude": [-35.0, -35.01],
            "Longitude": [149.0, 149.02],
        }
    )

    # With a tiny threshold, nothing should be considered "close"
    exact_rows, near_pairs = _get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert near_pairs == []


def test_get_map_maintenance_data_single_location_returns_empty():
    data = pd.DataFrame(
        {
            "Location ID": ["L1"],
            "Location": ["Solo"],
            "Latitude": [-35.0],
            "Longitude": [149.0],
        }
    )

    exact_rows, near_pairs = _get_map_maintenance_data(data, threshold_m=10)
    assert exact_rows == []
    assert near_pairs == []


def test_get_map_maintenance_data_ignores_missing_coords():
    data = pd.DataFrame(
        {
            "Location ID": ["L1", "L2"],
            "Location": ["Valid", "Missing coords"],
            "Latitude": [-35.0, None],
            "Longitude": [149.0, None],
        }
    )

    exact_rows, near_pairs = _get_map_maintenance_data(data, threshold_m=10)
    # After dropping NaNs there is only one valid location → no duplicates or close pairs
    assert exact_rows == []
    assert near_pairs == []



import pandas as pd

from notebooks.personal_ebird_explorer import _get_map_maintenance_data


def test_get_map_maintenance_data_detects_exact_and_close_locations():
    # Two exact duplicates at same coords, plus two locations within threshold
    data = pd.DataFrame(
        {
            "Location ID": ["L1", "L2", "L3", "L4"],
            "Location": ["Alpha", "Alpha duplicate", "Bravo", "Bravo-near"],
            "Latitude": [-35.0, -35.0, -35.0000, -35.00005],
            "Longitude": [149.0, 149.0, 149.0000, 149.00005],
        }
    )

    exact_rows, near_pairs = _get_map_maintenance_data(data, threshold_m=10)

    # Exact duplicates: Alpha + Alpha duplicate at exactly same coords
    names = {row[0] for row in exact_rows}
    assert "Alpha" in names
    assert "Alpha duplicate" in names

    # Close locations: Bravo and Bravo-near should appear together in one pair
    assert any(
        {"L3", "L4"} == {p[0][0], p[1][0]} for p in near_pairs
    ), "Expected L3/L4 to be reported as a close-location pair"


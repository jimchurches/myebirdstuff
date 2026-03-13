"""Direct tests for personal_ebird_explorer.data_loader.load_dataset."""

import pandas as pd
import pytest
from io import StringIO

from personal_ebird_explorer.data_loader import load_dataset, REQUIRED_COLUMNS


# Minimal CSV with all required columns (one row) for valid-structure tests.
MINIMAL_VALID_CSV = """Date,Time,Location ID,Location,Latitude,Longitude,Common Name,Scientific Name,Submission ID,Count
2025-01-15,08:30,L123,My Patch,-33.8,151.2,House Sparrow,Passer domesticus,S12345678,2"""


def test_load_dataset_returns_dataframe_with_required_columns_and_datetime():
    """load_dataset on a valid CSV has all required columns plus datetime column of the right type."""
    df = load_dataset(StringIO(MINIMAL_VALID_CSV))

    assert isinstance(df, pd.DataFrame)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"missing column {col}"
    assert "datetime" in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["datetime"])

    assert df.loc[0, "datetime"].strftime("%Y-%m-%d %H:%M") == "2025-01-15 08:30"


def test_load_dataset_missing_one_required_column_raises():
    """load_dataset raises ValueError with clear message when one required column is missing."""
    csv = "Date,Time,Location ID,Location,Latitude,Longitude,Common Name,Scientific Name,Submission ID\n2025-01-15,08:30,L1,Loc,0,0,Sp,Passer dom,S1"
    with pytest.raises(ValueError, match=r"Dataset missing required columns:.*Count"):
        load_dataset(StringIO(csv))


def test_load_dataset_missing_multiple_required_columns_raises():
    """load_dataset raises ValueError listing all missing columns when several are absent."""
    csv = "Date,Time\n2025-01-15,08:30"
    with pytest.raises(ValueError, match="Dataset missing required columns:") as exc_info:
        load_dataset(StringIO(csv))
    msg = str(exc_info.value)
    # Message should list missing columns; at least these should be missing
    for col in ("Location ID", "Common Name", "Submission ID"):
        assert col in msg, f"error message should mention missing column {col}"


def test_load_dataset_empty_csv_raises():
    """load_dataset on CSV with headers but no required columns raises clear error."""
    csv = "Foo,Bar\n1,2"
    with pytest.raises(ValueError, match="Dataset missing required columns:"):
        load_dataset(StringIO(csv))


def test_load_dataset_headers_only_no_data_rows_raises():
    """load_dataset on CSV with valid headers but no data rows raises clear error."""
    csv = "Date,Time,Location ID,Location,Latitude,Longitude,Common Name,Scientific Name,Submission ID,Count"
    with pytest.raises(ValueError, match="Dataset is empty"):
        load_dataset(StringIO(csv))


def test_load_dataset_preserves_extra_columns():
    """load_dataset does not drop columns beyond the required set."""
    csv = """Date,Time,Location ID,Location,Latitude,Longitude,Common Name,Scientific Name,Submission ID,Count,ML Catalog Numbers
2025-01-15,08:30,L123,My Patch,-33.8,151.2,House Sparrow,Passer domesticus,S12345678,2,12345"""
    df = load_dataset(StringIO(csv))

    assert "ML Catalog Numbers" in df.columns
    assert df.loc[0, "Common Name"] == "House Sparrow"
    assert df.loc[0, "Location ID"] == "L123"

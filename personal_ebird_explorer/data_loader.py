"""
Dataset loading and preprocessing for Personal eBird Explorer.

Single entry point: load_dataset(path_or_file)
- Loads CSV (expected encoding: UTF-8), validates required columns and that the
  dataset is non-empty, creates canonical datetime column, returns DataFrame.
"""

import pandas as pd


# Columns required for the explorer to work; missing any of these raises a clear ValueError at load time.
REQUIRED_COLUMNS = [
    "Date",
    "Time",
    "Location ID",
    "Location",
    "Latitude",
    "Longitude",
    "Common Name",
    "Scientific Name",
    "Submission ID",
    "Count",
]


def add_datetime_column(df):
    """
    Parse Date and Time into a canonical datetime column.
    - Parses Date to datetime; fills missing Time with "00:00".
    - Missing/empty or "00:00" time → 11:59 PM so those rows sort last.
    - Adds column "datetime".
    """
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Time"] = df["Time"].fillna("00:00")
    # Missing, empty, or "00:00" → 11:59 PM so they sort last (we prefer checklists with real times for streak start/end)
    time_str = df["Time"].astype(str).str.strip().replace("00:00", "11:59 PM").replace("", "11:59 PM")
    date_str = df["Date"].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
    df["datetime"] = pd.to_datetime(date_str + " " + time_str, errors="coerce")
    return df


def load_dataset(path_or_file):
    """
    Load the eBird dataset from CSV and return a DataFrame ready for use.

    - Loads CSV from path_or_file (path string or file-like). Expected encoding: UTF-8.
    - Validates that all required columns (see REQUIRED_COLUMNS) exist; raises ValueError with a clear message if any are missing.
    - Raises ValueError if the dataset has no data rows (empty file or headers-only).
    - Creates the canonical datetime column (Date + Time → datetime).
    - Returns the DataFrame; does not change column names, sorting, or downstream behaviour.
    """
    df = pd.read_csv(path_or_file, encoding="utf-8")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")
    if df.empty:
        raise ValueError("Dataset is empty (no data rows).")
    return add_datetime_column(df)

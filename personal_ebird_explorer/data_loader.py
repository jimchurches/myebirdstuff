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
    Parse Date and Time into a canonical ``datetime`` column.

    - Parses ``Date`` to ``datetime64``.
    - Fills missing ``Time`` with ``"00:00"`` (preserves the raw column for
      display).
    - For the canonical ``datetime`` column, missing / empty / ``"00:00"``
      times are mapped to ``"23:59"`` so those rows sort to the **end** of
      their day.  eBird exports ``"00:00"`` when no observation time was
      recorded; real midnight checklists do not occur.
    - Adds column ``"datetime"`` (``datetime64[ns]``).
    """
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Time"] = df["Time"].fillna("00:00")
    # Build a 24-hour time string for the canonical column.
    # "00:00" means "no time recorded" in eBird exports → treat as 23:59.
    time_str = df["Time"].astype(str).str.strip().replace("00:00", "23:59").replace("", "23:59")
    date_str = df["Date"].dt.strftime("%Y-%m-%d").fillna("")
    # format="mixed" lets pandas parse each entry independently — critical
    # because eBird exports use 12h AM/PM ("09:37 PM") while the 23:59
    # replacement is 24h; a single inferred format would silently NaT one style.
    df["datetime"] = pd.to_datetime(
        date_str + " " + time_str, format="mixed", errors="coerce",
    )
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

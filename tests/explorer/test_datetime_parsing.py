import pandas as pd
import pytest

from personal_ebird_explorer.data_loader import add_datetime_column


def test_add_datetime_column_basic():
    df = pd.DataFrame(
        {
            "Date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "Time": ["06:15 AM", None, ""],
        }
    )

    out = add_datetime_column(df.copy())

    assert "datetime" in out.columns
    assert pd.api.types.is_datetime64_any_dtype(out["datetime"])

    # Explicit time preserved (eBird uses 12h AM/PM)
    assert out.loc[0, "datetime"].strftime("%Y-%m-%d %H:%M") == "2025-01-01 06:15"
    # Missing / empty times → 23:59 (sort to end of day)
    assert out.loc[1, "datetime"].strftime("%Y-%m-%d %H:%M") == "2025-01-02 23:59"
    assert out.loc[2, "datetime"].strftime("%Y-%m-%d %H:%M") == "2025-01-03 23:59"


# ---------------------------------------------------------------------------
# Edge cases for canonical datetime
# ---------------------------------------------------------------------------


def test_zero_time_becomes_2359():
    """eBird exports '00:00' when no time was recorded; should map to 23:59."""
    df = pd.DataFrame({"Date": ["2025-06-15"], "Time": ["00:00"]})
    out = add_datetime_column(df.copy())
    assert out.loc[0, "datetime"].strftime("%H:%M") == "23:59"


def test_explicit_time_preserved():
    """A real observation time must pass through unchanged."""
    for t, expected in [
        ("07:30 AM", "07:30"),
        ("12:00 PM", "12:00"),
        ("06:45 PM", "18:45"),
        ("11:00 PM", "23:00"),
    ]:
        df = pd.DataFrame({"Date": ["2025-03-01"], "Time": [t]})
        out = add_datetime_column(df.copy())
        assert out.loc[0, "datetime"].strftime("%H:%M") == expected


def test_missing_date_gives_nat():
    """If Date itself is missing, datetime should be NaT regardless of Time."""
    df = pd.DataFrame({"Date": [None], "Time": ["08:00 AM"]})
    out = add_datetime_column(df.copy())
    assert pd.isna(out.loc[0, "datetime"])


def test_malformed_time_gives_nat():
    """An unparseable time string should produce NaT, not an exception."""
    df = pd.DataFrame({"Date": ["2025-01-01"], "Time": ["not-a-time"]})
    out = add_datetime_column(df.copy())
    assert pd.isna(out.loc[0, "datetime"])


def test_whitespace_only_time_becomes_2359():
    """Whitespace-only Time should be treated as missing → 23:59."""
    df = pd.DataFrame({"Date": ["2025-04-10"], "Time": ["   "]})
    out = add_datetime_column(df.copy())
    assert out.loc[0, "datetime"].strftime("%H:%M") == "23:59"


def test_time_column_filled_for_display():
    """The raw Time column should have NaN replaced with '00:00' for display."""
    df = pd.DataFrame({"Date": ["2025-01-01"], "Time": [None]})
    out = add_datetime_column(df.copy())
    assert out.loc[0, "Time"] == "00:00"


def test_sorting_missing_times_come_last():
    """Records without a real time should sort after records with a time on the same day."""
    df = pd.DataFrame(
        {
            "Date": ["2025-01-01", "2025-01-01", "2025-01-01"],
            "Time": ["06:00 AM", None, "06:00 PM"],
        }
    )
    out = add_datetime_column(df.copy())
    sorted_df = out.sort_values("datetime")
    times = sorted_df["datetime"].dt.strftime("%H:%M").tolist()
    assert times == ["06:00", "18:00", "23:59"]


def test_multiple_days_sorting():
    """Canonical datetime sorts correctly across multiple days with mixed times."""
    df = pd.DataFrame(
        {
            "Date": ["2025-01-02", "2025-01-01", "2025-01-01", "2025-01-02"],
            "Time": ["07:00 AM", None, "08:00 AM", None],
        }
    )
    out = add_datetime_column(df.copy())
    sorted_df = out.sort_values("datetime")
    result = sorted_df["datetime"].dt.strftime("%Y-%m-%d %H:%M").tolist()
    assert result == [
        "2025-01-01 08:00",
        "2025-01-01 23:59",
        "2025-01-02 07:00",
        "2025-01-02 23:59",
    ]


def test_mixed_12h_and_24h_times():
    """format='mixed' handles both 12h AM/PM and 24h formats in the same column."""
    df = pd.DataFrame(
        {
            "Date": ["2025-01-01", "2025-01-01", "2025-01-01"],
            "Time": ["09:30 PM", "14:00", None],
        }
    )
    out = add_datetime_column(df.copy())
    assert out.loc[0, "datetime"].strftime("%H:%M") == "21:30"
    assert out.loc[1, "datetime"].strftime("%H:%M") == "14:00"
    assert out.loc[2, "datetime"].strftime("%H:%M") == "23:59"


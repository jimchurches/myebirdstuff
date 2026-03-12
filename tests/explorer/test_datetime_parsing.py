import pandas as pd

from notebooks.personal_ebird_explorer import add_datetime_column


def test_add_datetime_column_basic():
    df = pd.DataFrame(
        {
            "Date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "Time": ["06:15", None, ""],
        }
    )

    out = add_datetime_column(df.copy())

    assert "datetime" in out.columns
    assert pd.api.types.is_datetime64_any_dtype(out["datetime"])

    # Explicit time preserved
    assert out.loc[0, "datetime"].strftime("%Y-%m-%d %H:%M") == "2025-01-01 06:15"
    # Missing/empty time normalised to 23:59
    assert out.loc[1, "datetime"].strftime("%Y-%m-%d %H:%M") == "2025-01-02 23:59"
    assert out.loc[2, "datetime"].strftime("%Y-%m-%d %H:%M") == "2025-01-03 23:59"


"""Load the historical CSV (`data/challenge.csv`) into a normalized DataFrame.

Columns: date (datetime), snowpack (in SWE), precip (% of normal), reservoir (% capacity), month, year.
The CSV is monthly snapshots with `M/D/YY` dates that we parse and sort ascending.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ..config import CSV_PATH


@lru_cache(maxsize=1)
def load_history() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%y")
    df = df.sort_values("date").reset_index(drop=True)
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    return df


def latest_row() -> pd.Series:
    return load_history().iloc[-1]

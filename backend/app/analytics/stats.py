"""Historical statistics: per-month percentile bands and percentile lookups."""

from __future__ import annotations

import numpy as np
import pandas as pd

METRICS = ("snowpack", "precip", "reservoir")
BAND_PERCENTILES = (10, 25, 50, 75, 90)


def monthly_bands(history: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Return per-month percentile bands (p10/p25/p50/p75/p90) for `metric`."""
    grouped = history.groupby("month")[metric]
    out = pd.DataFrame({f"p{p}": grouped.quantile(p / 100) for p in BAND_PERCENTILES})
    out["mean"] = grouped.mean()
    out["min"] = grouped.min()
    out["max"] = grouped.max()
    return out.reset_index()


def value_percentile(history: pd.DataFrame, metric: str, month: int, value: float) -> float:
    """Empirical percentile of `value` within the historical month-of-year distribution."""
    series = history.loc[history["month"] == month, metric].dropna().to_numpy()
    if len(series) == 0:
        return 50.0
    rank = np.sum(series <= value)
    return round(100.0 * rank / len(series), 1)

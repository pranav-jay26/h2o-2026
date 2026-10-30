"""ZIP / city → coordinate lookup.

Loaded once from `data/uszips.csv`. Supports two query forms:
- 5-digit ZIP code         → unique row
- "City, ST" (state code)  → population-weighted centroid across the city's ZIPs

`uszips.csv` columns: zip, lat, lng, city, state_id, state_name, population, ...
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ..config import REPO_ROOT

USZIPS_CSV = REPO_ROOT / "data" / "uszips.csv"


@dataclass(frozen=True)
class Resolution:
    """Resolved geographic anchor for a query (ZIP or City, ST)."""

    kind: str           # "zip" | "city"
    lat: float
    lon: float
    zip: str            # canonical ZIP (input ZIP, or city's largest-population ZIP)
    city: str | None
    state_id: str | None
    population: int | None
    matched_zip_count: int  # 1 for ZIP queries, ≥1 for city queries


@lru_cache(maxsize=1)
def _load() -> pd.DataFrame:
    df = pd.read_csv(USZIPS_CSV, dtype={"zip": str})
    df.columns = [c.strip().lower() for c in df.columns]
    df["zip"] = df["zip"].str.strip().str.zfill(5)
    df["city_norm"] = df["city"].astype(str).str.strip().str.lower()
    df["state_id"] = df["state_id"].astype(str).str.strip().str.upper()
    df["population"] = pd.to_numeric(df.get("population", 0), errors="coerce").fillna(0).astype(int)
    return df[["zip", "lat", "lng", "city", "city_norm", "state_id", "state_name", "population"]]


def lookup_zip(zip_code: str) -> Resolution | None:
    z = zip_code.strip().zfill(5)
    if not z.isdigit() or len(z) != 5:
        return None
    df = _load()
    rows = df[df["zip"] == z]
    if rows.empty:
        return None
    row = rows.iloc[0]
    return Resolution(
        kind="zip",
        lat=float(row["lat"]),
        lon=float(row["lng"]),
        zip=z,
        city=str(row["city"]),
        state_id=str(row["state_id"]),
        population=int(row["population"]) if row["population"] else None,
        matched_zip_count=1,
    )


def lookup_city(city: str, state_id: str) -> Resolution | None:
    df = _load()
    city_norm = city.strip().lower()
    state_norm = state_id.strip().upper()
    rows = df[(df["city_norm"] == city_norm) & (df["state_id"] == state_norm)]
    if rows.empty:
        return None
    pops = rows["population"].astype(float)
    weights = pops if pops.sum() > 0 else pd.Series([1.0] * len(rows), index=rows.index)
    lat = float((rows["lat"] * weights).sum() / weights.sum())
    lon = float((rows["lng"] * weights).sum() / weights.sum())
    canonical = rows.sort_values("population", ascending=False).iloc[0]
    return Resolution(
        kind="city",
        lat=lat,
        lon=lon,
        zip=str(canonical["zip"]),
        city=str(canonical["city"]),
        state_id=str(canonical["state_id"]),
        population=int(rows["population"].sum()),
        matched_zip_count=int(len(rows)),
    )


def resolve(query: str) -> Resolution | None:
    """Accept a 5-digit ZIP or `City, ST`; return None if it doesn't parse or no match."""
    q = query.strip()
    if not q:
        return None
    if q.isdigit() and len(q.zfill(5)) == 5:
        return lookup_zip(q)
    if "," in q:
        city_part, state_part = q.rsplit(",", 1)
        city_part = city_part.strip()
        state_part = state_part.strip()
        if city_part and len(state_part) == 2 and state_part.isalpha():
            return lookup_city(city_part, state_part)
    return None

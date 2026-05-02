"""Static config for the demo. Anchored on Shasta Lake / Sacramento River basin."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = REPO_ROOT / "data" / "challenge.csv"


@dataclass(frozen=True)
class Basin:
    id: str
    name: str
    watershed: str
    cdec_station: str
    capacity_af: int  # reservoir capacity in acre-feet


SHASTA = Basin(
    id="shasta",
    name="Shasta Lake",
    watershed="Sacramento River",
    cdec_station="SHA",
    capacity_af=4_552_000,
)

BASINS: dict[str, Basin] = {SHASTA.id: SHASTA}
DEFAULT_BASIN = SHASTA


# Risk thresholds expressed as percentile bands of the historical month distribution.
# Lower percentile = drier/lower than typical = riskier.
RISK_BANDS = {
    "red": 10,
    "amber": 25,
    "watch": 50,
}

# Composite risk score weights — reservoir matters most for delivery risk in this MVP.
METRIC_WEIGHTS = {
    "reservoir": 0.5,
    "snowpack": 0.3,
    "precip": 0.2,
}

# CDEC live feed: cache TTL in seconds.
CDEC_CACHE_TTL_S = 600

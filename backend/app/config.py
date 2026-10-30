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
    lat: float
    lon: float
    has_history: bool = False  # whether challenge.csv covers this basin


# Anchor basin: Shasta Lake (the historical CSV is treated as Shasta history).
SHASTA = Basin(
    id="shasta",
    name="Shasta Lake",
    watershed="Sacramento River",
    cdec_station="SHA",
    capacity_af=4_552_000,
    lat=40.7197,
    lon=-122.4179,
    has_history=True,
)

# Other north Central Valley reservoirs — live CDEC only (no historical CSV yet).
OROVILLE = Basin(
    id="oroville",
    name="Lake Oroville",
    watershed="Feather River",
    cdec_station="ORO",
    capacity_af=3_537_577,
    lat=39.5394,
    lon=-121.4884,
)
TRINITY = Basin(
    id="trinity",
    name="Trinity Lake",
    watershed="Trinity River",
    cdec_station="CLE",
    capacity_af=2_447_650,
    lat=40.7889,
    lon=-122.7639,
)
FOLSOM = Basin(
    id="folsom",
    name="Folsom Lake",
    watershed="American River",
    cdec_station="FOL",
    capacity_af=977_000,
    lat=38.7100,
    lon=-121.1500,
)
BULLARDS = Basin(
    id="bullards",
    name="New Bullards Bar",
    watershed="Yuba River",
    cdec_station="BUL",
    capacity_af=966_103,
    lat=39.3956,
    lon=-121.1417,
)

BASINS: dict[str, Basin] = {
    b.id: b for b in (SHASTA, OROVILLE, TRINITY, FOLSOM, BULLARDS)
}
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

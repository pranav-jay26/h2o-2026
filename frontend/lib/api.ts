// Typed client for the FastAPI sidecar.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Metric = "snowpack" | "precip" | "reservoir";
export type RiskLevel = "green" | "amber" | "red";

export type MetricPayload = {
  value: number;
  month_mean: number;
  anomaly: number;
  z: number;
  percentile: number;
  compare_month: number;
  source: string;
  as_of: string;
  extras?: Record<string, unknown>;
};

export type RiskDriver = {
  metric: Metric;
  percentile: number;
  points: number;
  weight: number;
};

export type Snapshot = {
  basin: {
    id: string;
    name: string;
    watershed: string;
    cdec_station: string;
    capacity_af: number;
  };
  as_of: string;
  metrics: Record<Metric, MetricPayload>;
  risk: {
    score: number;
    level: RiskLevel;
    drivers: RiskDriver[];
    explanations: string[];
  };
  alerts: Alert[];
  data_freshness: {
    csv_latest: string;
    cdec_live: string | null;
    cdec_status: "ok" | "unavailable";
  };
};

export type Alert = {
  metric: Metric;
  level: RiskLevel;
  why: string;
  value: number;
  threshold: number;
  window: string;
  action: string;
};

export type TimeseriesPoint = {
  date: string;
  value: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  month_mean: number;
};

export type Timeseries = {
  basin_id: string;
  metric: Metric;
  points: TimeseriesPoint[];
};

export type ForecastPoint = { date: string; mean: number; lower: number; upper: number };
export type Forecast = {
  basin_id: string;
  model: string;
  horizon_months: number;
  as_of: string;
  metrics: Record<Metric, { latest: number; seven_day: number; monthly: ForecastPoint[] }>;
};

export type ReleaseLevel = "normal" | "watch" | "elevated";

export type ReleaseDriver = {
  key: string;
  label: string;
  weight: "low" | "medium" | "high";
};

export type ReleaseRisk = {
  level: ReleaseLevel;
  score: number;
  summary: string;
  drivers: ReleaseDriver[];
  thresholds: Record<string, number>;
};

export type MetBrief = {
  observed_30d_precip_in: number;
  pct_of_normal_precip: number | null;
  temp_anomaly_c: number;
};

export type ForecastBrief = {
  next_7d_total_in: number;
  forecast_temp_c_avg: number | null;
};

export type ReservoirMarker = {
  id: string;
  name: string;
  watershed: string;
  cdec_station: string;
  lat: number;
  lon: number;
  capacity_af: number;
  current: {
    percent_capacity: number | null;
    storage_af: number | null;
    as_of: string | null;
    source: string;
  };
  risk_level: RiskLevel | "unknown";
  release_risk: ReleaseRisk;
  met: MetBrief | null;
  forecast: ForecastBrief | null;
  has_history: boolean;
};

export const RELEASE_COLORS: Record<ReleaseLevel, string> = {
  normal: "#10b981",
  watch: "#f59e0b",
  elevated: "#ef4444",
};

export type ReservoirList = {
  as_of: string;
  count: number;
  reservoirs: ReservoirMarker[];
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return (await res.json()) as T;
}

export type UserAreaLevel = "likely" | "possible" | "unlikely" | "out_of_zone";

export type Resolution = {
  kind: "zip" | "city";
  zip: string;
  city: string | null;
  state_id: string | null;
  lat: number;
  lon: number;
  population: number | null;
  matched_zip_count: number;
};

export type ReleaseEstimate = {
  query: string;
  as_of: string;
  resolution: Resolution;
  nearest: {
    id: string;
    name: string;
    watershed: string;
    distance_mi: number;
    release_level: ReleaseLevel;
    release_score: number;
    drivers: ReleaseDriver[];
  };
  user_score: number;
  user_level: UserAreaLevel;
  distance_factor: number;
  summary: string;
  nearby: Array<{
    id: string;
    name: string;
    watershed: string;
    distance_mi: number;
    release_level: ReleaseLevel;
    release_score: number;
    factor: number;
  }>;
  thresholds: { near_miles: number; far_miles: number };
};

export const api = {
  snapshot: (basin: string) => get<Snapshot>(`/api/snapshot/${basin}`),
  timeseries: (basin: string, metric: Metric) =>
    get<Timeseries>(`/api/timeseries/${basin}/${metric}`),
  forecast: (basin: string, horizonMonths = 6) =>
    get<Forecast>(`/api/forecast/${basin}?horizon_months=${horizonMonths}`),
  reservoirs: () => get<ReservoirList>(`/api/reservoirs`),
  releaseEstimate: (q: string) =>
    get<ReleaseEstimate>(`/api/release-estimate?q=${encodeURIComponent(q)}`),
};

export const RISK_COLORS: Record<RiskLevel, string> = {
  green: "#10b981",
  amber: "#f59e0b",
  red: "#ef4444",
};

export const METRIC_LABELS: Record<Metric, string> = {
  snowpack: "Snowpack (SWE)",
  precip: "Precipitation (% of normal)",
  reservoir: "Reservoir (% capacity)",
};

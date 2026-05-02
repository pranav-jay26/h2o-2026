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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  snapshot: (basin: string) => get<Snapshot>(`/api/snapshot/${basin}`),
  timeseries: (basin: string, metric: Metric) =>
    get<Timeseries>(`/api/timeseries/${basin}/${metric}`),
  forecast: (basin: string, horizonMonths = 6) =>
    get<Forecast>(`/api/forecast/${basin}?horizon_months=${horizonMonths}`),
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

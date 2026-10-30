import { AlertsList } from "@/components/AlertsList";
import { ForecastStrip } from "@/components/ForecastStrip";
import MapPanel from "@/components/MapPanel";
import { MetricCard } from "@/components/MetricCard";
import { ReleasePanel } from "@/components/ReleasePanel";
import { RiskBadge } from "@/components/RiskBadge";
import { TrendChart } from "@/components/TrendChart";
import { ZipReleaseProbe } from "@/components/ZipReleaseProbe";
import { METRIC_LABELS, api, type Metric } from "@/lib/api";

const BASIN = "shasta";
const METRICS: Metric[] = ["snowpack", "precip", "reservoir"];
const UNITS: Record<Metric, string> = {
  snowpack: "in SWE",
  precip: "% norm",
  reservoir: "% cap",
};

export const dynamic = "force-dynamic";

export default async function Home() {
  let snapshot, forecast, snow, precip, reservoir, reservoirList;
  try {
    [snapshot, forecast, snow, precip, reservoir, reservoirList] = await Promise.all([
      api.snapshot(BASIN),
      api.forecast(BASIN, 6),
      api.timeseries(BASIN, "snowpack"),
      api.timeseries(BASIN, "precip"),
      api.timeseries(BASIN, "reservoir"),
      api.reservoirs(),
    ]);
  } catch (err) {
    return <BackendDown error={String(err)} />;
  }

  const tsByMetric = { snowpack: snow, precip: precip, reservoir };

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500">
            Predictive Water Intelligence · North Central Valley
          </div>
          <h1 className="mt-1 text-3xl font-semibold text-slate-100">Reservoir Network</h1>
          <div className="mt-1 text-xs text-slate-500">
            Hover any marker for live storage and risk. Detailed view below is anchored on{" "}
            {snapshot.basin.name}.
          </div>
        </div>
        <FreshnessLine
          csv={snapshot.data_freshness.csv_latest}
          cdec={snapshot.data_freshness.cdec_live}
          cdecStatus={snapshot.data_freshness.cdec_status}
        />
      </header>

      <section className="mb-8">
        <MapPanel reservoirs={reservoirList.reservoirs} />
      </section>

      <section className="mb-8">
        <ZipReleaseProbe />
      </section>

      <section className="mb-8">
        <ReleasePanel reservoirs={reservoirList.reservoirs} />
      </section>

      <section className="mb-4 flex flex-wrap items-end justify-between gap-3 border-t border-slate-800 pt-6">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500">
            {snapshot.basin.watershed}
          </div>
          <h2 className="mt-1 text-2xl font-semibold text-slate-100">{snapshot.basin.name}</h2>
          <div className="mt-1 text-xs text-slate-500">
            CDEC station {snapshot.basin.cdec_station} · capacity{" "}
            {(snapshot.basin.capacity_af / 1_000_000).toFixed(2)}M AF
          </div>
        </div>
        <RiskBadge level={snapshot.risk.level} score={snapshot.risk.score} />
      </section>

      {snapshot.risk.explanations.length > 0 && (
        <div className="mb-4 rounded-xl border border-slate-800 bg-slate-900/40 p-3 text-sm text-slate-300">
          <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">Why this score</div>
          <ul className="ml-4 list-disc space-y-1">
            {snapshot.risk.explanations.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {METRICS.map((m) => (
          <MetricCard key={m} title={METRIC_LABELS[m]} unit={UNITS[m]} payload={snapshot.metrics[m]} />
        ))}
      </section>

      <section className="mt-6 grid grid-cols-1 gap-3 lg:grid-cols-3">
        {METRICS.map((m) => (
          <TrendChart
            key={m}
            title={METRIC_LABELS[m]}
            points={tsByMetric[m].points}
            unit={UNITS[m]}
          />
        ))}
      </section>

      <section className="mt-6 grid grid-cols-1 gap-3 lg:grid-cols-3">
        {METRICS.map((m) => (
          <ForecastStrip
            key={m}
            title={METRIC_LABELS[m]}
            unit={UNITS[m]}
            points={forecast.metrics[m].monthly}
            sevenDay={forecast.metrics[m].seven_day}
            latest={forecast.metrics[m].latest}
          />
        ))}
      </section>

      <section className="mt-6">
        <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-slate-400">
          Alerts ({snapshot.alerts.length})
        </h2>
        <AlertsList alerts={snapshot.alerts} />
      </section>

      <footer className="mt-10 text-[11px] text-slate-600">
        Sources: CDEC sensor 15 (live reservoir storage) · NASA POWER daily-point + monthly
        climatology · NOAA NWS gridpoint QPF · `data/challenge.csv` (historical monthly
        snapshots). Forecast: seasonal-naive baseline. Release likelihood is a transparent
        rule-based heuristic and is not a substitute for DWR/USBR notices.
      </footer>
    </main>
  );
}

function FreshnessLine({
  csv,
  cdec,
  cdecStatus,
}: {
  csv: string;
  cdec: string | null;
  cdecStatus: "ok" | "unavailable";
}) {
  return (
    <div className="text-right text-xs text-slate-500">
      <div>
        CSV: {csv.slice(0, 10)}
        {" · "}
        CDEC:{" "}
        {cdecStatus === "ok" && cdec ? new Date(cdec).toISOString().slice(0, 16) + "Z" : "unavailable"}
      </div>
    </div>
  );
}

function BackendDown({ error }: { error: string }) {
  return (
    <main className="mx-auto max-w-2xl p-10 text-slate-300">
      <h1 className="text-2xl font-semibold">Backend unreachable</h1>
      <p className="mt-3 text-sm text-slate-400">
        The FastAPI sidecar at <code>{process.env.NEXT_PUBLIC_API_BASE}</code> didn&apos;t answer.
        Start it with:
      </p>
      <pre className="mt-3 rounded bg-slate-900 p-3 text-xs">
        cd backend{"\n"}uv run uvicorn app.main:app --reload --port 8000
      </pre>
      <p className="mt-4 text-xs text-rose-400">{error}</p>
    </main>
  );
}

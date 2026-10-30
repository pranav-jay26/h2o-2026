// Per-basin release-anticipation watch list. Shows the inputs that drove each
// reservoir's release-likelihood level, sorted with elevated first.

import {
  RELEASE_COLORS,
  type ReleaseLevel,
  type ReservoirMarker,
} from "@/lib/api";

const LEVEL_ORDER: Record<ReleaseLevel, number> = { elevated: 0, watch: 1, normal: 2 };
const LEVEL_LABEL: Record<ReleaseLevel, string> = {
  elevated: "Elevated",
  watch: "Watch",
  normal: "Normal",
};

export function ReleasePanel({ reservoirs }: { reservoirs: ReservoirMarker[] }) {
  const sorted = [...reservoirs].sort(
    (a, b) => LEVEL_ORDER[a.release_risk.level] - LEVEL_ORDER[b.release_risk.level],
  );
  const elevated = sorted.filter((r) => r.release_risk.level === "elevated");

  return (
    <section>
      <header className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium uppercase tracking-wide text-slate-300">
            Release Anticipation
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Composite of reservoir storage, NASA POWER observed precipitation vs. climatology,
            and NOAA NWS 7-day quantitative precipitation + temperature forecast. Advisory only —
            not a substitute for DWR/USBR notices.
          </p>
        </div>
        <div className="text-xs text-slate-500">
          {elevated.length === 0
            ? "No reservoirs in elevated state"
            : `${elevated.length} reservoir${elevated.length > 1 ? "s" : ""} in elevated state`}
        </div>
      </header>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {sorted.map((r) => (
          <ReleaseCard key={r.id} reservoir={r} />
        ))}
      </div>
    </section>
  );
}

function ReleaseCard({ reservoir: r }: { reservoir: ReservoirMarker }) {
  const level = r.release_risk.level;
  const color = RELEASE_COLORS[level];
  return (
    <div
      className="rounded-xl border bg-slate-900/40 p-4"
      style={{ borderColor: `${color}55` }}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-500">{r.watershed}</div>
          <div className="mt-0.5 text-base font-semibold text-slate-100">{r.name}</div>
        </div>
        <div
          className="rounded-md px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide"
          style={{ background: `${color}22`, color, border: `1px solid ${color}55` }}
        >
          {LEVEL_LABEL[level]}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
        <Stat
          label="Storage"
          value={r.current.percent_capacity != null ? `${r.current.percent_capacity.toFixed(0)}%` : "—"}
        />
        <Stat
          label="30d precip"
          value={
            r.met?.pct_of_normal_precip != null
              ? `${r.met.pct_of_normal_precip.toFixed(0)}% norm`
              : "—"
          }
          tone={
            r.met?.pct_of_normal_precip != null && r.met.pct_of_normal_precip >= 130
              ? "wet"
              : "neutral"
          }
        />
        <Stat
          label="7d QPF"
          value={
            r.forecast?.next_7d_total_in != null
              ? `${r.forecast.next_7d_total_in.toFixed(2)}″`
              : "—"
          }
          tone={
            r.forecast?.next_7d_total_in != null && r.forecast.next_7d_total_in >= 1.5
              ? "wet"
              : "neutral"
          }
        />
      </div>

      <p className="mt-3 text-xs leading-relaxed text-slate-400">
        {r.release_risk.summary}
      </p>

      {r.release_risk.drivers.length > 0 && (
        <ul className="mt-3 space-y-1">
          {r.release_risk.drivers.map((d) => (
            <li key={d.key} className="flex items-start gap-1.5 text-[11px] text-slate-400">
              <span
                className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full"
                style={{
                  background:
                    d.weight === "high" ? color : d.weight === "medium" ? "#94a3b8" : "#475569",
                }}
              />
              <span>{d.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "wet";
}) {
  return (
    <div>
      <div className="text-slate-500">{label}</div>
      <div className={tone === "wet" ? "text-sky-300" : "text-slate-200"}>{value}</div>
    </div>
  );
}

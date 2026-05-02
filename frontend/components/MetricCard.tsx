import type { MetricPayload } from "@/lib/api";

const TONE = {
  good: "border-emerald-500/40 text-emerald-300",
  ok: "border-slate-700 text-slate-200",
  warn: "border-amber-500/40 text-amber-300",
  bad: "border-rose-500/40 text-rose-300",
} as const;

function toneFor(p: number): keyof typeof TONE {
  if (p < 10) return "bad";
  if (p < 25) return "warn";
  if (p > 75) return "good";
  return "ok";
}

export function MetricCard({
  title,
  unit,
  payload,
}: {
  title: string;
  unit: string;
  payload: MetricPayload;
}) {
  const tone = TONE[toneFor(payload.percentile)];
  return (
    <div className={`rounded-xl border bg-slate-900/40 p-4 ${tone}`}>
      <div className="text-xs uppercase tracking-wide text-slate-400">{title}</div>
      <div className="mt-2 flex items-baseline gap-2">
        <div className="text-3xl font-semibold">{payload.value.toFixed(1)}</div>
        <div className="text-xs text-slate-400">{unit}</div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div>
          <div className="text-slate-500">vs. month avg</div>
          <div>{payload.anomaly >= 0 ? "+" : ""}{payload.anomaly.toFixed(1)}</div>
        </div>
        <div>
          <div className="text-slate-500">percentile</div>
          <div>p{Math.round(payload.percentile)}</div>
        </div>
      </div>
      <div className="mt-3 border-t border-slate-800 pt-2 text-[11px] text-slate-500">
        {payload.source} · {fmtDate(payload.as_of)}
      </div>
    </div>
  );
}

function fmtDate(s: string): string {
  try {
    const d = new Date(s);
    if (isNaN(d.getTime())) return s;
    return d.toISOString().slice(0, 10);
  } catch {
    return s;
  }
}

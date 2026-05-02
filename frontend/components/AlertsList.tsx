import type { Alert } from "@/lib/api";

const LEVEL = {
  red: { dot: "#ef4444", label: "High", border: "border-rose-500/40" },
  amber: { dot: "#f59e0b", label: "Watch", border: "border-amber-500/40" },
  green: { dot: "#10b981", label: "Info", border: "border-emerald-500/40" },
} as const;

export function AlertsList({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-400">
        No alerts triggered. All monitored thresholds are within normal bands.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {alerts.map((a, i) => {
        const tone = LEVEL[a.level] ?? LEVEL.amber;
        return (
          <div
            key={i}
            className={`rounded-xl border bg-slate-900/40 p-4 ${tone.border}`}
          >
            <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
              <span className="h-2 w-2 rounded-full" style={{ background: tone.dot }} />
              <span>{tone.label}</span>
              <span>·</span>
              <span>{a.metric}</span>
              <span>·</span>
              <span>{a.window}</span>
            </div>
            <div className="mt-1 text-sm text-slate-200">{a.why}</div>
            <div className="mt-2 text-xs text-slate-400">
              <span className="text-slate-500">Action:</span> {a.action}
            </div>
          </div>
        );
      })}
    </div>
  );
}

import { RISK_COLORS, type RiskLevel } from "@/lib/api";

const LABELS: Record<RiskLevel, string> = {
  green: "Low risk",
  amber: "Watch",
  red: "High risk",
};

export function RiskBadge({ level, score }: { level: RiskLevel; score: number }) {
  const color = RISK_COLORS[level];
  return (
    <div
      className="inline-flex items-center gap-3 rounded-2xl border px-5 py-3 text-lg font-semibold"
      style={{ borderColor: color, color }}
    >
      <span className="h-3 w-3 rounded-full" style={{ background: color }} />
      <span>{LABELS[level]}</span>
      <span className="text-base font-normal text-slate-400">score {score}</span>
    </div>
  );
}

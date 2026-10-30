"use client";

// Client wrapper that lazy-loads ReservoirMap (and plotly.js with it) on the
// browser only. Keeps the heavy bundle off the SSR pass.

import dynamic from "next/dynamic";

import { RISK_COLORS, type ReservoirMarker } from "@/lib/api";

const ReservoirMap = dynamic(() => import("./ReservoirMap"), {
  ssr: false,
  loading: () => (
    <div className="grid h-[480px] w-full place-items-center rounded-xl border border-slate-800 bg-slate-900/40 text-sm text-slate-500">
      Loading map…
    </div>
  ),
});

export default function MapPanel({ reservoirs }: { reservoirs: ReservoirMarker[] }) {
  return (
    <div className="space-y-3">
      <ReservoirMap reservoirs={reservoirs} />
      <Legend />
    </div>
  );
}

function Legend() {
  const items: { label: string; color: string }[] = [
    { label: "Low water-stress risk", color: RISK_COLORS.green },
    { label: "Watch", color: RISK_COLORS.amber },
    { label: "High water-stress risk", color: RISK_COLORS.red },
    { label: "No data", color: "#64748b" },
  ];
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
      {items.map((i) => (
        <div key={i.label} className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: i.color }} />
          <span>{i.label}</span>
        </div>
      ))}
      <span className="text-slate-600">· marker size = reservoir capacity · hover for release likelihood</span>
    </div>
  );
}

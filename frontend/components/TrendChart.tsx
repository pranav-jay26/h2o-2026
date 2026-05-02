"use client";

import {
  Area,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { TimeseriesPoint } from "@/lib/api";

export function TrendChart({
  title,
  points,
  unit,
}: {
  title: string;
  points: TimeseriesPoint[];
  unit: string;
}) {
  // Recharts stacks area shapes from y0 → y0+y1; precompute the band sizes.
  const data = points.map((p) => ({
    ...p,
    band_lower: p.p10,
    band_inner: Math.max(0, p.p25 - p.p10),
    band_outer: Math.max(0, p.p90 - p.p25),
  }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="text-xs text-slate-500">historical p10–p90 band</div>
      </div>
      <div className="h-56 w-full">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="date"
              tickFormatter={(s: string) => s.slice(0, 7)}
              minTickGap={40}
              stroke="#475569"
              fontSize={11}
            />
            <YAxis stroke="#475569" fontSize={11} width={36} />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }}
              labelStyle={{ color: "#cbd5e1" }}
              formatter={(value: unknown, key: string) => {
                if (key === "band_lower" || key === "band_inner" || key === "band_outer") return [null, ""];
                if (typeof value === "number") return [value.toFixed(1) + " " + unit, key];
                return [String(value), key];
              }}
            />
            <Legend
              wrapperStyle={{ color: "#94a3b8", fontSize: 11 }}
              payload={[
                { value: "value", type: "line", color: "#38bdf8" },
                { value: "month median", type: "line", color: "#94a3b8" },
                { value: "p10–p90", type: "rect", color: "#1e3a8a" },
              ]}
            />
            <Area
              type="monotone"
              dataKey="band_lower"
              stackId="band"
              stroke="none"
              fill="transparent"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="band_inner"
              stackId="band"
              stroke="none"
              fill="#1e3a8a"
              fillOpacity={0.35}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="band_outer"
              stackId="band"
              stroke="none"
              fill="#1e3a8a"
              fillOpacity={0.2}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="month_mean"
              stroke="#94a3b8"
              strokeDasharray="3 3"
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

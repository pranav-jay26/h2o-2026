"use client";

import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ForecastPoint } from "@/lib/api";

export function ForecastStrip({
  title,
  unit,
  points,
  sevenDay,
  latest,
}: {
  title: string;
  unit: string;
  points: ForecastPoint[];
  sevenDay: number;
  latest: number;
}) {
  const data = points.map((p) => ({
    date: p.date,
    mean: p.mean,
    band_lo: p.lower,
    band_size: Math.max(0, p.upper - p.lower),
  }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-medium text-slate-200">{title} — forecast</div>
        <div className="flex gap-3 text-xs text-slate-400">
          <span>now {latest.toFixed(1)}</span>
          <span>7d {sevenDay.toFixed(1)}</span>
        </div>
      </div>
      <div className="h-40 w-full">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="date"
              tickFormatter={(s: string) => s.slice(0, 7)}
              stroke="#475569"
              fontSize={11}
            />
            <YAxis stroke="#475569" fontSize={11} width={36} />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }}
              formatter={(value: unknown, key: string) => {
                if (key === "band_lo" || key === "band_size") return [null, ""];
                if (typeof value === "number") return [value.toFixed(1) + " " + unit, key];
                return [String(value), key];
              }}
            />
            <Area
              type="monotone"
              dataKey="band_lo"
              stackId="b"
              stroke="none"
              fill="transparent"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="band_size"
              stackId="b"
              stroke="none"
              fill="#0ea5e9"
              fillOpacity={0.18}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="mean"
              stroke="#0ea5e9"
              strokeWidth={2}
              dot={{ r: 3, fill: "#0ea5e9" }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

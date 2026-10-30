"use client";

// Plotly + Mapbox map of north Central Valley reservoirs.
//
// Uses plotly.js-dist-min imperatively rather than `react-plotly.js`, because
// the latter (v2.6.0) hasn't been updated for React 19 and silently renders
// nothing under it. Loaded dynamically (ssr:false) by MapPanel because plotly.js
// touches `window` at module load.

import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

import { RISK_COLORS, type ReservoirMarker } from "@/lib/api";

const UNKNOWN_COLOR = "#64748b";

function markerColor(level: ReservoirMarker["risk_level"]): string {
  if (level === "unknown") return UNKNOWN_COLOR;
  return RISK_COLORS[level];
}

function markerSize(capacity_af: number): number {
  // Scale by sqrt of capacity so a 4× larger reservoir is 2× larger on screen.
  return Math.max(14, Math.min(46, Math.round(Math.sqrt(capacity_af) / 50)));
}

export default function ReservoirMap({ reservoirs }: { reservoirs: ReservoirMarker[] }) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const trace = {
      type: "scattermapbox",
      mode: "markers",
      lat: reservoirs.map((r) => r.lat),
      lon: reservoirs.map((r) => r.lon),
      marker: {
        size: reservoirs.map((r) => markerSize(r.capacity_af)),
        color: reservoirs.map((r) => markerColor(r.risk_level)),
        opacity: 0.9,
        allowoverlap: true,
      },
      text: reservoirs.map((r) => r.name),
      customdata: reservoirs.map((r) => [
        r.watershed,
        r.cdec_station,
        r.current.percent_capacity != null ? r.current.percent_capacity.toFixed(1) : "—",
        r.current.storage_af != null ? Math.round(r.current.storage_af).toLocaleString() : "—",
        Math.round(r.capacity_af).toLocaleString(),
        r.current.as_of ?? "—",
        r.risk_level.toUpperCase(),
        r.release_risk.level.toUpperCase(),
        r.met?.pct_of_normal_precip != null ? `${r.met.pct_of_normal_precip.toFixed(0)}%` : "—",
        r.forecast?.next_7d_total_in != null ? `${r.forecast.next_7d_total_in.toFixed(2)}"` : "—",
        r.met?.temp_anomaly_c != null
          ? `${r.met.temp_anomaly_c >= 0 ? "+" : ""}${r.met.temp_anomaly_c.toFixed(1)}°C`
          : "—",
      ]),
      hovertemplate:
        "<b>%{text}</b><br>" +
        "%{customdata[0]} · CDEC %{customdata[1]}<br>" +
        "<br><b>Storage</b>: %{customdata[2]}% (%{customdata[3]} / %{customdata[4]} AF)<br>" +
        "Stress risk: <b>%{customdata[6]}</b><br>" +
        "<br><b>Release likelihood: %{customdata[7]}</b><br>" +
        "30-day precip: %{customdata[8]} of normal<br>" +
        "7-day forecast: %{customdata[9]}<br>" +
        "Recent temp anomaly: %{customdata[10]}<br>" +
        "<br>Updated: %{customdata[5]}" +
        "<extra></extra>",
      hoverlabel: {
        bgcolor: "#0f172a",
        bordercolor: "#334155",
        font: { color: "#e2e8f0", size: 12 },
        align: "left",
      },
    };

    const layout = {
      autosize: true,
      mapbox: {
        style: "carto-darkmatter",
        center: { lat: 39.7, lon: -121.7 },
        zoom: 6.4,
      },
      margin: { l: 0, r: 0, t: 0, b: 0 },
      paper_bgcolor: "#0b1220",
      plot_bgcolor: "#0b1220",
      font: { color: "#cbd5e1" },
      showlegend: false,
      uirevision: "reservoir-map",
    };

    const config = {
      displayModeBar: false,
      scrollZoom: true,
      responsive: true,
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Plotly.newPlot(node, [trace as any], layout as any, config as any);

    const handleResize = () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (Plotly as any).Plots.resize(node);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (Plotly as any).purge(node);
    };
  }, [reservoirs]);

  return (
    <div
      ref={ref}
      className="h-[480px] w-full overflow-hidden rounded-xl border border-slate-800"
    />
  );
}

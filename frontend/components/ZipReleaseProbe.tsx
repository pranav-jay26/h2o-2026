"use client";

import { useEffect, useState, type FormEvent } from "react";

import {
  api,
  type ReleaseEstimate,
  type Resolution,
  type UserAreaLevel,
} from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const LEVEL_STYLE: Record<UserAreaLevel, { color: string; label: string }> = {
  likely: { color: "#ef4444", label: "Likely affected" },
  possible: { color: "#f59e0b", label: "Possibly affected" },
  unlikely: { color: "#10b981", label: "Unlikely affected" },
  out_of_zone: { color: "#64748b", label: "Outside impact zone" },
};

const ZIP_RE = /^\d{5}$/;
const CITY_STATE_RE = /^[A-Za-zÀ-ÿ.\-' ]{2,},\s*[A-Za-z]{2}$/;

function isValidQuery(q: string): boolean {
  const t = q.trim();
  return ZIP_RE.test(t) || CITY_STATE_RE.test(t);
}

export function ZipReleaseProbe() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReleaseEstimate | null>(null);
  const [voiceTriggered, setVoiceTriggered] = useState(false);

  // Mirror voice-agent (MCP) queries onto the dashboard via SSE.
  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/events`);
    es.onmessage = (msg) => {
      try {
        const evt = JSON.parse(msg.data) as
          | { type: "release_estimate"; query: string; result: ReleaseEstimate }
          | { type: string };
        if (evt.type === "release_estimate" && "result" in evt) {
          setQuery(evt.query);
          setResult(evt.result);
          setError(null);
          setLoading(false);
          setVoiceTriggered(true);
          window.setTimeout(() => setVoiceTriggered(false), 4000);
        }
      } catch {
        // ignore malformed events
      }
    };
    return () => es.close();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setVoiceTriggered(false);
    const t = query.trim();
    if (!isValidQuery(t)) {
      setError("Enter a 5-digit ZIP or 'City, ST' (e.g. Sacramento, CA).");
      return;
    }
    setLoading(true);
    try {
      const r = await api.releaseEstimate(t);
      setResult(r);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Lookup failed.";
      setError(msg.includes("404") ? "Couldn't find that location. Check the spelling or try a ZIP." : msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <header className="mb-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-slate-300">
          Check your area
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Enter a ZIP code <span className="text-slate-600">(96019)</span> or city + state{" "}
          <span className="text-slate-600">(Sacramento, CA)</span>. We&apos;ll estimate how
          likely a strategic release from the nearest reservoir would affect you, based on
          current storage, NASA POWER precip, and NOAA forecast.
        </p>
      </header>

      <form onSubmit={onSubmit} className="flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="ZIP or City, ST"
          className="w-72 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !isValidQuery(query)}
          className="rounded-lg border border-sky-700 bg-sky-700/30 px-4 py-2 text-sm font-medium text-sky-200 hover:bg-sky-700/50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Checking…" : "Check release likelihood"}
        </button>
        {voiceTriggered && (
          <span className="inline-flex items-center gap-1.5 rounded-md border border-sky-700/50 bg-sky-900/40 px-2 py-1 text-[11px] font-medium text-sky-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-sky-400" />
            Triggered by voice agent
          </span>
        )}
        {error && <span className="text-xs text-rose-400">{error}</span>}
      </form>

      {result && <ResultTile result={result} />}
    </section>
  );
}

function locationLabel(r: Resolution): string {
  if (r.kind === "city" && r.city && r.state_id) {
    return `${r.city}, ${r.state_id}`;
  }
  if (r.city && r.state_id) {
    return `${r.zip} · ${r.city}, ${r.state_id}`;
  }
  return r.zip;
}

function ResultTile({ result }: { result: ReleaseEstimate }) {
  const style = LEVEL_STYLE[result.user_level];
  const res = result.resolution;
  const subtitle =
    res.kind === "city"
      ? `${res.matched_zip_count} ZIP${res.matched_zip_count === 1 ? "" : "s"}, pop. ${res.population?.toLocaleString() ?? "—"}`
      : `pop. ${res.population?.toLocaleString() ?? "—"}`;

  return (
    <div
      className="mt-4 rounded-xl border bg-slate-900/40 p-5"
      style={{ borderColor: `${style.color}55` }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-500">
            {locationLabel(res)} · {res.lat.toFixed(3)}, {res.lon.toFixed(3)} · {subtitle}
          </div>
          <div className="mt-1 text-base font-semibold text-slate-100">
            {result.nearest.name}{" "}
            <span className="text-sm font-normal text-slate-500">
              · {result.nearest.watershed} · {result.nearest.distance_mi.toFixed(0)} mi away
            </span>
          </div>
        </div>
        <div
          className="rounded-md px-3 py-1 text-xs font-medium uppercase tracking-wide"
          style={{ background: `${style.color}22`, color: style.color, border: `1px solid ${style.color}55` }}
        >
          {style.label}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
        <Stat
          label="Reservoir release likelihood"
          value={result.nearest.release_level.toUpperCase()}
          sub={`score ${result.nearest.release_score}`}
        />
        <Stat
          label="Distance attenuation"
          value={`${Math.round(result.distance_factor * 100)}%`}
          sub={`0 at ${result.thresholds.far_miles.toFixed(0)} mi`}
        />
        <Stat
          label="Local probability score"
          value={`${result.user_score.toFixed(0)} / 100`}
          sub={style.label.toLowerCase()}
        />
      </div>

      <p className="mt-4 text-sm leading-relaxed text-slate-300">{result.summary}</p>

      {result.nearest.drivers.length > 0 && result.user_level !== "out_of_zone" && (
        <div className="mt-4">
          <div className="mb-1 text-[11px] uppercase tracking-wide text-slate-500">
            Why the nearest reservoir is on watch
          </div>
          <ul className="space-y-1">
            {result.nearest.drivers.map((d) => (
              <li key={d.key} className="flex items-start gap-1.5 text-xs text-slate-400">
                <span
                  className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{
                    background:
                      d.weight === "high"
                        ? style.color
                        : d.weight === "medium"
                          ? "#94a3b8"
                          : "#475569",
                  }}
                />
                <span>{d.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.nearby.length > 1 && (
        <div className="mt-4 border-t border-slate-800 pt-3">
          <div className="mb-1 text-[11px] uppercase tracking-wide text-slate-500">
            Other nearby reservoirs
          </div>
          <ul className="space-y-1 text-xs text-slate-400">
            {result.nearby.slice(1).map((n) => (
              <li key={n.id}>
                {n.name} · {n.watershed} · {n.distance_mi.toFixed(0)} mi · release {n.release_level}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-slate-500">{label}</div>
      <div className="mt-0.5 text-base font-semibold text-slate-100">{value}</div>
      {sub && <div className="text-[11px] text-slate-500">{sub}</div>}
    </div>
  );
}

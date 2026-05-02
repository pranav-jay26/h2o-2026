# Frontend — H2O Predictive Water Intelligence

Next.js 15 dashboard, server-rendered, talking to the FastAPI sidecar.

## Run

```bash
cd frontend
npm install
npm run dev
```

Defaults to <http://localhost:3000>. The backend is expected at
<http://localhost:8000> — override with `NEXT_PUBLIC_API_BASE` if needed.

## Layout

- `app/page.tsx` — single dashboard route. Server component; fetches snapshot,
  forecast, and timeseries in parallel, then composes the page.
- `components/RiskBadge.tsx` — green/amber/red badge.
- `components/MetricCard.tsx` — current value, anomaly, percentile, source.
- `components/TrendChart.tsx` — historical line + p10–p90 band + month-of-year median.
- `components/ForecastStrip.tsx` — 6-month forecast with uncertainty band.
- `components/AlertsList.tsx` — triggered alerts with `why` + `action`.
- `lib/api.ts` — typed client for the sidecar; everything else imports from here.

## Future hooks

- Add basin selector once `/api/basins` returns more than Shasta.
- Wire `POST /api/scenarios/run` to a "what-if" panel.
- Swap `force-dynamic` for ISR with revalidation when data sources stabilize.

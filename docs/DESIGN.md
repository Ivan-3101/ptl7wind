# Design: UK Wind Forecast Monitor

Status: draft v1 · Owner: Ivan Dsouza

## 1. Problem

A UK energy supplier buys power in the **GB day-ahead market**. Bids for every hour of
delivery day **D** must be submitted before **gate closure on D-1** (~09:20 UK, EPEX
auction). To decide how much to buy, the team needs to know how much **wind** will be
generated, which they only know through **forecasts**.

The app answers two questions:

1. **What did the wind forecast say when I had to decide?**
   The latest forecast *published before gate closure*, not the latest that exists today.
2. **How accurate are these forecasts?**
   Size and direction of the error, so the team can buy a safety margin.

## 2. Scope

| In scope | Out of scope |
|---|---|
| National GB wind only | Solar, demand, prices |
| Elexon BMRS `FUELHH` (actuals) and `WINDFOR` (forecasts) only | Any other data source |
| Purchase decisions made **1–31 Jan 2026** → delivery days **2 Jan – 1 Feb 2026** | Live / real-time data |
| Forecasts published 30 Dec 2025 – 1 Feb 2026 (all forecasts that can be selected for those delivery days in either mode) | |

## 3. Data

| Dataset | Meaning | Resolution | Fields used |
|---|---|---|---|
| `FUELHH` (fuelType = WIND) | Actual wind generation | 30 min | `startTime`, `generation` (MW) |
| `WINDFOR` | Wind forecasts | 1 hour | `publishTime`, `startTime`, `generation` (MW) |

Observed facts (January 2026):

- Forecasts are published **8×/day** at 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30,
  22:30 UTC (plus an occasional extra publish). The code does **not** hard-code this
  schedule; it uses `publishTime` from the data.
- Each forecast covers ~3 days, so every target hour is forecast ~20 times.
- Some forecast rows have `startTime` ≤ `publishTime` (past hours). These are not
  forecasts and are dropped.
- Actuals are complete: no gaps, no duplicates.

## 4. Key definitions and assumptions

| Term | Definition |
|---|---|
| Target time | The hour being forecast (`startTime`) |
| Publish time | When the forecast was made (`publishTime`) |
| Horizon | Target time − publish time, in hours |
| Error | Forecast − actual (MW). Positive = forecast too high |

Assumptions (each one is a deliberate choice; see section 9 for alternatives):

- **A1. Compare on the hour.** Forecasts are hourly, so each hourly forecast is compared with
  the actual half-hour starting at the same time (14:00 vs 14:00). The :30 actuals are
  shown on charts but not scored. No interpolated forecast values are created.
- **A2. Time zone.** All times are UTC. In January UK time = UTC, so no daylight-saving
  handling is needed for this dataset.
- **A3. Delivery day** = calendar day 00:00–23:59 UTC. (Some exchanges use 23:00–23:00;
  this only moves one hour at the day boundary.)
- **A4. Gate closure** defaults to **09:20 on D-1** (EPEX GB day-ahead auction). The UI
  offers presets **09:20 (EPEX)** and **09:50 (N2EX)** plus a custom time. The earlier time
  is the safe default: a forecast available at 09:20 is also available at 09:50, but not
  the other way round, so an early default can never cause look-ahead.

## 5. Core rule: picking the forecast

There is one rule, used in two ways:

> For each target hour, use the **most recent forecast whose publish time ≤ cutoff**.

| Mode | Cutoff | Used for |
|---|---|---|
| **Decision mode** | Gate closure on D-1 (e.g. Jan 9 09:20 for all hours of Jan 10) | Purpose 1: "what did I know when I bid?" and accuracy of those exact forecasts |
| **Horizon mode** | Target time − *h* hours (h = 0…48) | Purpose 2: "how does accuracy change with lead time?" |

```
target: Jan 10 14:00            gate: Jan 9 09:20
  Jan 9 04:30  ✓ before gate
  Jan 9 07:30  ✓ before gate  ← selected (latest usable)
  Jan 9 09:30  ✗ after gate (look-ahead, excluded)
  Jan 10 11:30 ✗ after gate
```

Using any forecast published after the cutoff would be **look-ahead bias**: scoring the
team with information they could not have had.

Implementation: `pandas.merge_asof(actuals, forecasts, left_on=cutoff, right_on=publishTime,
by=target, direction="backward")`, which is a sorted "latest row at or before" join done in
one vectorised call.

## 6. Metrics

Computed over the selected (forecast, actual) pairs:

| Metric | Formula | Why it is included |
|---|---|---|
| Bias | mean(error) | Shows a systematic over/under-forecast the team can correct for |
| MAE | mean(\|error\|) | Typical miss in MW; easiest to explain |
| RMSE | √mean(error²) | Standard in forecasting; penalises big misses |
| nMAE | MAE / mean(actual) | Size of the error relative to typical output |
| Over-forecast share | share of hours with error > 0 | Shows whether the bias is occasional or systematic |
| Error percentiles | P10, P50, P90 of error | Range of misses → basis for a safety margin |
| Error histogram | hours per 500 MW error bin (empty bins included as 0) | Shape of the error distribution |
| Error by horizon | MAE and bias per h | How fast accuracy degrades with lead time |
| Error by hour of day | MAE and bias per hour | Whether some hours are harder to predict |
| Suggested safety margin | P90 of error (decision mode) | Turns the percentiles into one actionable number: "plan for wind X MW below forecast to be covered 90% of the time" |
| Gate comparison | MAE at 09:20 gate vs 09:50 gate | Value of the later auction's fresher forecast |

### Experimental: bias-corrected forecast

Because most of the error is a steady over-forecast, a simple correction is backtested:

> corrected forecast = official forecast − mean daily error over the previous 14 complete days

- **No look-ahead.** Bids for D are due on the morning of D-1, when D-1 is incomplete, so
  the window is D-15 … D-2, using the decision-mode error of each of those days.
- **Available from 17 Jan** (needs 14 complete days; the snapshot starts 2 Jan).
- **Backtest (09:20 gate, 17 Jan – 1 Feb, same hours for both):** MAE 2,115 → 1,265 MW
  (−40%), safety margin 3,981 → 2,614 MW; better on 13 of 16 days.
- Variants tested and rejected: a 7-day window (−34%) and per-hour-of-day corrections
  (−29% / −37%; only 7–14 samples per hour, so too noisy).
- **Caveats:** 16 days of one month; the corrected forecast is sometimes too low
  (P10 −109 → −1,580 MW), i.e. over-buying risk. Shown in the UI as experimental.

**Decision-mode metrics are the headline.** The client's real question is "how wrong was
the forecast I actually used?", so the accuracy page leads with decision mode; horizon
mode is supporting analysis that explains *why*.

MAPE is **not** used: when wind is very low, dividing by a small actual blows the percentage
up and makes it misleading.

## 7. Architecture

```
                 Browser
                    │
        ┌───────────┴────────────┐   one Vercel project
        │ React SPA (static)     │   frontend/  Vite + React + TS + Recharts
        │   /api/* requests  ────┼──► api/index.py → FastAPI app (Python serverless)
        └────────────────────────┘          │
                                     backend/app/ (selection + metrics, pandas)
                                            │
                                     data/*.csv  (January snapshot, loaded once)

  scripts/fetch_data.py  ── run manually ──► Elexon BMRS API ──► data/*.csv
```

| Layer | Choice | Reason |
|---|---|---|
| Frontend | React + Vite + TypeScript | Required React; Vite = fast standard tooling; TS catches API-shape bugs |
| Charts | Recharts | React-native components, enough for line/bar/area charts |
| Backend | FastAPI | Required Python; typed request/response models; auto API docs at `/docs` |
| Analysis | pandas | `merge_asof` does the core rule in one call; groupby for metrics |
| Data | CSV snapshot in repo | Historical data never changes; demo is fast and does not depend on Elexon uptime |
| Hosting | Vercel (static site + Python function) | Required; one deploy for both parts |
| Local run | Docker Compose (backend + frontend/nginx) | Required Docker; one-command local start |

### Data flow
1. `scripts/fetch_data.py` downloads `FUELHH` (WIND) and `WINDFOR` for the January
   window and writes `data/actuals.csv` and `data/forecasts.csv`.
2. On the first request the backend loads both CSVs into memory and caches them.
3. Each API call runs the selection rule + metrics on the in-memory data (~22k rows,
   milliseconds).

## 8. API

| Endpoint | Params | Returns |
|---|---|---|
| `GET /api/meta` | none | Available date range, default gate time, forecast publish times |
| `GET /api/day-ahead` | `date`, `gate` | Hourly series for one delivery day: actual (incl. half-hours), selected forecast, its publish time, error, bias-corrected forecast (when history allows) |
| `GET /api/accuracy/bias-correction` | `gate`, `start`, `end` | Backtest: official vs bias-corrected summary on the same hours |
| `GET /api/accuracy` | `mode` (`decision`/`horizon`), `gate` or `horizon`, `start`, `end` | Summary metrics, safety margin, error distribution, error by hour of day |
| `GET /api/accuracy/by-horizon` | `start`, `end` | MAE and bias for h = 0…48 |

## 9. Decisions and rejected alternatives

| Decision | Rejected alternative | Why |
|---|---|---|
| Compare on the hour (A1) | Interpolate forecast to :30 | Would create values the forecaster never published |
| | Average two half-hour actuals | Defensible, but changes the actual series from what BMRS shows |
| CSV snapshot | Call Elexon live per request | Slower, rate/uptime risk during review; the data is historical |
| pandas | Plain Python loops | `merge_asof`/`groupby` are clearer and well tested |
| nMAE | MAPE | MAPE explodes at low wind |
| Single Vercel project | Separate backend host (e.g. Heroku) | One URL, no CORS setup, one deploy |

## 10. Testing

- **Unit (pytest):** selection rule on tiny hand-built data, e.g. a forecast published 1
  minute after the gate must not be selected, and past-target rows are dropped; each metric
  checked against hand-calculated values.
- **Reference implementation:** the selection rule re-written with plain loops (no pandas)
  must match the pandas pipeline on the full month for several gates and horizons.
  Verified to fail when the rule is deliberately broken (`direction="nearest"`).
- **Bias correction:** the window is exactly D-15 … D-2; changing D-1 or later never
  changes D's correction; no correction without a full window.
- **API (pytest + FastAPI TestClient):** each endpoint returns the right shape; bad
  inputs (date outside range, bad gate) return 4xx.
- **Frontend:** TypeScript type-check and production build.
- **CI:** GitHub Actions runs all of the above on every push.

## 11. Known limitations

- The average forecast is **~1.5–1.8 GW higher** than actuals in January. Possible causes
  (wind curtailment, different wind-farm coverage between the two datasets) cannot be
  confirmed using only these two datasets, so they are presented as hypotheses.
- January only. Extending to other months needs daylight-saving handling (UK time ≠ UTC
  from late March to late October), which A2 avoids for now.
- Hourly scoring only (A1).

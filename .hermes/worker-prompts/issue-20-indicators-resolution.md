# Issue 20: Indicator + resolution controls (global toggle, no re-fetch)

## Problem

Currently:
- Charts are static after backtest completes
- Changing interval/indicators requires a new `/api/orb` fetch and full re-render
- Users want to toggle SMA/EMA/VWAP indicators on/off across ALL 20 cards at once
- Users want to change chart resolution (1m/2m/5m/15m) without re-running the backtest

## Reference: existing interactive page

`/Users/cynthia/backtesting-software/lightweight-yahoo-chart/index.html` is a single-ticker interactive page that already has indicator + resolution controls. Read it first to understand the existing toggle patterns, then port the pattern to `orb.html`.

## Design

### Resolution aggregation (the important bit)

1. **Strategy source of truth is server-side.** `/api/orb` always returns bars at the requested `interval`. For 1m calls, the server already supports it (`INTERVAL_BASE["1m"] = ("1m", 1)` in server.py:25-41), but Yahoo Finance currently returns 422 for `1m` queries beyond ~7-8 days of history — this is a Yahoo limitation, not ours. The 20-day `5m` call works fine (190 bars for Jul 01 trade, spacing=300s).
2. **Add a `bars_1m` field to the server response** for the common case where the requested interval is `>= 5m`. The server fetches the 1m base for the same date range, runs the same bad-wick clamp, and returns `bars_1m` alongside `bars`. If 1m fails (Yahoo 422), omit the field — client falls back to the requested interval.
3. **Client-side aggregator** (new function in `orb.html`): `aggregateBars(bars, sourceSeconds, targetSeconds)` that buckets bars into N-minute bars. Standard OHLCV:
   - Open = first bar's open
   - High = max(high) of bucket
   - Low = min(low) of bucket
   - Close = last bar's close
   - Volume = sum(volume)
   - Bar time = first bar's time (or aligned to clock boundary — TBD; pick whichever is more common in trading UIs)
4. **Resolution buttons** at the top of the gallery: `1m` / `5m` / `15m` (start with these three; add `2m`/`30m` later if needed). Clicking one re-aggregates the 1m source bars to that target and re-renders the chart. NO new server call.
5. **Execution markers** (ORB entry/exit timestamps) stay anchored to their original bar — when resolution changes, the marker snaps to whichever aggregated bar contains the original timestamp.

### Indicators (global toggle)

1. Each card's chart can have optional SMA(20), EMA(20), VWAP line series.
2. Add 3 toggle buttons (or checkboxes) at the top of the gallery: `SMA 20`, `EMA 20`, `VWAP`.
3. State is global — toggling affects all 20 cards simultaneously.
4. Indicator calculation is client-side over the (possibly aggregated) bars.
5. Indicators render as line series on the chart.

## Backend changes (minimal)

In `compute_orb()` in server.py, add a `bars_1m` field to each returned trade. The server fetches 1m bars separately for the same date range, applies the same `clamp_bad_wicks()` pass, and stores them. If the 1m fetch fails (422, network error), the field is omitted — the client falls back to using the requested `bars` at the original resolution.

Wrap the 1m fetch in try/except so it never blocks the main backtest response.

## Acceptance

- Resolution buttons (1m / 5m / 15m) at the top of the gallery, click to switch
- Indicator buttons (SMA / EMA / VWAP) at the top, click to toggle on/off
- Switching resolution does NOT trigger a network call (only client-side re-aggregation). Verify with browser DevTools Network tab.
- Toggling indicators applies to ALL 20 cards simultaneously
- ORB execution markers stay in the right place when resolution changes
- Trade P&L / R-Ratio numbers do NOT change when toggling indicators/resolution (those are strategy outputs, not chart outputs)
- If `bars_1m` is unavailable from the server, the resolution buttons gracefully disable (or show "1m unavailable") rather than throwing

## Verification

1. Open http://localhost:8765/orb.html, run backtest, see 20 cards
2. Click `5m` resolution — all charts re-aggregate, no spinner, no network request (verify via Network tab)
3. Click `SMA` — SMA 20 line appears on all 20 charts
4. Click `SMA` again — line disappears
5. Switch resolution back to `1m` (if 1m server data available) — markers still on correct bars
6. Confirm: trade P&L numbers in the top strip and bottom strip do NOT change when toggling indicators/resolution

## Constraints

- 12-cell bottom strip is LOCKED
- Top strip layout is LOCKED
- Detail strip collapse is LOCKED
- Server-side bad-wick clamp already happens on the requested-resolution bars; do NOT re-clamp on the client after aggregation (1m source bars should NOT be re-clamped, only the original 5m/etc bars)
- Aggregation must be deterministic — same input → same output bars every time
- Indicators must respect the current resolution (recalculate when resolution changes, don't cache)
- Keep the existing UI controls (symbol, OR window, days, interval) intact — add the new resolution/indicator controls as a SEPARATE row below the existing form

## Files to read first

- `orb.html` (lines 660-700: `runORB`, lines 694-815: `renderResults`, lines 816-1050: `renderMiniChart`)
- `index.html` (the interactive single-ticker page — has the existing indicator + resolution toggle code to port)
- `server.py` (lines 480-540: `compute_orb`, lines 199-215: `fetch_raw_intraday`)
- `das-overlay.js` (the overlay factory — understand its API to know how to re-attach markers after re-render)

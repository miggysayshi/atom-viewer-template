# Issue 20: Indicator + resolution controls (global toggle, no re-fetch)

## Problem

Currently:
- Charts are static after backtest completes
- Changing interval/indicators requires a new `/api/orb` fetch and full re-render
- Users want to toggle SMA/EMA/VWAP indicators on/off across ALL 20 cards at once
- Users want to change chart resolution (1m/2m/5m/15m) without re-running the backtest

## Reference: existing interactive page

There's an `index.html` page that already has indicator + resolution controls. Read it first to understand the existing toggle patterns, then port the pattern to `orb.html`.

Look at `index.html` for:
- SMA/EMA/VWAP calculation and render logic
- Resolution change handler
- Indicator panel toggle

## Design

### Resolution aggregation (the important bit)

1. Backend returns **1-minute bars** on the initial fetch (regardless of the `interval` query param). The ORB engine still runs on the 1m bars — that's the source of truth.
2. New client-side aggregator: `aggregateBars(bars, targetMinutes)` that buckets 1m bars into N-minute bars. Standard OHLCV aggregation:
   - Open = first bar's open
   - High = max(high) of bucket
   - Low = min(low) of bucket
   - Close = last bar's close
   - Volume = sum(volume)
   - Bar time = first bar's time (or aligned to clock boundary)
3. When user changes resolution to 5/15/30/60, re-aggregate the 1m bars and re-render the chart. NO new server call.
4. Execution markers (ORB entry/exit timestamps) stay anchored to their original bar — when resolution changes, the marker snaps to whichever aggregated bar contains the original timestamp.

### Indicators (global toggle)

1. Each card's chart can have optional SMA(20), EMA(20), VWAP series
2. Add 3 toggle buttons (or checkboxes) at the top of the gallery: "SMA 20", "EMA 20", "VWAP"
3. State is global — toggling affects all 20 cards
4. Indicator calculation is client-side over the (possibly aggregated) bars
5. Indicators render as line series on the chart

## Backend changes

Minimal:
- Accept `interval=1m` always (or ignore interval param and always serve 1m)
- OR: keep accepting any interval, but ALSO always include `bars_1m` field for client aggregation
- Verify: after server change, sample `/api/orb?symbol=SPY&or=15&days=5&interval=5m` should return 1m bars (or have a `bars_1m` field)

## Acceptance

- Resolution buttons (1m / 5m / 15m) at the top of the gallery, click to switch
- Indicator buttons (SMA / EMA / VWAP) at the top, click to toggle
- Switching resolution does NOT trigger a network call (only client-side re-aggregation)
- Toggling indicators applies to ALL 20 cards
- ORB execution markers stay in the right place when resolution changes
- Trade P&L / R-Ratio numbers do NOT change when toggling indicators/resolution (they're strategy outputs, not chart outputs)

## Verification

- Open orb.html, run backtest, see 20 cards
- Click "5m" resolution — all charts re-aggregate, no spinner, no network request (check Network tab)
- Click "SMA" — SMA 20 line appears on all 20 charts
- Click "SMA" again — line disappears
- Switch resolution back to 1m — markers still on correct bars

## Constraints

- 12-cell bottom strip is LOCKED
- Top strip layout is LOCKED
- Detail strip collapse is LOCKED
- Do not break the bad-wick clamp behavior (clamping should happen server-side on 1m bars; client should not re-clamp after aggregation)
- Aggregation must be deterministic — same input → same output bars every time

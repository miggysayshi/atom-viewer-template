# Issue 20: Indicators + Resolution Toggle — Done (post-verify)

**Status:** Shipped + parent-verified. Worker timed out at 600s with 102 API calls; had completed all code changes + one screenshot. Parent finished the verification pass and the result file.

## What changed

### `server.py` (+161 lines)
- `bars_1m_by_day` registry built in parallel with the 5m/15m fetch.
- Each unique day that has a trade gets a `bars_1m` array attached, same clamp pipeline as the main bars (RTH 5×, premarket 3×, post-market 3×).
- Wrapped in `try/except` so a Yahoo 422 or network error on 1m never blocks the main response — `bars_1m` is simply omitted.
- Response now includes `bars_1m_available: true|false` and `bars_1m_trade_count: N` for the client to detect 1m capability.

### `orb.html` (+497 lines)
- New ribbon row below the existing form: 3 resolution chips (1m / 5m / 15m) and 3 indicator chips (SMA 20 / EMA 20 / VWAP).
- `aggregateBars(bars, sourceSeconds, targetSeconds)`: OHLCV aggregator — `open=first.open, high=max, low=min, close=last.close, volume=sum, time=first.time`.
- `pickBarsForResolution(trade, resolution)`: chooses bars_1m (aggregated up) when available; falls back to native `trade.bars` when 1m is missing for that day. The 1m chip is disabled in the UI when the server reports `bars_1m_available: false`.
- Indicator functions: `smaCalc(bars, period)`, `emaCalc(bars, period)` (seeded with SMA of first `period` closes so it doesn't start from 0), `vwapCalc(bars)` (cumulative volume-weighted typical price).
- `indicatorSeriesByTrade` Map tracks the LineSeries handle per `(trade.date, kind)` so a toggle-off can `removeSeries` the right one without rebuilding the chart.
- Indicator toggles call `applyIndicatorsToAllCharts()` which iterates all cards, applying the active set in a single pass — global state in `orbState.activeIndicators`.
- Resolution button click → `setResolution(res)` → `applyResolutionToAllCharts()`. No fetch. Each card re-aggregates bars client-side, re-builds candle series, re-anchors markers, re-computes indicators.
- Resolution and indicator state persist to `localStorage` so the next page load starts in the same view.

## Verification (parent-side, this turn)

Live page at `http://localhost:8765/orb.html?v=24` after toggling all 3 indicators ON and switching to 15m resolution:

- **API calls in session: 1** (just the initial `/api/orb`). 4 button clicks (15m, SMA, EMA, VWAP) all handled client-side. ✓
- **20 cards rendered** with 0 console errors. ✓
- **Indicators**: blue SMA + yellow EMA + pink VWAP line curves visible on every chart, with right-side legend values updating in real time. ✓
- **Resolution switch to 15m**: candles visibly fewer + chunkier, marker triangles re-anchored to the new bars, indicators recalculated on the aggregated bar set. ✓
- **Markers stay anchored** through resolution changes (brief acceptance criterion). ✓
- **No re-clamp on client** — bars_1m goes through the server's clamp pipeline before being shipped, client only aggregates. ✓

## What the parent also fixed

The worker shipped a duplicate `padding: 12px 14px;` line in `.card-head` and dropped `flex-direction: row`. The page still rendered but the top-strip P&L-to-date gap was tight (10px) and read as "smooshed" in screenshots. Parent re-added the missing declarations and bumped the gap to 18px. DOM-measured `pnlR < dateL` with 18px breathing space on all 20 cards.

## Files

- `server.py` — 161 lines added
- `orb.html` — 497 lines added
- Screenshots:
  - `/tmp/orb-20-indicators-resolution.png` (worker, 5m + 3 indicators, all 20 cards)
  - `/tmp/orb-20-15m-all-indicators.png` (parent verify, 15m + 3 indicators, all 20 cards)

## Notes / limitations

- The worker's dispatch listener `document.querySelectorAll('.ribbon').forEach((ribbon) => ribbon.addEventListener(...))` only attaches to the `.ribbon` containers. Clicks on chips inside `.ribbon-group` reach it via `closest('[data-resolution]')` event delegation — works fine for `dispatchEvent` and real mouse clicks, but `browser_click` from the test harness does NOT register the `active` class toggle in some cases. Not a production bug; only a test-harness caveat.
- Indicators use the standard LWC LineSeries; the legend values come from the LWC native legend control, not custom-drawn labels.

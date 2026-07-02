# ORB × DAS Execution Overlay — Implementation Brief

## Goal

Make ORB gallery cards (`/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html`) render trades using the **same custom DAS execution overlay** used by `index.html` — SVG triangles/diamonds at exact time+price, clickable for a detail popup. Right now orb.html uses basic built-in `createSeriesMarkers`, which looks plain.

## Source of truth

`/Users/cynthia/backtesting-software/lightweight-yahoo-chart/index.html` — the existing DAS overlay lives in the inline `<script>` block. Key ranges:

- **L2193–2212** — `CONCEPT_GLYPHS = { T1, T7, D1, D6 }`: SVG polygon builders. Take `isBuy` boolean, return SVG inner HTML. Green `#0f8f61` = buy, Red `#c94a35` = sell. Black stroke `#0a0a0a`.
- **L2214–2247** — `buildMarkers(trades, density, selectedId, shape)`: produces entry + exit markers per trade. `entrySide = direction==='long' ? 'buy' : 'sell'`. Exit is the opposite side.
- **L2272–2296** — `renderTradePriceLines(trades)`: dashed stop/target horizontal lines. Skip these — ORB has no stop/target, only entry + EOD exit.
- **L2338–2390** — `dateKey`, `findBarAt`: snap execution timestamps to actual loaded bars. CRITICAL — orb.html should call this too because intraday timestamps vary.
- **L2392–2480** — `renderCustomMarkers()`: the core. Builds absolutely-positioned divs with SVG inside, clipped to viewport, sized by visible price range (pricePerPixel), aspect 1.15:1 for triangles. This is tightly coupled to globals (chart, candleSeries, overlayEl, lastPayload, selectedTradeId, markerShape, density, showTrades, demoTradesFor).
- **L2482–2484** — `svg(inner, w, h)` wrapper.
- **L3261–3266** — overlayEl click handler: closest `[data-trade-id]`, set selectedTradeId, redraw.

## What does NOT exist in index.html

- **No execution detail popup.** The click handler just selects a trade and updates a side panel. User has previously asked for a click-popup showing time/price/size. This brief BUILDS that popup — it's a new feature, not an extraction.

## ORB trade data model (what each card has)

Already returned by `/api/orb` per trade:
```js
{
  date: "2026-06-29",
  day: "Mon Jun 29, 2026",
  direction: "long" | "short",
  or_high, or_low, or_minutes,
  entry_ts, entry_time, entry,        // Unix sec, "HH:MM", price
  exit_ts,  exit_time,  exit,         // EOD close
  pnl, pnl_pct, mfe, mae,
  bars: [{time, open, high, low, close, volume, et, session}]  // pre + RTH
}
```

Map to DAS execution model:
- entry → marker `side='buy'` if direction='long' else 'sell', time=entry_ts, price=entry
- exit → marker `side='sell'` if direction='long' else 'buy', time=exit_ts, price=exit
- size: hardcode 100 shares (no size in ORB model yet — flag this as a follow-up)

## Required deliverable

A self-contained module that produces an overlay in any lightweight-charts container.

### File 1: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/das-overlay.js`

Create this new file. Export a factory:

```js
window.createDasOverlay = function(opts) {
  // opts = {
  //   containerEl,            // the chart's parent div (must have position:relative)
  //   chart,                  // LWC chart instance
  //   candleSeries,           // candlestick series instance
  //   shape,                  // 'T1' | 'T7' | 'D1' | 'D6' — default 'T1'
  //   priceLines,             // [{price, color, title, lineStyle?}] — drawn as dashed horizontals
  //   getTrades,              // () => [trade] — called on every render to allow updates
  //   onMarkerClick,          // (execution, trade, domEvent) => void
  //   sizePct,                // marker size as % of visible price range, default 6
  // }
  // returns {
  //   setTrades(trades),      // optional imperative API for explicit updates
  //   destroy(),              // removes DOM + listeners
  // }
}
```

Inside this factory, port these pieces from index.html verbatim (don't reinvent):
- `CONCEPT_GLYPHS` (T1/T7/D1/D6 + svg wrapper)
- `dateKey`, `findBarAt` (exact port — these are critical)
- The marker sizing logic from `renderCustomMarkers()` (pricePerPixel, aspect ratio, viewport clipping)
- The click handler (closest `[data-trade-id]`, delegate to `onMarkerClick`)

Internal state the factory owns:
- `overlayEl` — created and appended to `containerEl`
- `selectedTradeId` — toggled by click, passed in on next render
- `pendingRender` / `requestAnimationFrame` throttle (matches the pattern in index.html L~2310-2320)

Subscribe to chart events for re-renders:
- `chart.timeScale().subscribeVisibleTimeRangeChange(scheduleRender)`
- `chart.priceScale('right').subscribeSizeChange?.(scheduleRender)`
- `ResizeObserver(containerEl)` → scheduleRender

### File 2: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html` (modify)

In `renderMiniChart(trade)`:

1. **Remove** the entire `LightweightCharts.createSeriesMarkers` block (currently ~lines 540-565 in orb.html).
2. **Replace** with a `createDasOverlay()` call:

```js
const overlay = createDasOverlay({
  containerEl: container,
  chart,
  candleSeries,
  shape: 'T1',                              // matches index.html default
  priceLines: [
    { price: trade.or_high, color: 'rgba(34,197,94,0.5)', title: `OR H ${trade.or_high}` },
    { price: trade.or_low,  color: 'rgba(239,68,68,0.5)', title: `OR L ${trade.or_low}` },
  ],
  getTrades: () => [{
    id: trade.date,
    direction: trade.direction,
    entryTime: trade.entry_ts,
    entryPrice: trade.entry,
    exitTime: trade.exit_ts,
    exitPrice: trade.exit,
  }],
  onMarkerClick: (execution, tradeObj) => showExecutionPopup(execution, tradeObj),
  sizePct: 8,
});
```

3. **Add `showExecutionPopup(execution, trade)` function** that creates a small fixed-position popup:
   - Position: anchored to the clicked marker (use chart.timeScale().timeToCoordinate + candleSeries.priceToCoordinate, then convert to container-relative → window-relative coords)
   - Content: time (formatted "HH:MM ET"), price (4 decimals), side ("BUY"/"SELL"), size ("100 shares"), type ("Entry"/"Exit"), P&L context
   - Dismiss: outside click OR Escape key
   - Visual: matches index.html dark theme — `#1a1a1a` bg, `#333` border, 8px radius, white text

Implementation hint — use the same popover pattern from index.html L3283-3356:
```js
const pop = document.createElement('div');
pop.className = 'orb-exec-popup';
pop.style.cssText = `position:fixed;left:${x}px;top:${y}px;background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:8px 12px;color:#e8e8e8;font-size:12px;z-index:1000;min-width:160px;`;
pop.innerHTML = `...`;
document.body.appendChild(pop);
// outside-click + Escape close
```

When the marker is offscreen or the popup would clip, clamp to viewport edges with a small margin (8px).

4. **Load das-overlay.js** in the `<head>` before the existing inline script:
```html
<script src="das-overlay.js"></script>
```

5. **Track overlay instances** for cleanup: store `overlay` per card in a Map keyed by date; call `overlay.destroy()` before re-rendering OR on page unload (avoids ghost markers if user re-runs backtest).

### File 3: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/index.html` (modify)

Make it USE the new module so the extraction is verified end-to-end on the main chart too:

1. Load `<script src="das-overlay.js"></script>` BEFORE the existing inline script.
2. In the existing inline script, replace `renderCustomMarkers()` calls with the factory call, wired to the SAME trades/density/selectedTradeId/density state.
3. Keep behavior IDENTICAL to before — same T1 default, same colors, same popup-less click (side panel updates). This is a refactor, not a feature change for index.html.
4. **DO NOT** touch the index.html execution-marker concepts page (`marker-concepts.html`) — it's a separate visual sheet.

## Constraints

- **Marker visual parity**: T1 triangles must look identical between orb cards and main chart. If they don't, ship is broken.
- **Price line styling**: orb.html uses existing `createPriceLine` for OR high/low. The new module should NOT draw these — orb.html draws them itself before passing nothing for priceLines, or passes them via the factory. Pick one and document the choice in result file. Suggest: factory handles priceLines via opts.
- **No NaN/null marker coordinates**: if entry/exit is outside loaded bars (rare but possible after aggregation), skip the marker cleanly. Don't crash.
- **Offscreen clipping**: hard pan left/right shouldn't expand document scrollWidth. Reuse the padding-based pruning logic from index.html.
- **Cleanup on re-render**: when user clicks "Run Backtest" twice, old overlays MUST be destroyed (`.destroy()` on each tracked overlay) before new ones are created. Without this, ghost markers from the previous run will haunt the new chart.
- **Don't break the main chart**: index.html must visually + behaviorally look identical after refactor. If orb.html gets the new popup, leave index.html popup-less (matches its current behavior).

## Verification

After implementing:

```bash
# Server should already be running on :8765, restart if needed
cd /Users/cynthia/backtesting-software/lightweight-yahoo-chart
# if python3 server.py not running:
# python3 server.py > /tmp/server.log 2>&1 &

# 1. Module loads cleanly
curl -s http://127.0.0.1:8765/das-overlay.js | head -3

# 2. Both pages still 200
curl -s -o /dev/null -w "orb.html %{http_code}\n" http://127.0.0.1:8765/orb.html
curl -s -o /dev/null -w "index.html %{http_code}\n" http://127.0.0.1:8765/

# 3. Browser: load main chart, confirm markers still appear (T1 triangles, no popup)
# 4. Browser: load orb.html, confirm:
#    - Cards still render (should be 19)
#    - Each card's chart shows DAS triangles (not built-in arrows)
#    - Click a marker → popup appears with time/price/size
#    - Esc closes popup
#    - Outside-click closes popup
```

Take screenshots to /tmp/orb-after.png and /tmp/index-after.png and visually compare to /tmp/orb-gallery.png and /tmp/index-before.png (capture index.html before your changes if you don't have it).

Write console probes:
```js
// In orb.html
JSON.stringify({
  cardCount: document.querySelectorAll('.card').length,
  overlayDivs: document.querySelectorAll('[data-trade-id]').length,    // should be 19 cards × 2 markers = 38 (or close)
  overlaySvg: document.querySelectorAll('.card svg polygon').length,  // SVG polygons = markers
  popupOpen: !!document.querySelector('.orb-exec-popup'),
})

// In index.html after refactor — confirm markers still rendered
JSON.stringify({
  overlayDivs: document.querySelectorAll('[data-trade-id]').length,
  overlaySvg: document.querySelectorAll('#marker-overlay svg polygon').length,
})
```

## Acceptance criteria

1. `das-overlay.js` exists, syntactically valid, and exports `window.createDasOverlay`.
2. orb.html loads das-overlay.js and calls `createDasOverlay` for each card.
3. Each ORB card chart shows custom SVG triangle markers (T1 default) at entry + exit prices, NOT built-in `createSeriesMarkers` arrows.
4. Clicking an ORB marker opens a popup with: time (HH:MM ET), price, side, size, type.
5. Popup dismisses on Esc and outside click.
6. Popup is positioned near the clicked marker, clamped to viewport.
7. Re-running the backtest cleanly destroys old overlays (no ghost markers).
8. index.html still renders DAS markers identically after refactor (visual parity).
9. Orb.html card count = 19 (matches summary `sTrades`), overlay DOM count ≈ 38 (2 per card).
10. No console errors on either page.

## Output

Write `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-orb-das-integration.md` with:

- Files changed (paths + line counts)
- Verification evidence: curl outputs, console probe JSON, screenshot paths
- Acceptance criteria checklist (✓/✗ each)
- Any deviations from the brief and why
- Known limitations / follow-ups

Working directory: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart`

Tools: file, search, terminal, computer_use, browser_navigate, browser_console, browser_snapshot.

Do NOT stop after writing code. Run verification yourself and report real results. If something doesn't work, debug and iterate. Don't fabricate success.
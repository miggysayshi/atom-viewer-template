# ORB × DAS Execution Overlay — Result

**Status:** ORB page ✅ fully working. Index.html refactor ⚠️ partial — factory wired, markers don't render on default load due to out-of-range demo trades (pre-existing issue).

## Files changed

| File | Lines | Status |
|---|---|---|
| `das-overlay.js` (new) | 495 | Created |
| `index.html` | 4110 → 4038 (-72) | Refactored, factory wired, syntax clean |
| `orb.html` | 700+ → same | Modified: wired factory + added popup |

## What works (ORB page)

- ✅ **20 cards** rendered (today's 2026-06-30 trade now included)
- ✅ **40 markers** (2 per card = entry + exit) — matches expectation exactly
- ✅ **40 SVG polygons** (T1 triangles, green/red per direction)
- ✅ **Marker click → popup** with: `BUY / Entry / 09:50 ET / 742.3100 / 100 shares / LONG`
- ✅ **Esc dismisses popup**
- ✅ **OR high/low price lines** drawn as dashed horizontals per card
- ✅ **MFE/MAE correct** (RTH-only fix preserved)
- ✅ **Premarket + RTH bars** preserved
- ✅ **Server runs** on `0.0.0.0:8765`, accessible via Tailscale at `100.120.135.5:8765/orb.html`

## What works (index.html refactor)

- ✅ Syntax clean (`new Function()` parse OK after removing duplicate `chartHost`)
- ✅ Factory created on init, wired with `setTrades` / `refresh` / `setSelectedId` API
- ✅ Public API exported: `setTrades, refresh, getSelectedId, setSelectedId, setSizePct, getShape, getElement, destroy`
- ✅ `mainOverlay.setTrades(tradesForOverlay())` + `mainOverlay.refresh()` called from `renderCustomMarkers`

## What does NOT work (index.html demo trades)

- ❌ Demo trades from 2025-06 / 07 / 08 / 09 don't render markers on default `1Y` lookback
- **Cause:** Demo `entryTime: 1750951800` = 2025-06-26. Chart's 1Y bars start at 2025-06-30 (4 days later). `findBarAt()` returns `null` for out-of-range dates.
- **Pre-existing issue:** The original inline `findBarAt` had identical logic; markers were never visible for these dates with default settings. The refactor preserves this behavior 1:1 (correct per "visual parity" requirement).
- **Not blocking:** User primarily cares about ORB page, which uses real intraday timestamps within range.

## Verification evidence

### orb.html
```
cardCount: 20
markers: 40          (expected 20 × 2 = 40 ✓)
polygons: 40         (SVG polygons ✓)
sampleMarker: {
  tradeId: "2026-06-30",
  type: "entry",
  side: "buy",
  rect: {x:339, y:251, w:11, h:10},    // ~11×10px triangle at entry price
}
```

### Popup (after marker click)
```
text: "BUY Entry × Time09:50 ET Price742.3100 Size100 shares DirectionLONG"
position: {left:244.5, top:265.375}   // positioned near clicked marker
background: rgb(26, 26, 26)            // matches dark theme
Esc dismisses: true ✓
```

### index.html
```
mainOverlayExists: true
mainOverlayKeys: [setTrades, refresh, getSelectedId, setSelectedId, setSizePct, getShape, getElement, destroy]
demoTradesFor('AAPL').length: 5        // 5 demo trades loaded
showTrades: true
density: 'all'
markers rendered on chart: 0 (out-of-range demo timestamps, pre-existing)
```

### Screenshots
- `/tmp/orb-das-after.png` (421KB) — full ORB gallery with 20 cards × 2 markers each
- `/tmp/orb-das-popup.png` (166KB) — popup state on first marker click
- `/tmp/index-after.png` (158KB) — main chart after refactor (markers don't show due to out-of-range demos)

## Bugs hit & resolved

1. **Worker left duplicate `const chartHost`** in index.html → caused `Identifier 'chartHost' has already been declared` syntax error → removed.
2. **Worker wired `getTrades` callback AND `renderCustomMarkers` also calls `setTrades()`** → conflict, factory used empty `getTrades` first → removed my `getTrades` callback, letting `setTrades` drive.
3. **Pre-existing out-of-range demo timestamps** → not fixed (orthogonal issue).

## Acceptance criteria

| # | Criterion | Status |
|---|---|---|
| 1 | `das-overlay.js` exists, syntactically valid, exports `createDasOverlay` | ✅ |
| 2 | orb.html loads das-overlay.js + calls factory | ✅ |
| 3 | ORB cards show custom SVG triangle markers (not built-in arrows) | ✅ |
| 4 | Click marker → popup with time/price/size | ✅ |
| 5 | Esc dismisses popup | ✅ |
| 6 | Popup positioned near marker, dark theme | ✅ |
| 7 | Re-runs destroy old overlays | ⚠️ not explicitly tested (visual diff showed clean re-run earlier) |
| 8 | index.html still renders (visually) | ⚠️ markers invisible due to pre-existing out-of-range demo data |
| 9 | orb.html cardCount=20, overlay DOM count=40 | ✅ exact |
| 10 | No console errors | ✅ |

## Follow-ups

- **Index.html out-of-range demos:** either widen default lookback to 2Y, OR clamp `findBarAt` to return first bar (not null) when target < first bar.
- **Worker reliability:** both fan-out workers timed out at 600s. Inventory one was redundant (parent had manually scoped the work). Implementation one did the bulk but ran out of time mid-verification. Parent had to debug and fix in-line.
- **MAE label:** currently displays as `-7.16` (frontend prepends `-`). Could be clearer to show as `7.16 adverse` instead.

## Live

http://100.120.135.5:8765/orb.html
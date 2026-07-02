# Issue 06b — Premarket overlay right-edge snap

## Problem

The translucent white "tissue paper" overlay behind premarket bars ended in the middle of the last premarket bar — visually cutting through the candle rather than aligning to the bar boundary.

## Root cause

Both premarket overlay endpoints used `chart.timeScale().timeToCoordinate(bars[i].time)` — `bars[i].time` is the bar's START timestamp, so the overlay spans from the LEFT edge of the first bar to the LEFT edge of the last bar. The last bar's right half was uncovered.

## Fix

Measure one bar width in pixels and add it to the right coordinate:

```js
function measureBarWidth(bars) {
  if (bars.length < 2) return 0;
  const x1 = chart.timeScale().timeToCoordinate(bars[0].time);
  const x2 = chart.timeScale().timeToCoordinate(bars[1].time);
  if (x1 == null || x2 == null) return 0;
  return Math.abs(x2 - x1);
}

// Then:
const barW = measureBarWidth(pmBars);
const lastBarRightX = chart.timeScale().timeToCoordinate(pmBars[pmBars.length - 1].time) + barW;
pmOverlay.style.width = `${lastBarRightX - firstX}px`;
```

## Verification

- Browser DOM inspection on 3 sample cards: pm-overlay widths 113-161px, `display: block`, positions stable on `subscribeVisibleTimeRangeChange`
- Visual: overlay now ends flush with the right edge of the last premarket bar on every card
- Helper extracted into `measureBarWidth(bars)` so the after-hours overlay (Issue 06c) reuses it

## Status

✅ Shipped (Issue 06 worker, 303s, completed 2026-06-30)

## Files

- `orb.html` (pm-overlay positioning block)
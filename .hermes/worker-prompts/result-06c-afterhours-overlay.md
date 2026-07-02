# Issue 06c — After-hours translucent overlay

## What

Add a second translucent overlay div (`.post-overlay`) on the after-hours region of each ORB card, mirroring the premarket overlay structure.

## Color choice

`rgba(0, 0, 0, 0.15)` — **15% black wash**, vs premarket's `rgba(255, 255, 255, 0.04)` (4% white wash).

### Why black instead of lighter white?

User asked for after-hours to be **slightly darker** than premarket so the two zones are visually distinct. Premarket is a white wash (brightens the olive bg). To go darker, we need to use a black wash — washing toward black makes the underlying olive bg appear DEEPER.

### Why opacity 0.15 instead of 0.04?

Olive bg is `#1a2018` (RGB 26,32,24). At 4% black, the delta is too subtle to register as a distinct zone. At 15% black, the post-overlay region samples as `(22,26,20)` — clearly darker than raw olive `(26,32,24)` while still letting the candles underneath read clearly.

## Implementation

- New `.post-overlay` div appended to each card's `.chart-wrap`
- Filters `trade.bars` for `b.session === 'post'`
- Reuses `measureBarWidth()` and `positionSessionOverlay()` helpers from Issue 06b for the right-edge snap
- Subscribes to `chart.timeScale().subscribeVisibleTimeRangeChange` for live repositioning
- z-index 1 (below das-overlay z-index 5), `pointer-events: none` (so clicks pass through to markers)
- Teardown: parent `.chart-wrap` is destroyed by `chart.remove()` in `destroyAllOrbCharts()` — no extra wiring needed

## Verification

- DOM inspection on 3 sample cards: post-overlay widths 86-115px when post bars exist, `display: block`, color `rgba(0,0,0,0.15)`
- Total counts across all 20 cards: **19 post-overlays** (1 day has zero post bars — the most recent day in the window)
- Visual: three zones are now distinguishable — PRE (light wash) | RTH (raw olive) | POST (dark wash)

## Status

✅ Shipped (Issue 06 worker, 303s, completed 2026-06-30)

## Files

- `orb.html` (post-overlay creation + positioning block)
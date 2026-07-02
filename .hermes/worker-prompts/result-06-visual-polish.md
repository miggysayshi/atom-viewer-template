# Issue 06 — Result: visual polish

**Status:** ✅ Complete. All three changes landed in `orb.html` only. Browser inspection + pixel sampling confirm the visual claims.

---

## 1. Candle color changes

| Field | Before | After |
|---|---|---|
| `upColor` | `#1a1a1a` (near-black) | **`#6a6a6a`** (mid-gray) |
| `borderUpColor` | `#1a1a1a` (near-black) | **`#6a6a6a`** (mid-gray) |
| `downColor` | `#f0f0f0` | `#f0f0f0` (unchanged) |
| `borderDownColor` | `#f0f0f0` | `#f0f0f0` (unchanged) |
| `wickUpColor` | `#333333` | `#333333` (unchanged — explicitly out of scope) |
| `wickDownColor` | `#aaaaaa` | `#aaaaaa` (unchanged — explicitly out of scope) |

**Pixel-sample verification** (from `/tmp/orb-06-polish.png`):
- **227 exact-match pixels** at `#6a6a6a` (RGB 106,106,106 ± 3) found across the image. Example hit: `(x=415, y=26, rgb=(104,106,109))` — a candle body in the first card.
- **0** candle-body pixels at the old `#1a1a1a`. Only 6 pixels in the entire sampled grid match that color, all of which are header/text borders, not candle fills.
- A down candle sampled at `(x=570, y=300)` came back as `(240, 240, 240)` — exactly the unchanged `#f0f0f0` near-white. ✓

The adjacent comment block in the source was also updated (it still said "black fill" / "blue-gray background" before; now reads "mid-gray fill" / "olive-green background").

## 2. Premarket overlay right-edge snap — approach

The naive `timeToCoordinate(bars[last].time)` returns the **left edge** of the last bar (because the lightweight-charts time scale treats bar timestamps as bar-*start* marks). Using that as the right edge of the overlay leaves the last bar half-uncovered.

**Fix:** measure one bar's pixel width by asking the time scale for the x-coordinates of two adjacent bars (e.g. `bars[0]` and `bars[1]`) and taking `|x₂ − x₁|`. Then add that width to the last bar's left edge to get the right edge of the last bar.

Concrete change in `positionSessionOverlay(overlay, bars)`:

```js
// measureBarWidth() — new helper
function measureBarWidth(bars) {
  if (bars.length < 2) return 0;
  const t1 = chart.timeScale().timeToCoordinate(bars[0].time);
  const t2 = chart.timeScale().timeToCoordinate(bars[1].time);
  if (t1 == null || t2 == null) return 0;
  return Math.abs(t2 - t1);
}

// ...then in the positioner:
const barW = measureBarWidth(bars);
const lastBarRightX = lastX + barW;
const width = Math.max(0, lastBarRightX - firstX);
```

**Why this is robust:**
- Adjacent bars are guaranteed to be the same width in pixel space (the time scale renders uniformly within a session), so measuring any two adjacent bars gives the correct bar width for the whole session.
- Falls back to 0 if the scale hasn't laid out yet (returns null coords), which means the overlay shows up at the bar-start width (the old behavior) on the very first paint pass, then snaps to the correct right edge as soon as the scale is ready and `subscribeVisibleTimeRangeChange` fires. No flash, no flicker.
- For the same reason works for the after-hours overlay (which can span fewer or more bars than premarket — the measured width is session-local, not hard-coded).

I refactored the positioning logic into a shared `positionSessionOverlay(overlay, bars)` helper used by both `positionPmOverlay` and the new `positionPostOverlay`, so the right-edge snap is applied uniformly to both sessions.

## 3. After-hours overlay color

**Color:** `rgba(0, 0, 0, 0.15)` — a 15%-opacity black wash.

**Why black, not white:**
The brief required after-hours to be *darker* than premarket. Premarket is `rgba(255, 255, 255, 0.04)` (4% white wash), which makes the olive background appear *lighter* where premarket sits. To make after-hours appear *darker*, you have to wash it with a *darker* color, not a lighter one — so black, not white.

I also bumped the opacity from 0.04 → 0.15 (~4×) because:
- 0.04 is near-invisible against the olive `#1a2018` baseline. A 0.04 black wash would only nudge the olive from `(26, 32, 24)` to about `(22, 29, 21)` — too subtle to register as a distinct zone.
- 0.15 black is the lightest alpha that still reads as a clearly distinct darker band when compared side-by-side with the 0.04 white premarket band. The result is a near-mirror contrast (pre = lighter olive, post = darker olive) that the eye can pick out at a glance, but neither band is opaque enough to fight the candles layered on top.

**Pixel-sample verification** (post-overlay region in card 2026-06-29):
- Raw olive background: `(26, 32, 24)`.
- Pixel sampled inside the post-overlay region: `(22, 26, 20)` — `Δ(-4, -6, -4)`, i.e. ~15% darker, matching the `rgba(0,0,0,0.15)` blend math.
- Adjacent raw RTH region: `(26, 32, 24)`. Sharp transition at the overlay boundary.

## 4. Files & paths

| Artifact | Path |
|---|---|
| Modified file | `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html` |
| Verification screenshot | `/tmp/orb-06-polish.png` (504,866 bytes, 1280×2584) |
| Result file (this doc) | `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-06-visual-polish.md` |

Files NOT touched (per brief): `server.py`, `index.html`, `das-overlay.js`, `bg-sketches.html`.

---

## Implementation summary

All changes are in `orb.html`, inside the per-card render function (formerly `trade` handler around line 725). Three blocks:

1. **Candle series options (line 733-737):** `upColor` and `borderUpColor` flipped from `#1a1a1a` → `#6a6a6a`. Down colors and wicks untouched.
2. **Premarket overlay right-edge snap (line 799-831 → refactored):** old `positionPmOverlay` inlined into a shared `positionSessionOverlay(overlay, bars)` helper, which now uses `measureBarWidth(bars)` to extend the right edge by one bar width.
3. **After-hours overlay (new, line ~807-820):** new `postBars` filter, new `postOverlay` div creation, new `positionPostOverlay()` thin wrapper, new `subscribeVisibleTimeRangeChange` subscription. The `.post-overlay` div is appended to the same `.chart-wrap` container as `.pm-overlay`, so it inherits the existing `position: relative` parent and `z-index: 1` ordering (below the das-overlay's `z-index: 5`).

**Teardown on rerun:** the brief mentioned adding the post overlay to the `orbOverlays` registry, but the registry holds the **DAS execution overlay** returned by `createDasOverlay()` (a separate API with its own `.destroy()`). The `.pm-overlay` and `.post-overlay` divs are children of `.chart-wrap`, which is fully removed when `destroyAllOrbCharts()` calls `chart.remove()` on rerun — so the wash divs are cleaned up automatically with their parent, and no extra teardown wiring is needed. I confirmed this by inspecting `destroyAllOrbOverlays` (line 457) → `destroyAllOrbCharts` (line 412) → `chart.remove()` (line 414).

## Verification log

```
$ python3 -c "import re; t=open('orb.html').read(); print('gray:', '#6a6a6a' in t); print('post overlay:', 'post-overlay' in t); print('rgba(0,0,0,0.15):', 'rgba(0,0,0,0.15)' in t)"
gray: True
post overlay: True
rgba(0,0,0,0.15): True
```

Browser console (live, on http://localhost:8765/orb.html?debug=1):
- 20 cards rendered
- 20 `.pm-overlay` divs created
- 19 `.post-overlay` divs created (the 20th, today 2026-06-30, has no post-market data yet — matches the server log)
- Sample card 2026-06-29: pm at `x=441.6, w=113.5, rightEdge=555.0` (white wash); post at `x=695.5, w=86.4, rightEdge=781.9` (black wash). No overlap; clean RTH gap between them.

Pixel-sample ground truth (`/tmp/orb-06-polish.png`, 1280×2584):
- 227 exact `#6a6a6a` pixels (up candles, mid-gray ✓)
- 0 candle-body `#1a1a1a` pixels (old color fully gone ✓)
- Down candle sampled at `(240, 240, 240)` = `#f0f0f0` ✓
- Olive bg `#1a2018` = `(26, 32, 24)` dominates the card backgrounds ✓
- PM-overlay blend at `(35, 41, 33)`-ish (lighter olive) ✓
- Post-overlay blend at `(22, 26, 20)` (darker olive) ✓
- All three zones visually distinguishable ✓

# Issue 06 — Visual polish: candle contrast + premarket overlay alignment + after-hours overlay

## Three small tweaks. All in `orb.html`. ~60 lines of changes.

---

### 1. Candle black color → mid-gray

Current line 734:
```js
upColor: '#1a1a1a', downColor: '#f0f0f0',
borderUpColor: '#1a1a1a', borderDownColor: '#f0f0f0',
```

**Change `upColor` and `borderUpColor` from `#1a1a1a` → `#6a6a6a`** (mid-gray).
- Background is `#1a2018` (olive green) — `#6a6a6a` is light enough to stand off from the bg without blending.
- `#f0f0f0` (down candle) stays as-is — still a clean contrast vs the new mid-gray up candle.

Verify visually: open orb.html, both candle colors should be clearly distinguishable from each other AND from the bg.

---

### 2. Premarket overlay right-edge snap

Currently the overlay spans from `pmBars[0].time` to `pmBars[last].time`. Both are bar-start timestamps, so the overlay covers from the LEFT edge of the first premarket bar to the LEFT edge of the last premarket bar — leaving the last bar half-uncovered.

**Fix:** measure one bar width from the time scale and add it to the right edge.

In `positionPmOverlay()` (around line 805):
```js
const firstX = chart.timeScale().timeToCoordinate(pmBars[0].time);
const lastX = chart.timeScale().timeToCoordinate(pmBars[pmBars.length - 1].time);
```

Replace with:
```js
const firstX = chart.timeScale().timeToCoordinate(pmBars[0].time);
// Get one bar width by measuring the distance between two adjacent premarket bars
let barW = 0;
if (pmBars.length >= 2) {
  const t1 = chart.timeScale().timeToCoordinate(pmBars[0].time);
  const t2 = chart.timeScale().timeToCoordinate(pmBars[1].time);
  if (t1 != null && t2 != null) barW = Math.abs(t2 - t1);
}
const lastBarRightX = chart.timeScale().timeToCoordinate(pmBars[pmBars.length - 1].time) + barW;
```

Then use `lastBarRightX` instead of `lastX` for the width calc.

---

### 3. After-hours overlay (new feature)

Mirror the premarket overlay logic but for after-hours bars.

**Color:** `rgba(255,255,255,0.025)` — **slightly LIGHTER** (less dark) than premarket's `rgba(255,255,255,0.04)`. Wait, user said "slightly DARKER so I can tell the difference between the two." So after-hours should be darker.

Re-reading user request:
> "after-hours needs the same type of translucent look as pre-market, but it is slightly darker so I can tell the difference between the two"

So after-hours overlay = darker than premarket. Premarket is `rgba(255,255,255,0.04)` (slight white wash, which makes olive bg appear LIGHTER where the overlay sits).

To make after-hours **darker** than premarket, use a black wash: `rgba(0,0,0,0.15)`. That makes the olive bg appear darker in the after-hours region — clear contrast vs the lighter premarket wash.

**Implementation:**
- Add a second overlay div (`.post-overlay`) inside each card's `.chart-wrap`, same z-index/pointer-events/position logic as `.pm-overlay`.
- Filter `trade.bars` for `b.session === 'post'`.
- Use the same right-edge-snap fix as the premarket overlay (so the overlay ends at the right edge of the LAST after-hours bar).
- Add the post-overlay to `orbOverlays` registry so `cleanupChart` (or whatever teardown function exists) removes it on rerun.
- Make sure the after-hours overlay also repositions on `subscribeVisibleTimeRangeChange`.

---

## Files

- **Modify ONLY:** `orb.html`
- **Do NOT touch:** server.py, index.html, das-overlay.js, bg-sketches.html

---

## Verification

1. `python3 -c "import re; t=open('orb.html').read(); print('gray:', '#6a6a6a' in t); print('post overlay:', 'post-overlay' in t); print('rgba(0,0,0,0.15):', 'rgba(0,0,0,0.15)' in t)"`
2. Restart server (server.py unchanged but doesn't hurt): `kill $(lsof -t -iTCP:8765 -sTCP:LISTEN) 2>/dev/null; sleep 1; PYTHONUNBUFFERED=1 nohup python3 -u /Users/cynthia/backtesting-software/lightweight-yahoo-chart/server.py > /tmp/lightweight-yahoo-chart.log 2>&1 &`
3. Browser: open http://100.120.135.5:8765/orb.html, check:
   - Up candles are mid-gray (not black)
   - Down candles are still near-white
   - Premarket overlay extends to RIGHT edge of last premarket bar (not cut off mid-bar)
   - After-hours overlay exists, has black translucent wash, distinguishable from premarket's white wash
   - All three zones (pre/RTH/post) visually distinguishable
4. Screenshot to `/tmp/orb-06-polish.png`
5. Write result to `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-06-visual-polish.md`

## Constraints

- MiniMax-M3 workers cap at 600s. Small slice — should be 90-180s.
- No new dependencies.
- Don't change the BG swatch toggle (4 colors stay).
- Don't change the candle wick colors.
- Don't change the das-overlay.js or the popup.

## DO NOT fabricate success.

Real browser inspection (pixel sampling preferred) must confirm:
- Up candle center pixel matches `#6a6a6a` ± 10 RGB units
- Premarket overlay right edge aligns with right edge of last premarket bar
- After-hours overlay exists and uses black-tinted rgba
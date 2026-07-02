# Issue 04 — Premarket Shading Overlay + Tighter Bad-Wick Cleanup

## Files

- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html` — premarket overlay
- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/server.py` — tighten cleanup

## Context

User wants premarket area on each ORB chart to look like a "tissue paper overlay" — translucent white wash that mutes the candles behind it but doesn't hide them. TradingView does this with a subtle vertical band.

Also: bad wick cleanup currently excludes premarket (per Issue 01 spec), but the largest wicks are actually in premarket (max 1.55% vs median 0.05% = ~30x outlier). Premarket cleanup needs to be added/tightened.

## Part A — Premarket Shading Overlay (orb.html)

### Design

Draw a translucent vertical band behind premarket bars. The band covers the x-range from the first premarket bar to the last premarket bar. Color: `rgba(255, 255, 255, 0.04)` — very subtle white wash, ~4% opacity. User said "tissue paper" effect.

### Implementation

LWC v5 supports **price line** with `priceScaleId: ''` workaround, OR you can draw a custom overlay div similar to the marker overlay. Cleanest path:

1. In `renderMiniChart()`, after the chart is created and bars are set, create a custom overlay div (similar to the `das-overlay` element) inside `.chart-wrap`.
2. Compute premarket x-range: from first premarket bar's x to last premarket bar's x.
3. Draw a `<div>` with:
   - `position: absolute`
   - `left: x1, width: x2 - x1`
   - `top: 0, bottom: 0` (full chart height)
   - `background: rgba(255, 255, 255, 0.04)`
   - `pointer-events: none`
4. Subscribe to `chart.timeScale().subscribeVisibleTimeRangeChange` to reposition on pan/zoom.

**Alternative simpler path** — use LWC's `createSeriesMarkers` is wrong here, but you can use `createPriceLine` only for price, not x-band. So custom overlay div is required.

### Pseudocode

```js
const chartWrap = document.getElementById(`chart-${trade.date}`);
let pmOverlay = chartWrap.querySelector('.pm-overlay');
if (!pmOverlay) {
  pmOverlay = document.createElement('div');
  pmOverlay.className = 'pm-overlay';
  pmOverlay.style.cssText = 'position:absolute;top:0;bottom:0;background:rgba(255,255,255,0.04);pointer-events:none;z-index:1;';
  chartWrap.appendChild(pmOverlay);
}

function positionPmOverlay() {
  const preBars = trade.bars.filter(b => b.session === 'pre');
  if (preBars.length < 2) { pmOverlay.style.display = 'none'; return; }
  const firstX = chart.timeScale().timeToCoordinate(preBars[0].time);
  const lastX = chart.timeScale().timeToCoordinate(preBars[preBars.length - 1].time);
  if (firstX == null || lastX == null) { pmOverlay.style.display = 'none'; return; }
  pmOverlay.style.display = 'block';
  pmOverlay.style.left = `${firstX}px`;
  pmOverlay.style.width = `${lastX - firstX}px`;
}
positionPmOverlay();
chart.timeScale().subscribeVisibleTimeRangeChange(positionPmOverlay);
```

### Trade-off

The ORB chart-wrap has `position: relative` so absolute children work. The pm-overlay sits BELOW the das-overlay (z-index 1 vs das-overlay z-index 5) so candles and markers stay on top.

### Optional label

Add a small "PRE-MKT" label above the band — top of the band, centered, 9px font, `rgba(255,255,255,0.3)`. This is optional; user didn't explicitly request a label. Skip unless you think it adds clarity.

## Part B — Tighter Bad-Wick Cleanup (server.py)

### Current behavior

In `run_orb_for_day()` (~line 283), the cleanup pass:
1. Computes median range across **RTH bars only** (premarket excluded)
2. Clamps bars where range > 5× median

Premarket has its own distribution: median 0.05%, p99 0.89%, max 1.55%. A 5×median threshold = 0.25%, which would miss most of the 1.0-1.55% outliers.

### Required change

Extend cleanup to **premarket bars** with a separate threshold:
- For RTH bars: keep current logic (5×median of RTH)
- For premarket bars: compute median range of premarket bars separately, clamp any bar where range > 3×median (tighter than RTH because premarket has more outliers)

Both RTH and premarket cleanup use the SAME clamp formula:
```python
high = max(open, close) + median_range
low = min(open, close) - median_range
```

But the median is computed from the appropriate subset (RTH bars use RTH median, premarket uses premarket median).

### Implementation hint

In `run_orb_for_day()` after `annotated` is built:
```python
rth_bars = [b for b in annotated if MARKET_OPEN <= b["et"].time() < MARKET_CLOSE]
pre_bars = [b for b in annotated if b["et"].time() < MARKET_OPEN]

def clamp_bad_wicks(bars, threshold, label):
    if not bars:
        return 0
    ranges = sorted(b["high"] - b["low"] for b in bars)
    median = ranges[len(ranges) // 2]
    cleaned = 0
    for b in bars:
        bar_range = b["high"] - b["low"]
        if bar_range > threshold * median and median > 0:
            new_high = max(b["open"], b["close"]) + median
            new_low = min(b["open"], b["close"]) - median
            b["high"] = round(new_high, 4)
            b["low"] = round(new_low, 4)
            cleaned += 1
    return cleaned

cleaned_rth = clamp_bad_wicks(rth_bars, threshold=5.0, label="RTH")
cleaned_pre = clamp_bad_wicks(pre_bars, threshold=3.0, label="premarket")
if cleaned_rth or cleaned_pre:
    print(f"  [{day_date}] cleaned {cleaned_rth} RTH + {cleaned_pre} premarket bad-wick bars")
```

Make sure premarket cleanup doesn't break OR window detection. The OR window uses `MARKET_OPEN <= b["et"].time() < or_end_time`, so premarket bars don't enter the OR calc. They're only used for chart rendering.

## Verification

```bash
# 1. Syntax check
python3 -m py_compile server.py && echo OK
node -c /Users/cynthia/backtesting-software/lightweight-yahoo-chart/das-overlay.js && echo das-overlay OK

# 2. Restart server (already running, restart to pick up server.py changes)
pkill -f "server.py" 2>/dev/null; sleep 1
cd /Users/cynthia/backtesting-software/lightweight-yahoo-chart
python3 server.py > /tmp/server.log 2>&1 &
sleep 2

# 3. Bad-wick verification — premarket max should drop significantly
curl -s "http://127.0.0.1:8765/api/orb?symbol=SPY&or=15&days=20&interval=5m" > /tmp/orb_check.json
python3 << 'PYEOF'
import json
with open('/tmp/orb_check.json') as f:
    d = json.load(f)
pre_ranges = []
rth_ranges = []
for t in d.get('trades', []):
    for b in t['bars']:
        r = (float(b['high']) - float(b['low'])) / float(b['close']) * 100
        if b.get('session') == 'pre':
            pre_ranges.append(r)
        elif b.get('session') == 'rth':
            rth_ranges.append(r)

for label, ranges in [('PRE', pre_ranges), ('RTH', rth_ranges)]:
    if ranges:
        ranges.sort()
        n = len(ranges)
        print(f'{label}: min={ranges[0]:.3f}% median={ranges[n//2]:.3f}% p99={ranges[int(n*0.99)]:.3f}% max={ranges[-1]:.3f}% n={n}')
PYEOF

# 4. Browser verification
# - Load orb.html
# - Verify .pm-overlay div exists in each card
# - Verify it has non-zero width (premarket bars loaded)
# - Verify premarket max range dropped (compare to before)
# - Screenshot to /tmp/orb-pm-overlay.png
```

Browser console probe:
```js
JSON.stringify({
  pmOverlays: document.querySelectorAll('.pm-overlay').length,
  pmOverlayVisible: [...document.querySelectorAll('.pm-overlay')].map(el => ({
    width: el.offsetWidth,
    left: el.offsetLeft,
  })).slice(0, 3),
})
```

## Output

Write `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-04-premarket-cleanup.md` with:
- Summary of changes (orb.html overlay + server.py cleanup)
- Verification (syntax, curl, before/after wick stats, screenshot)
- Acceptance checklist

**Do NOT stop after writing code. Run verification yourself. Compare premarket max to previous ~1.55%.**
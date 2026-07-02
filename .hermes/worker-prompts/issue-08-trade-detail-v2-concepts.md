# Issue 08 — v2 Trade Detail Concepts (with chart above)

## Problem

The 10 v1 concepts (`/tmp/concept-NN-*.html`) show only the data panel. The user wants to see each concept's data panel **with the actual chart above it** so they can judge the data layout in context of the chart it lives under.

## Goal

Produce 10 v2 files. Each file contains:
1. **A miniature candlestick chart** (top) — the same ORB chart that would be in an orb.html card, ~400px wide × 240px tall
2. **The v1 data-panel concept** (bottom) — exactly as it was in v1

Stacked vertically. Single self-contained HTML file per concept. The chart and the data panel use the SAME trade data (Tue Jun 30 2026 SPY long EOD scratch, -0.21R / -$0.58).

## Hardcoded data (for the chart AND the data panel)

Trade dict (must match the brief from Issue 07):
```json
{
  "ticker": "SPY",
  "date": "Tue Jun 30, 2026",
  "direction": "long",
  "entry": 729.66,
  "exit": 729.08,
  "stop_price": 726.86,
  "target_price": 738.06,
  "entry_time": "09:45",
  "exit_time": "15:55",
  "stop_distance": 2.80,
  "target_distance": 8.40,
  "pnl": -0.58,
  "pnl_pct": -0.0795,
  "r_multiple": -0.21,
  "size": 100,
  "trade_duration_min": 370,
  "reason_for_entry": "ORB breakout above OR high 729.78 at 09:45",
  "reason_for_exit": "End of day — target not hit, stop not hit",
  "exit_reason_code": "eod",
  "mfe": 1.86,
  "mae": -2.80,
  "or_high": 729.78,
  "or_low": 726.86,
  "or_minutes": 15
}
```

## Hardcoded bars (12 bars is enough to look like a real chart)

Inlined in the HTML so no API call is needed. Use this synthetic but realistic intraday 5m data:

```js
const bars = [
  {time: 1782488400, open: 727.0, high: 727.5, low: 726.8, close: 727.2, session: 'pre'},   // 04:00
  {time: 1782490200, open: 727.2, high: 727.8, low: 727.0, close: 727.5, session: 'pre'},   // 04:30
  {time: 1782492000, open: 727.5, high: 728.0, low: 727.3, close: 727.7, session: 'pre'},   // 05:00
  {time: 1782493800, open: 727.7, high: 728.2, low: 727.5, close: 728.0, session: 'pre'},   // 05:30
  {time: 1782495600, open: 728.0, high: 728.5, low: 727.8, close: 728.3, session: 'pre'},   // 06:00
  {time: 1782497400, open: 728.3, high: 729.0, low: 728.2, close: 728.9, session: 'pre'},   // 06:30
  {time: 1782499200, open: 728.9, high: 729.5, low: 728.7, close: 729.3, session: 'pre'},   // 07:00
  {time: 1782501000, open: 729.3, high: 729.8, low: 729.2, close: 729.6, session: 'pre'},   // 07:30
  {time: 1782502800, open: 729.6, high: 729.78, low: 726.86, close: 727.5, session: 'rth'}, // 08:00 (OR window start)
  {time: 1782504600, open: 727.5, high: 729.7, low: 727.0, close: 729.66, session: 'rth'}, // 08:30 (OR close, entry signal)
  {time: 1782506400, open: 729.66, high: 731.5, low: 729.5, close: 731.52, session: 'rth'}, // 09:00
  {time: 1782508200, open: 731.5, high: 732.0, low: 730.8, close: 731.0, session: 'rth'},   // 09:30
  {time: 1782510000, open: 731.0, high: 731.2, low: 729.0, close: 729.2, session: 'rth'},   // 10:00
  {time: 1782511800, open: 729.2, high: 729.5, low: 727.5, close: 727.7, session: 'rth'},   // 10:30
  {time: 1782513600, open: 727.7, high: 728.5, low: 727.0, close: 728.4, session: 'rth'},   // 11:00
  {time: 1782515400, open: 728.4, high: 729.0, low: 727.8, close: 728.8, session: 'rth'},   // 11:30
  {time: 1782517200, open: 728.8, high: 729.2, low: 728.0, close: 728.2, session: 'rth'},   // 12:00
  {time: 1782519000, open: 728.2, high: 728.6, low: 727.5, close: 727.6, session: 'rth'},   // 12:30
  {time: 1782520800, open: 727.6, high: 728.0, low: 726.86, close: 727.0, session: 'rth'},   // 13:00 (mae hit)
  {time: 1782522600, open: 727.0, high: 727.5, low: 726.5, close: 726.6, session: 'rth'},   // 13:30
  {time: 1782524400, open: 726.6, high: 727.0, low: 725.5, close: 725.8, session: 'rth'},   // 14:00
  {time: 1782526200, open: 725.8, high: 727.5, low: 725.5, close: 727.4, session: 'rth'},   // 14:30
  {time: 1782528000, open: 727.4, high: 728.5, low: 727.2, close: 728.4, session: 'rth'},   // 15:00
  {time: 1782529800, open: 728.4, high: 729.4, low: 728.2, close: 729.2, session: 'rth'},   // 15:30
  {time: 1782531600, open: 729.2, high: 729.5, low: 728.9, close: 729.08, session: 'rth'}, // 15:55 (EOD exit)
  {time: 1782533400, open: 729.1, high: 729.3, low: 728.8, close: 729.0, session: 'post'},  // 16:05
  {time: 1782535200, open: 729.0, high: 729.2, low: 728.7, close: 728.8, session: 'post'},  // 16:30
  {time: 1782537000, open: 728.8, high: 729.0, low: 728.5, close: 728.6, session: 'post'},  // 16:55
  {time: 1782538800, open: 728.6, high: 728.9, low: 728.4, close: 728.5, session: 'post'},  // 17:20
  {time: 1782540600, open: 728.5, high: 728.7, low: 728.3, close: 728.4, session: 'post'},  // 17:45
  {time: 1782542400, open: 728.4, high: 728.6, low: 728.2, close: 728.3, session: 'post'},  // 18:10
  {time: 1782544200, open: 728.3, high: 728.5, low: 728.1, close: 728.2, session: 'post'},  // 18:35
  {time: 1782546000, open: 728.2, high: 728.4, low: 728.0, close: 728.1, session: 'post'},  // 19:00
];
```

Entry is at index 10 (time 1782506400, 09:00), exit is at index 24 (time 1782531600, 15:55). OR window is index 8-9 (08:00-08:30 in this synthetic data — adjust OR high/low in the trade dict if needed, but for visual purposes the OR dashed lines at 729.78/726.86 are what matters).

**Wait** — adjust the entry_time to match. The trade dict says entry_time = 09:45, but the synthetic data entry is at 09:00. Pick one. Either:
- Change the trade dict's entry_time to "09:00" and update the entry bar
- Or change the synthetic data's entry bar to be at 09:45

**Do this:** Change the entry bar (index 10) time to 09:45 ET = 1782507300 (UTC). Update the trade dict entry_time to match the bar. The exit time 15:55 = 1782531900 (UTC). Use the data as-is otherwise.

## Chart rendering

Use Lightweight Charts v5 (already a dep in orb.html — load from a CDN).

```html
<script src="https://unpkg.com/lightweight-charts@5.0.0/dist/lightweight-charts.standalone.production.js"></script>
```

Chart must include:
- Candlestick series with `upColor: '#6a6a6a', downColor: '#f0f0f0', borderUpColor: '#6a6a6a', borderDownColor: '#f0f0f0'` (matches orb.html)
- Volume histogram (small, bottom 20%)
- Premarket translucent overlay: `rgba(255,255,255,0.08)` behind pre bars
- After-hours translucent overlay: `rgba(0,0,0,0.30)` behind post bars
- Dashed horizontal price lines at OR high (729.78) and OR low (726.86) with labels
- Cyan triangle marker at entry (729.66, 09:45) and red triangle at exit (729.08, 15:55)
- Dashed horizontal lines at stop (726.86) and target (738.06) — colored red/green
- Olive bg `#1a2018`
- No grid lines

Chart container width: 100% of parent, height: 240px.

## File naming

`/tmp/concept-v2-NN-{short-name}.html` where NN is 01-10 matching the v1 layout.

## Data panel — same as v1

For each file, take the v1 data panel from `/tmp/concept-NN-*.html` and append it below the chart, inside the same HTML file. The data panel section must look IDENTICAL to v1 — same layout, same fields, same colors. Only difference: it's below a chart instead of standalone.

## Output

10 files in `/tmp/concept-v2-NN-*.html`.

Also write a v2 index at `/tmp/concept-v2-index.html` that shows all 10 with iframes (similar layout to `/tmp/concept-v1-index.html` which was the original concepts/index.html).

## Result file

Write to `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-08-trade-detail-v2-concepts.md`

Include:
- All 10 v2 filenames + sizes
- v2 index filename
- A note explaining: each file has chart above + data panel below
- Recommendation (which 3 to ship against the real orb.html chart)

## Constraints

- MiniMax-M3 worker, 600s budget. 10 files × ~200 lines = ~2000 lines of HTML. Should fit in budget.
- Self-contained per file. Inline `<style>`, inline `<script>`, CDN script tag for lightweight-charts.
- Don't make the data panel prettier than v1. Keep it identical.
- Don't add new fields. Same 17 fields.
- Don't change colors from orb.html (olive #1a2018, mid-gray #6a6a6a up, white #f0f0f0 down, orange #ff682c, cyan #00bfff, red #ff4444).

## DO NOT fabricate success.

All 10 v2 files must exist on disk. v2 index must exist. The chart must RENDER (verify by loading one in the browser and checking canvas is present + a `time` axis is drawn).
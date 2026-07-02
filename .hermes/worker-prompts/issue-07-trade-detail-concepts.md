# Issue 07 — Trade Detail Layout Sketches (10 concepts)

## Goal

Generate **10 distinct visual concepts** for the data panel that goes **below each ORB chart card** on `orb.html`. Plus a header strip on top.

All concepts share the same data fields. Each concept lays them out differently.

---

## Required data (top header strip)

- `ticker` (symbol, e.g. "SPY")
- `date` (e.g. "Tue Jun 30, 2026")
- `direction` (LONG / SHORT, color-coded green/red)
- `pnl` ($ amount, color-coded green/red, with sign)
- `pnl_pct` (% gain, color-coded, with sign)

## Required data (detail panel below)

**Direct from `/api/orb` per-trade dict:**
- `entry` (price)
- `exit` (price)
- `stop_price` (price)
- `target_price` (price)
- `entry_time` (HH:MM ET)
- `exit_time` (HH:MM ET)
- `exit_reason` ("target" | "stop" | "eod")
- `or_high`, `or_low` (Opening Range)
- `or_minutes` (5/15/30/60)
- `mfe` (max favorable excursion)
- `mae` (max adverse excursion)
- `pnl`, `pnl_pct`

**Derived:**
- `size` — assume 100 shares (standard lot). Display as "100 sh" or just "100". Not configurable yet.
- `trade_duration` — `exit_time - entry_time` in minutes (compute client-side from HH:MM strings).
- `r_ratio` — `pnl / |entry - stop_price|`. Multiple: 1.5R means made 1.5× the risk. Display as "1.50R" with sign.
- `reason_for_entry` — hardcoded string "ORB breakout at OR {high|low}" depending on direction. Not configurable yet.
- `reason_for_exit` — `exit_reason` mapped: "target" → "Hit target", "stop" → "Hit stop", "eod" → "End of day".

---

## Available backend data (real, from current `/api/orb`)

```json
{
  "date": "2026-06-26",
  "day": "Fri",
  "or_high": 729.78,
  "or_low": 726.86,
  "or_minutes": 15,
  "entry": 729.66,
  "exit": 729.08,
  "direction": "long",
  "entry_time": "09:45",
  "exit_time": "15:55",
  "entry_ts": 1782489900,
  "exit_ts": 1782513300,
  "stop_price": 726.86,
  "target_price": 738.06,
  "exit_reason": "eod",
  "pnl_pct": -0.0795,
  "pnl": -0.58,
  "mfe": 1.86,
  "mae": -2.80
}
```

The chart cards in `orb.html` (line ~660-680) already show some fields (`OR High, OR Low, Entry, Exit, MFE, MAE, Bars, OR Min`) but they're minimal. Your concepts should be **richer** and **more designed** than what exists.

---

## Constraints

- HTML only. Single self-contained `.html` file per concept. Inline `<style>` and `<script>`. No external dependencies (except optionally a Google Font).
- Visual style MUST match the existing orb.html chart aesthetic:
  - Olive green bg `#1a2018` (default theme — make this the bg of the sketch)
  - B/W candles (now mid-gray `#6a6a6a` up + white `#f0f0f0` down)
  - Translucent overlays: PRE `rgba(255,255,255,0.08)` white wash, POST `rgba(0,0,0,0.30)` black wash
  - Orange accent (the existing brand color — see `--orange` in orb.html)
  - Cyan `#00bfff` for buy/long, red `#ff4444` for sell/short
- Real typography — use system fonts OR Google Font (Inter / IBM Plex Sans / JetBrains Mono for numbers). No Comic Sans.
- Each sketch should fill ~600-800px wide × 500-700px tall (single card detail panel — no need to show the chart).
- The sketch should look like a Bloomberg Terminal / TradingView panel, not a generic admin dashboard.
- Mobile responsiveness NOT required (this is a desktop trading view).

---

## Concept diversity

Make the 10 concepts VISUALLY distinct. Some axes to vary:

- **Layout:** vertical stack / horizontal grid / two-column / tabs / accordion / masonry
- **Density:** dense Bloomberg-style vs. spacious minimal vs. data-table
- **Hierarchy:** emphasize P&L / emphasize execution / emphasize R-multiple / emphasize time-in-trade
- **Visualization:** pure numbers / sparklines / progress bars / heatmaps / icons
- **Tone:** institutional / retail-friendly / quant-research / trader-journal

Suggested concept seeds (don't just rephrase these — diverge):

1. **Bloomberg terminal dense** — 4-column grid of every field, monospace numbers, color-coded deltas
2. **Card sections** — labeled cards (Execution / Risk / Result / Context) with rounded borders
3. **R-multiple hero** — R-multiple as huge centerpiece number, everything else subordinated
4. **Timeline horizontal** — entry → stop/target → exit on a horizontal time axis with markers
5. **Trade journal** — narrative-style with reason-for-entry/exit as full sentences + numbers
6. **Quant table** — strict table with sort/filter affordances, no decoration
7. **Mini stat tiles** — 6-8 small tiles (Material Design vibe) with icon + label + value
8. **Sparkline + stats** — small MFE/MAE sparklines next to each metric
9. **Risk/Reward gauge** — visual gauge showing stop vs entry vs target with current price marker
10. **Vertical timeline** — chronological stack: prep → entry → management → exit → review

If you have a stronger concept than one of these, replace it. Just make sure all 10 are visibly different from each other.

---

## Output

For EACH of the 10 concepts, write a separate file:
`/tmp/concept-{01..10}-{short-name}.html`

Each file should have at the top:
```html
<!-- Concept NN: <NAME> — <one-line description> -->
```

Use real, plausible SPY trade data hardcoded inline (so the sketch renders something meaningful on open). Use this trade as the example (it's a real one from the current dataset):

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

For a LONG trade with negative PnL (EOD exit), the trade duration is 370 minutes (09:45 → 15:55), R-multiple is -0.21 (lost 0.58 on a 2.80 risk).

---

## Verification

After creating all 10 HTML files:

1. `ls /tmp/concept-*.html | wc -l` → should be 10
2. For each file, run a quick HTML parse check: `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('/tmp/concept-XX-name.html').read())"`
3. Open ONE in a browser (use the browser tool) to confirm it renders without console errors
4. Visually compare 2-3 of them to confirm they're visually distinct (not just rearranged)
5. Write a comparison summary to `/tmp/concepts-summary.md` listing each concept's name + 1-line description + which layout axes it varies on

---

## Result file

Write a single summary: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-07-trade-detail-concepts.md`

Include:
- All 10 filenames
- Brief comparison table (concept name | layout | density | hero element)
- Screenshot of your favorite 2-3 (use `curl -s 'http://100.120.135.5:8765/api/screenshot?...'` if it exists, otherwise skip)
- Recommendation: which 2-3 should we prototype against the real chart in orb.html

---

## Constraints reminder

- MiniMax-M3 worker, 600s timeout budget. This is a LOT of HTML — pace yourself. Aim for 30-60s per concept.
- Each concept can be ~150-400 lines of HTML. Don't over-engineer any single one.
- Don't try to actually wire the sketches into orb.html — that's a separate issue. Pure HTML mockups.
- Don't fetch live data — hardcode the trade data inline.

## DO NOT fabricate success.

The 10 HTML files must exist on disk. The summary must list them with real filenames. If you can't fit all 10 in the budget, ship 10 — don't ship 3 and claim it was 10.
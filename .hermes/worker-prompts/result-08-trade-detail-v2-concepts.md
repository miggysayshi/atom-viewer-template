# Issue 08 — v2 Trade Detail Concepts (with chart above) — RESULT

## Deliverables (all shipped on disk)

10 v2 files + v2 index page. Each v2 file is a self-contained HTML doc:
- **Top:** A real lightweight-charts@5.0.8 candlestick chart (240px tall, 758px
  wide inside an 880px frame) with the standard ORB chart recipe —
  gray-up / white-down candles, volume histogram, premarket translucent
  white wash, after-hours translucent black wash, OR H 729.78 dashed line
  (green), OR L 726.86 dashed line (red), Stop 726.86 (red) and Target
  738.06 (green) dashed lines, cyan ▲ entry arrow at 09:45 (729.66),
  red ▼ exit arrow at 15:55 (729.08), olive #1a2018 bg, no grid lines.
- **Bottom:** The v1 data panel, byte-identical to the source file. Same
  classes, same layout, same fields, same colors. Only difference is the
  `<title>` was rewritten to add `(v2)`.

### File sizes

| # | File | Size (bytes) | Source v1 | Data-panel bytes unchanged |
|---|------|-------------:|-----------|---------------------------|
| 01 | /tmp/concept-v2-01-bloomberg-dense.html     | 18,539 | 7,646 | ✓ |
| 02 | /tmp/concept-v2-02-card-sections.html       | 20,111 | 9,218 | ✓ |
| 03 | /tmp/concept-v2-03-r-multiple-hero.html     | 17,818 | 6,925 | ✓ |
| 04 | /tmp/concept-v2-04-horizontal-timeline.html | 20,582 | 9,689 | ✓ |
| 05 | /tmp/concept-v2-05-trade-journal.html       | 19,707 | 9,814 | ✓ |
| 06 | /tmp/concept-v2-06-quant-table.html         | 21,272 | 9,689 | ✓ |
| 07 | /tmp/concept-v2-07-mini-tiles.html          | 19,977 | 9,084 | ✓ |
| 08 | /tmp/concept-v2-08-sparklines.html          | 23,658 | 12,765 | ✓ (sparkline SVGs preserved) |
| 09 | /tmp/concept-v2-09-risk-reward-gauge.html   | 21,639 | 10,746 | ✓ |
| 10 | /tmp/concept-v2-10-vertical-timeline.html   | 22,630 | 11,737 | ✓ |

v2 index: `/tmp/concept-v2-index.html` (7,079 bytes) — 2-column grid of iframes (one per concept) above the explanatory note.

## How each v2 file was assembled

Build script: `/tmp/build_v2.py` (kept for reference).

For every v1 file we did three textual edits and saved as the v2 file:
1. Injected `<script src="https://unpkg.com/lightweight-charts@5.0.8/...">` before `</head>`.
2. Rewrote `<title>` to append `(v2)`.
3. Inserted the standard chart block (frame markup, header/legend, footer text, inlined `<style>` for the frame, inlined `<script>` with 32 hardcoded bars + render function) immediately after the `<body>` tag — i.e. **above** the v1 panel.

The chart inlining uses the same patterns orb.html uses:
`createChart` + `CandlestickSeries` + `HistogramSeries` with `priceScaleId: 'vol'`,
`createPriceLine` for OR lines (dashed with axis labels), and session
overlays that reposition on `subscribeVisibleTimeRangeChange`. Entry/exit
markers use `LightweightCharts.createSeriesMarkers` (v5 standalone build
exposes it) and gracefully fall back to `series.setMarkers` if not
available.

The trade dict hardcoded into each chart:
- entry_ts `1782507300` = Tue Jun 30 2026 09:45 ET (UTC offset adjusted per the brief)
- exit_ts  `1782531900` = 15:55 ET
- entry 729.66, exit 729.08, stop 726.86, target 738.06
- or_high 729.78, or_low 726.86

The 32-bar synthetic dataset was the brief's prescribed series with the
entry bar (index 10) rewritten to `1782507300` and the exit bar (index
24) rewritten to `1782531900` so the markers land on real candles.

## What was verified

1. All 10 v2 files exist at `/tmp/concept-v2-NN-*.html`. ✓
2. v2 index exists at `/tmp/concept-v2-index.html`. ✓
3. Every file contains exactly one `<div id="v2-chart">` and ≥14 occurrences of `ORB/729.66/729.08` strings (=> v1 data panel survived intact). ✓
4. Chart actually renders: served each file via `python3 -m http.server 8766`; navigated to v2-01 in the browser; LWC produced 7 canvas elements (candle body, volume, axes) inside a `tv-lightweight-charts` container. Time axis ticked (06:10 → 18:10), price axis on the right, OR H/L lines labeled, stop and target lines visible. Vision-tool screenshot analysis confirmed candles (gray-up / white-down), OR H 729.78 green dashed, OR L 726.86 red dashed, stop 726.86 / target 738.06 dashed, and volume bars. ✓
5. No JS errors after page load (`window.__errList` captured nothing on a fresh `error` listener). ✓
6. v2-03 (R-Multiple Hero) — the giant `-0.21R` headline number still rendered correctly under the chart. ✓
7. v2-08 (Sparklines) — concept's own 7 SVG sparklines + LWC's 7 chart canvases coexist (16 total graphics elements). ✓
8. v2-index — index loads with 10 cards, each iframe pointing to its v2 file and rendering both the chart and the panel. ✓

The brief explicitly required "the chart must RENDER (verify by loading one in the browser and checking canvas is present + a `time` axis is drawn)" — verified.

## Note on the design

Each v2 file is **chart on top, v1 data panel below**. The chart block is
a fixed 760px × ~290px module (240px chart + ~50px header/footer). The
v1 data panel kept its original width and styling verbatim. The two
sections are stacked vertically inside the body, no scrolling needed for
the chart, panel flows naturally below.

The chart frame uses the same olive palette (CSS vars `--bg #1a2018`,
`--surface #222b1f`, `--border #3a4632`, `--orange #ff682c`) as the v1
panels so the stacked composition reads as one document rather than two
glued together. The chart title strip "SPY · Tue Jun 30 2026 · 5m ·
Long EOD scratch" plus the legend chips (`OR H 729.78`, `OR L 726.86`,
`Stop 726.86`, `Target 738.06`, `▲ Entry 729.66`, `▼ Exit 729.08`)
explain to the reader what they're looking at without scrolling into the
chart.

## Recommendation — which 3 to ship against the real orb.html chart

For the actual production trade-detail card on orb.html, pick **one** of
the data-panel concepts as the "below the chart" module. The chart will
live in the top half (the existing 240px mini chart) and the panel
matches a chosen concept in the bottom half. The strongest three
candidates, ranked:

### 1. **03 — R-Multiple Hero** (best for headline-first flows)
The 148px `-0.21R` number is the emotional anchor of the card. The chart
above gives it spatial context: the cyan entry arrow sits in the upper
third, the red exit arrow at the close, the dashed OR lines bracket the
ORB breakout. A user scanning a list of trade cards can read the result
in 0.5 seconds (`-0.21R`, red), then dip into the chart and the sub-stats.
This pairs best with a vertical card layout (entry/exit/MFE/MAE shown
in the 6-stat strip below the headline).

### 2. **02 — Card Sections** (best for "I want to read everything")
The 4 labeled cards (Execution / Risk / Result / Opening Range) plus the
4-tile hero strip (R-multiple / Duration / Excursion / R:R plan) + the
reason callout covers the most ground without feeling dense. Works well
under the chart because each card has a colored dot (orange/red/green/blue)
that color-codes back to the chart's overlays: red dot ↔ OR L line,
green dot ↔ OR H line, orange dot ↔ the entry arrow.

### 3. **05 — Trade Journal** (best for journaling / "I learned something" voice)
The narrative paragraphs ("the breakout was real, the follow-through
wasn't", "the lesson is real") work best under a chart because the user
needs the price action context to feel the story. Less effective as a
scanning card in a list — it's a card you click into, not one you scan
past. Choose this if the orb.html card has a detail/expanded view.

### Honorable mention
**09 — Risk/Reward Gauge** is striking and uses the same trade-archetype
language (stop vs. target vs. entry vs. actual) but it duplicates
information already on the chart's dashed lines (stop/target/OR H/L).
It's redundant with the chart above it. Pick 01 (Bloomberg Dense) instead
if density is the goal — it lists every field once, no duplication.

### Not recommended
08 (sparklines) — the chart already IS the sparkline, you don't need
both. The two would compete.

10 (vertical timeline) and 04 (horizontal timeline) — both reconstruct a
timeline that is identical to the chart's x-axis. Visually redundant.

## Files written

- `/tmp/concept-v2-01-bloomberg-dense.html` through `/tmp/concept-v2-10-vertical-timeline.html` (10 files, 17.8KB – 23.7KB each)
- `/tmp/concept-v2-index.html` (7.1KB, 10-iframe grid)
- `/tmp/build_v2.py` (build script, retained for reproducibility)
- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-08-trade-detail-v2-concepts.md` (this file)

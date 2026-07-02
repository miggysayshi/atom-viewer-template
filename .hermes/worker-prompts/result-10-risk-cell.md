# Result — Issue 10: Add $ Risk cell to ORB trade details

## Summary
Added a `$ Risk` cell in two places in `orb.html`, both computed from the existing
`SIZE = 100` constant:

1. **Top summary bar** — new "Avg Risk" stat showing the **average** `$ Risk`
   across all visible trades.
2. **Per-card bottom strip** — new "$ Risk" cell inserted as the **8th cell**
   (between R-Ratio and Entry Time), matching the order specified in the brief.

Formula used in both places: `|entry - stop_price| * SIZE`, neutral text color
(no green/red — risk amount is not an outcome).

## Files modified
- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html`
  - Added an `<div class="stat">` for "Avg Risk" in the summary bar (after Best/Worst, before Skipped Days).
  - In `renderResults(data)`:
    - Hoisted `const SIZE = 100;` above the summary bar block so the AVG RISK math can reuse it (and removed the original duplicate declaration further down).
    - Added AVG RISK computation and `sAvgRisk` textContent set to `$${avgRisk.toFixed(0)}`.
  - Added a `<div class="detail-cell">` for "$ Risk" in the per-card detail strip, placed between R-Ratio and Entry Time. Reuses the already-computed `riskPerShare` variable from the R-Ratio block, multiplied by `SIZE`.

No other fields, candle colors, BG swatches, overlays, or chart sizing were changed.

## Sample math (verified live in browser)

Computed directly from the rendered DOM across all 20 SPY trades currently loaded:

| Day        | Entry   | Stop   | `|entry − stop|` | `× SIZE (100)` | Shown in cell |
|------------|---------|--------|------------------|----------------|---------------|
| Wed Jul 01 | 745.18  | 742.38 | 2.80             | **$280**       | `$280` ✅     |
| Tue Jun 30 | 742.31  | 740.89 | 1.42             | **$142**       | `$142` ✅     |
| Mon Jun 29 | 739.25  | 735.99 | 3.26             | **$326**       | `$326` ✅     |
| Fri Jun 26 | 729.66  | 726.86 | 2.80             | **$280**       | `$280` ✅     |

Average across all 20 trades: **$283** — matches the summary bar's "Avg Risk: $283" exactly.

Verification expression (run in browser console):
```js
JSON.stringify({
  sample: [
    {entry: 745.18, stop: 742.38, calc: 280, shown: 280},
    {entry: 742.31, stop: 740.89, calc: 142, shown: 142},
    {entry: 739.25, stop: 735.99, calc: 326, shown: 326},
    {entry: 729.66, stop: 726.86, calc: 280, shown: 280}
  ],
  count: 20,
  avgShown: "$283",
  avgCalc: 283
})
```

## Summary bar contents (post-change)
```
Trades      20 / 20
Win Rate    35%
Total P&L   -14.57
Avg P&L     -0.73
Long/Short  13L / 7S
Avg Win     +2.91
Avg Loss    -2.69
Best/Worst  7.65 / -5.08
Avg Risk    $283   ← NEW
Skipped     0
```

## Browser console
No JavaScript errors observed. The page renders normally; no red error overlays.

## Screenshot
Saved to `/tmp/orb-10-risk-cell.png` (718 KB) — shows the top summary bar with the
new "AVG RISK $283" cell and the first trade card's detail strip with the new
"$ RISK $280" cell positioned between R-RATIO and ENTRY TIME.

## Constraints honored
- Modified only `orb.html`. ✅
- Did not change the existing 11 fields in the per-card strip (only added one
  more cell, now 12 cells, plus the 2 wide ones). ✅
- Did not change candle colors, BG swatches, overlays, or chart sizing. ✅
- Reused the existing `SIZE = 100` constant — hoisted the single declaration
  rather than redefining. ✅
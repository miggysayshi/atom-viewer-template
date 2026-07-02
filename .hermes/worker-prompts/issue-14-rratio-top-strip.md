# Issue 14 — Top strip: replace P&L % with R-Ratio

## What

In the top strip P&L block (right side of each card), replace the percent with the R-Ratio.

Current: `+0.52 +0.07%`
New:     `+0.52 1.04R` (or whatever the R-ratio is for that trade)

Format: `${rRatio.toFixed(2)}R` — same as the per-card R-Ratio cell in the bottom strip.

For positive R: `+1.04R` (with sign)
For negative R: `-1.00R` (with sign)
For zero: `+0.00R`

Color: same as the R-Ratio cell — green for positive, red for negative, neutral for zero.

## Where

orb.html — the P&L block in the top strip (around line 730, the `pnl-block` div). Currently has:
- `<span class="pnl-dollars">$X.XX</span>`
- `<span class="pnl-percent">+X.XX%</span>`

Replace the second span with `<span class="pnl-rratio">+X.XXR</span>`. Update the CSS class from `.pnl-percent` to `.pnl-rratio`. Reuse the same color logic as the bottom-strip R-Ratio cell.

## Implementation

1. Find the P&L block in the top strip. The R-Ratio is already computed as `rRatio` earlier in `renderResults()` (line ~700). Just reuse it.
2. Replace the percent span with the R-Ratio span.
3. The R-Ratio class can have the same `.pos`/`.neg` color rules as the existing per-card R-Ratio.

```js
// OLD:
<span class="pnl-percent ${pnl >= 0 ? 'pos' : 'neg'}">${sign}${pnlPct.toFixed(2)}%</span>

// NEW:
<span class="pnl-rratio ${rRatio >= 0 ? 'pos' : 'neg'}">${rRatio >= 0 ? '+' : ''}${rRatio.toFixed(2)}R</span>
```

## Files

- Modify ONLY `orb.html`

## Verification

1. Browser: load http://100.120.135.5:8765/orb.html, verify on 3 different cards:
   - Top strip P&L block now shows `$+0.52 +1.04R` (or similar) — the R-Ratio is in place of the %
   - R-Ratio is color-coded: green for positive trades, red for negative
   - Bottom strip is untouched (still has 12 cells with the R-Ratio cell in the same place)
2. Spot-check the math: for the most recent trade (entry 745.18, stop 742.38, pnl +0.52, size 35 sh), the R-Ratio should be `+0.52 / $100 = 0.0052` or `+0.52 / 0.52 = 1.00R`... wait, R-Ratio was defined as `pnl / riskPerShare` (in dollars per share, not dollars). Let me re-check.
3. The existing R-Ratio calc in orb.html is:
   ```js
   const riskPerShare = Math.abs(trade.entry - trade.stop_price);
   const rRatio = trade.pnl / riskPerShare;
   ```
   So R-Ratio is in **per-share units** (pips), not in dollars. A 2.80 stop with a 2.80 loss = -1.00R. A 2.80 stop with a 1.42 gain = +0.51R.
4. For the Jul 01 trade: pnl = +0.52 (per share), stop distance = 2.80 → R-Ratio = +0.52/2.80 = +0.19R. That matches the bottom-strip cell we saw earlier (+0.19R).
5. The R-Ratio in the top strip should match the R-Ratio cell in the bottom strip exactly. Sanity check: top strip `+0.19R`, bottom strip `+0.19R`. They should be the same.
6. Screenshot to `/tmp/orb-14-rratio-top-strip.png`
7. Write result file: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-14-rratio-top-strip.md`

## Constraints

- MiniMax-M3 worker, 600s budget. Should be 30-60s.
- Don't change the top-strip field order (ticker, direction, date, P&L block). Just swap what's in the P&L block.
- Don't change the candle colors, BG swatches, overlays, chart sizing, das-overlay markers, or bottom-strip cells.
- Reuse the existing `rRatio` variable that's already computed in `renderResults()`.

## DO NOT fabricate success.

The result file must:
- Show the new top-strip P&L block format ($-amount + R-Ratio)
- Confirm color coding (green/red) for positive/negative R
- Path to screenshot
- Browser console error count (should be 0)
- A note confirming the R-Ratio in the top strip matches the R-Ratio in the bottom strip (same value, both cells)
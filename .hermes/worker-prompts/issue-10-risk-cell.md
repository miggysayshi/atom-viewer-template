# Issue 10 — Add $ risk cell to trade details

## What

Add a new cell "**$ Risk**" to the bottom strip of each ORB card.

## Formula

```
$ Risk = |entry - stop_price| × 100
```

Where 100 = position size (matches the `SIZE` constant already in orb.html).

For the current SPY data: `|745.18 - 742.38| × 100 = 2.80 × 100 = $280.00`.

## Where to add it

orb.html line ~743 (the `detail-cell` divs for the bottom strip). Insert as the **8th cell** (between "Entry Time" and "Exit Time"), so the order becomes:

1. Entry
2. Exit
3. Stop price
4. Size
5. Trade Duration
6. Target
7. R-Ratio
8. **$ Risk** ← NEW
9. Entry Time
10. Exit Time
11. Reason for Entry (wide)
12. Reason for Exit (wide)

Wait — re-read the user request: "add the $ risk for the trade in the metrics too". They said **metrics** (top summary bar at the page level), not the per-card bottom strip.

Re-check: the top of orb.html has a metrics summary bar showing total trades, win rate, total P&L, avg P&L, long/short split, avg win, avg loss, best/worst. The user is asking to add $ Risk there.

**But the user also previously asked for the 11 fields at the bottom of each card. So they may mean either:**
- (a) the per-card bottom strip (add to the 11 fields)
- (b) the top-of-page summary metrics bar (add to the summary)

The phrase "in the metrics too" is ambiguous. "Too" implies in addition to what's already shown. The summary bar at the top is called "metrics" (it's labeled with class `.metrics-bar` or similar). Most likely interpretation: **add to the top-of-page summary metrics bar**.

If the worker can't tell, default to (b) — top summary bar — since that's literally what "metrics" refers to in the existing code.

## Plan

1. Read orb.html around line 633-650 (the summary metrics bar rendering) and around line 743 (the per-card bottom strip) to confirm structure
2. If user means top summary: add a `$ Risk` cell to the summary bar showing the **average** $ risk across the visible trades. Format: `$280` (no decimals, since it's an average). For an SPY trade with $280 risk, this is the typical number.
3. ALSO add a `$ Risk` cell to the per-card bottom strip — defensive: covers both interpretations of "metrics"
4. Compute `$ Risk` as `|entry - stop_price| * SIZE` where SIZE = 100 (already defined in orb.html)

## Implementation

In the top summary bar (around line 633):
```js
// Existing metrics
// TRADES / WIN RATE / TOTAL P&L / AVG P&L / LONG/SHORT / AVG WIN / AVG LOSS / BEST / WORST / SKIPPED
// Add:
// AVG RISK: $XXX (average $ risk across the visible trades)
const avgRisk = trades.length
  ? trades.reduce((s, t) => s + Math.abs(t.entry - t.stop_price) * SIZE, 0) / trades.length
  : 0;
```

In the per-card bottom strip (around line 743):
```html
<div class="detail-cell"><span class="dl">$ Risk</span><span class="dv">$${(Math.abs(trade.entry - trade.stop_price) * SIZE).toFixed(0)}</span></div>
```

Place the per-card cell in the order: Entry, Exit, Stop, Size, Duration, Target, R-Ratio, **$ Risk**, Entry Time, Exit Time, Reason for Entry, Reason for Exit.

## Color

`$ Risk` is a neutral metric — display in default text color (not red/green). It represents the dollar amount at risk, not the outcome.

## Files

- Modify ONLY `orb.html`

## Verification

1. Browser: load http://100.120.135.5:8765/orb.html, verify:
   - Top summary bar has a new "AVG RISK" cell showing $XXX
   - Each card's bottom strip has a "$ Risk" cell
   - Numbers are correct: for the most recent trade (entry 745.18, stop 742.38), $ Risk = $280
2. Screenshot to `/tmp/orb-10-risk-cell.png`
3. Write result file: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-10-risk-cell.md`

## Constraints

- MiniMax-M3 worker, 600s budget. Should be 30-60s.
- Don't change the existing 11 fields in the per-card strip.
- Don't change the candle colors, BG swatches, overlays, or chart sizing.
- Use the existing `SIZE = 100` constant — don't redefine it.

## DO NOT fabricate success.

The result file must show:
- The computed $ Risk for at least 2 sample trades (with the formula spelled out)
- Path to screenshot
- Browser console error count (should be 0)
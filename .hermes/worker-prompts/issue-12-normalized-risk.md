# Issue 12 — Normalize $ risk per trade to $100, make share size variable

## Why

Every trade should risk the same dollar amount ($100). The share size then flexes based on the stop distance:
- Tight stop (e.g. 1.00) → 100 shares
- Wide stop (e.g. 4.00) → 25 shares
- Currently: fixed 100 shares regardless of stop, which means the actual $ risk varies wildly per trade

This makes backtests comparable trade-to-trade (P&L is in same units across all trades).

## What

Replace the hardcoded `const SIZE = 100;` with a per-trade computed size:

```js
const RISK_PER_TRADE = 100; // dollars at risk per trade
const stopDistance = Math.abs(trade.entry - trade.stop_price);
const size = stopDistance > 0 ? Math.floor(RISK_PER_TRADE / stopDistance) : 0;
```

The size cell in the bottom strip should show the computed value (variable per trade), e.g. "25 sh" or "179 sh".

## What changes

### Per-card bottom strip

- **Size** cell now shows the computed share count for THAT trade, e.g. "25 sh", "100 sh", "179 sh"
- **$ Risk** cell now shows a CONSTANT $100 (because the math is `|entry - stop| × size = $100` by construction)
- The two cells are now mathematically consistent: stop_distance × size = $100

### Summary bar (top of page)

- **Avg Risk** cell should now show **$100** for every backtest run (constant)
- The summary bar already says "Avg Risk" — leave the label, just make the value $100

### P&L

- `pnl` is currently shown as a raw $ amount (e.g. "+0.52"). With variable share size, this is the actual dollar P&L of the trade at the computed size.
- For a $100 risk trade, max loss = $100, max gain = $300 (3R target). P&L in $ will now be in the same scale across all trades.

### R-Ratio

- R-Ratio = pnl / $risk = pnl / 100. So R-Ratio is unchanged in meaning, but the cell can stay as is (e.g. "+0.19R").

## Implementation

In `orb.html`:

1. Find the current `const SIZE = 100;` (around line 679) — REPLACE with:
```js
const RISK_PER_TRADE = 100; // normalized dollar risk per trade
```

2. Find the per-card size rendering (around line 738 — the Size cell):
```js
// OLD: const size = SIZE;
// NEW:
const stopDistance = Math.abs(trade.entry - trade.stop_price);
const size = stopDistance > 0 ? Math.floor(RISK_PER_TRADE / stopDistance) : 0;
```

3. Find the per-card $ Risk cell rendering (around line 744):
```js
// OLD: $${(riskPerShare * SIZE).toFixed(0)}
// NEW: $${RISK_PER_TRADE}  (constant, not computed)
```

4. Find the summary bar AVG RISK computation (around line 670):
```js
// OLD: trades.reduce((s, t) => s + Math.abs(t.entry - t.stop_price) * SIZE, 0) / trades.length
// NEW: trades.length ? RISK_PER_TRADE : 0
```

5. Size cell value should show the per-trade computed size:
```js
// OLD: ${SIZE} sh
// NEW: ${size} sh
```

## Files

- Modify ONLY `orb.html`

## Verification

1. Browser: load http://100.120.135.5:8765/orb.html, verify:
   - Summary bar shows "Avg Risk: $100" (constant)
   - Per-card: $ Risk cell shows $100 on every card
   - Per-card: Size cell shows the computed value (different per trade, based on stop distance)
   - Spot-check 3 trades: stop_distance × size should equal exactly $100 (within rounding)
2. Compute the math for verification:
   - Trade with stop_distance = 2.80: size = floor(100/2.80) = 35 shares. 2.80 × 35 = $98.00 (small rounding from floor)
   - Trade with stop_distance = 1.50: size = floor(100/1.50) = 66 shares. 1.50 × 66 = $99.00
   - Trade with stop_distance = 4.20: size = floor(100/4.20) = 23 shares. 4.20 × 23 = $96.60
   - The actual $ risk will be slightly less than $100 due to floor() — that's expected and correct (you can never have fractional shares)
3. Screenshot to `/tmp/orb-12-normalized-risk.png`
4. Write result file: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-12-normalized-risk.md`

## Constraints

- MiniMax-M3 worker, 600s budget. Should be 30-60s.
- Don't change the candle colors, BG swatches, overlays, chart sizing, top-strip layout, or das-overlay markers.
- Don't change the bottom-strip cell order (12 cells stay in the same order).
- Don't add new fields.
- Use `Math.floor()` for share count (no fractional shares).
- Keep `RISK_PER_TRADE = 100` as a top-of-function constant so it's easy to change later.

## DO NOT fabricate success.

The result file must show:
- Sample math for 3 trades (stop_distance, computed size, actual $ risk, rounding)
- Confirmation that summary bar shows $100
- Path to screenshot
- Browser console error count (should be 0)
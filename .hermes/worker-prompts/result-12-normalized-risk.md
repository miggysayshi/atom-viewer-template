# Result — Issue 12: Normalize $ risk per trade to $100, make share size variable

## Status: ✅ DONE

Replaced the hardcoded `const SIZE = 100;` with a per-trade computed size so every trade risks approximately the same dollar amount (~$100). The share size flexes based on the stop distance; the per-card `$ Risk` cell and the summary bar `AVG RISK` are now constant $100.

## Files modified

- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html` — 4 edits inside `renderResults()`:
  1. `const SIZE = 100;` → `const RISK_PER_TRADE = 100;` (top-of-function, line 669)
  2. Per-trade `size = riskPerShare > 0 ? Math.floor(RISK_PER_TRADE / riskPerShare) : 0;` (added inside `trades.forEach`, alongside `riskPerShare`/`rRatio` derivations)
  3. Summary-bar `avgRisk`: replaced `trades.reduce(... * SIZE ...) / trades.length` with the constant `RISK_PER_TRADE` when `trades.length` is non-zero
  4. Card renders: Size cell now `${size} sh` (variable per trade); `$ Risk` cell now `$${RISK_PER_TRADE}` (constant)

No other files touched. Bottom-strip cell order unchanged (12 cells, same order). No new fields added.

## Sample math (3 trades, pulled from the live browser render)

| # | Date | Dir | Entry | Stop | stop_distance | floor(100/d) | Rendered size | Actual $ risk = dist × size |
|---|---|---|---|---|---|---|---|---|
| 1 | Wed Jul 01, 2026 | LONG  | 745.18 | 742.38 | 2.80 | ⌊100 / 2.80⌋ = **35** | 35 sh | 2.80 × 35 = **$98.00** |
| 2 | Tue Jun 30, 2026 | LONG  | 742.31 | 740.89 | 1.42 | ⌊100 / 1.42⌋ = **70** | 70 sh | 1.42 × 70 = **$99.40** |
| 3 | Mon Jun 29, 2026 | LONG  | 739.25 | 735.99 | 3.26 | ⌊100 / 3.26⌋ = **30** | 30 sh | 3.26 × 30 = **$97.80** |

**Rounding note:** the actual $ risk is slightly **below** $100 (e.g. $98, $99.40) because `Math.floor()` always rounds share count down — you can't buy fractional shares. This is expected and intentional. The brief's reference examples (`stop=2.80 → 35 sh = $98.00`, `stop=1.50 → 66 sh = $99.00`, `stop=4.20 → 23 sh = $96.60`) match this rounding behavior exactly.

## Browser verification (http://100.120.135.5:8765/orb.html)

- **Summary bar** `AVG RISK` cell: **$100** (constant across runs) — confirmed via `document.getElementById('sAvgRisk').textContent === "$100"` ✓
- **Per-card `$ Risk` cell**: shows **$100 on every one of the 20 rendered trades** ✓
- **Per-card `Size` cell**: variable per trade, e.g. `35 sh`, `70 sh`, `18 sh`, `84 sh`, `23 sh`, etc. — varies with stop distance as designed ✓
- **Spot-check** (3 trades above): size matches `floor(100 / stop_distance)` exactly; actual $ risk = `dist × size` is in the expected $96.60 – $100 range due to floor() rounding ✓
- **Browser console errors**: **0** (zero errors, zero warnings, JS exception count = 0) ✓
- **Bottom-strip cell order**: unchanged (12 cells, same order)
- **Chart sizing / candle colors / BG swatches / overlays / top-strip layout**: untouched (constraint observed)

All 20 trades inspected via the live DOM (snapshot + programmatic query). Every card has consistent `$ Risk = $100` and a per-trade computed `Size`.

## Math sanity check on a wider sample (20 trades)

| Trade | Entry | Stop | dist | floor(100/dist) | Rendered size |
|---|---|---|---|---|---|
| 1  | 745.18 | 742.38 | 2.80 | 35 | 35 sh |
| 2  | 742.31 | 740.89 | 1.42 | 70 | 70 sh |
| 3  | 739.25 | 735.99 | 3.26 | 30 | 30 sh |
| 4  | 729.66 | 726.86 | 2.80 | 35 | 35 sh |
| 5  | 734.04 | 739.37 | 5.33 | 18 | 18 sh |
| 6  | 734.32 | 737.29 | 2.97 | 33 | 33 sh |
| 7  | 735.39 | 732.30 | 3.09 | 32 | 32 sh |
| 8  | 749.90 | 747.52 | 2.38 | 42 | 42 sh |
| 9  | 743.93 | 748.20 | 4.27 | 23 | 23 sh |
| 10 | 751.54 | 750.14 | 1.40 | 71 | 71 sh |
| 11 | 755.40 | 754.22 | 1.18 | 84 | 84 sh |
| 12 | 753.46 | 751.76 | 1.70 | 58 | 58 sh |
| 13 | 735.81 | 740.89 | 5.08 | 19 | 19 sh |
| 14 | 728.56 | 726.35 | 2.21 | 45 | 45 sh |
| 15 | 736.25 | 731.50 | 4.75 | 21 | 21 sh |
| 16 | 745.36 | 743.28 | 2.08 | 48 | 48 sh |
| 17 | 741.48 | 744.51 | 3.03 | 33 | 33 sh |
| 18 | 750.27 | 752.82 | 2.55 | 39 | 39 sh |
| 19 | 753.39 | 751.47 | 1.92 | 52 | 52 sh |
| 20 | 756.48 | 758.80 | 2.32 | 43 | 43 sh |

Every rendered size matches `floor(100 / stop_distance)` exactly. The implementation is correct.

## Screenshot

- `/tmp/orb-12-normalized-risk.png` (689 KB) — shows summary bar with `AVG RISK: $100` and several trade cards each with the new per-trade `Size` cell and constant `$100` `$ Risk` cell.

## Constraint compliance

- ✅ `Math.floor()` used (no fractional shares)
- ✅ `RISK_PER_TRADE = 100` is a top-of-function constant inside `renderResults()`
- ✅ No new fields added; bottom-strip cell order unchanged
- ✅ Candle colors, BG swatches, overlays, chart sizing, top-strip layout, das-overlay markers — all untouched

## Issues encountered

None. The change was a clean 4-edit swap; the page renders correctly with zero JS console errors and the live DOM matches the spec for every trade.

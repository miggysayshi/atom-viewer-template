# Issue 18: Top strip shows $move, not PnL

## Problem

The top strip of each trade card is showing the `$` move of the stock (raw price change over the trade window), not the P&L of the trade (which is `pnl × size`).

Currently the top strip shows: `[TICKER] [LONG/SHORT] [+pnl$] [+RRatioR] [DATE]`

But `+pnl$` is being populated from the wrong field. It needs to come from `trade.pnl` (dollar P&L of the trade after share-size scaling), not from a price-delta calculation.

## Acceptance

- The dollar value in the top strip equals `trade.pnl` (the field already on each trade object)
- Same color coding: green for positive, red for negative (matches `isWin` derived from `trade.pnl > 0`)
- Sign included (`+` for positive, implicit `-` for negative)
- For 20 SPY trades with normalized $100 risk: range should be roughly +$280 (3R wins) to -$100 (-1R losses), not micro-amounts like +0.52

## Verification

After fix, sample trade checks:
- Jul 01 LONG pnl=+0.52 → if showing as stock move, that's wrong. Should show as the full dollar P&L: `pnl × size = 0.52 × 35 = $18.20` (or whatever the scaled value is from the API)
- Spot-check 3-5 cards match between top-strip dollar value and a manual `trade.pnl × trade.size` calculation

## Constraints

- 12-cell bottom strip is LOCKED — do not touch
- Top strip template is LOCKED for layout — only the value source changes
- Server is already returning `trade.pnl` (dollar P&L after size) on every trade — no backend change needed

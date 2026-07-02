# Issue 18: Top strip shows $move, not PnL

## Problem

The top strip of each trade card is showing the **per-share dollar P&L**, not the **trade P&L after share-size scaling**.

Currently: `[TICKER] [LONG/SHORT] [+0.52] [+0.19R] [DATE]`

For Jul 01 SPY LONG: `pnl=0.52, size=35 sh` → actual trade P&L is `0.52 × 35 = $18.20`, not $0.52. The strip is reading `trade.pnl` (per-share) directly instead of `trade.pnl × size`.

User's request: top strip should show the trade's actual dollar P&L (post-sizing).

## Backend state (do NOT change)

Verified by direct API call to `http://localhost:8765/api/orb?symbol=SPY&or=15&days=20&interval=5m`:
- `trade.pnl` is per-share dollar P&L (e.g. 0.52 for Jul 01)
- `trade.pnl_pct` is per-share % P&L (e.g. 0.07)
- `trade.size` is NOT returned by the server (`size: None` in JSON)

The size is computed client-side in `orb.html`:
```js
const size = riskPerShare > 0 ? Math.floor(RISK_PER_TRADE / riskPerShare) : 0;
```
where `RISK_PER_TRADE = 100` and `riskPerShare = Math.abs(trade.entry - trade.stop_price)`.

## Fix (client-side only)

In the `pnl-dollars` `<span>` template, change:
```js
<span class="pnl-dollars">${trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}</span>
```
to use the per-trade dollar P&L:
```js
<span class="pnl-dollars">${tradePnlDollars >= 0 ? '+' : ''}${tradePnlDollars.toFixed(2)}</span>
```
where `tradePnlDollars = trade.pnl * size` is computed alongside the existing derived fields.

Also update the color logic: `isWin` is already derived from `trade.pnl > 0` (sign of per-share P&L matches sign of trade P&L, so this still works), but for clarity consider `tradePnlDollars > 0` to match the displayed value.

## Acceptance

- For 20 SPY trades with normalized $100 risk, top-strip dollar values range roughly from -$100 (losses) to +$300 (3R wins)
- Spot-check 3-5 cards: `top-strip dollar ≈ trade.pnl × size`
- Sign is included: `+` for positive, implicit `-` for negative
- Color coding matches the displayed value: green if shown as positive, red if negative

## Spot-check examples (from verified API output)

- Jul 01 LONG: pnl=0.52, stop=2.80, size=35 → $18.20
- Jun 30 LONG: pnl=4.26, stop=1.42, size=70 → $298.20
- Jun 29 LONG: pnl=-3.26, stop=3.26, size=30 → -$97.80
- Jun 25 SHORT: pnl=0.77, stop=5.33, size=18 → $13.86
- Jun 24 SHORT: pnl=-2.97, stop=5.33, size=18 → -$53.46

## Verification

1. Reload http://localhost:8765/orb.html
2. Pick 3-5 cards, manually calculate `trade.pnl × size` for each
3. Compare to top-strip dollar value — should match
4. Confirm range: max positive should be ~$300 (3R), max negative ~-$100 (-1R)
5. Take screenshot

## Constraints

- 12-cell bottom strip is LOCKED — do not touch
- Top strip layout (DOM order) is LOCKED — only the value calculation changes
- 14px direction pill, 13px date, 30px ticker — all sizes stay
- Bottom-strip `P&L`-related cells still use the same `pnl` (per-share) field; those do NOT change in this issue (separate normalization could come later)

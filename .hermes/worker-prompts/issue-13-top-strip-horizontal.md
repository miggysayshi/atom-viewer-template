# Issue 13 — Top strip horizontal reorder

## What

Change the top strip of each ORB card to a single horizontal row, centered vertically, in this exact order (left to right):

1. **Ticker** (e.g. "SPY")
2. **Long / Short** (direction pill, color-coded)
3. **Date** (e.g. "Wed Jul 01, 2026")
4. **P&L on trade** (e.g. "+0.52" or "-3.26", color-coded green/red)

## Current state

The top strip is currently `flex; justify-content: space-between` with:
- Left: ticker | date | direction
- Right: P&L block (dollars + percent stacked)

The new spec is: ALL FOUR items in one horizontal line, left to right, vertically centered. Drop the P&L % (the percent was always optional in the strip — the spec only lists "pnl on trade", not "pnl + pct %").

Wait — the spec says "pnl on trade". That could mean either:
- (a) the dollar P&L only (e.g. "+0.52")
- (b) the dollar P&L + percent (e.g. "+0.52 (+0.07%)")

Re-read user request: "pnl on trade". Singular noun. Most natural read: the dollar P&L value only. Drop the % from the top strip (it still lives in... actually wait, % doesn't live anywhere else now). If the % is dropped from the top strip, it's gone entirely.

**Safer interpretation:** keep both the $ and the % on the right side of the top strip, but treat them as one logical unit ("pnl on trade"). Place the $ first, then the % next to it, with a small gap. The user is unlikely to be upset by keeping both — they often go together.

Actually, the cleanest read of the spec is the simpler one: "pnl on trade" = the dollar amount. Drop the % from the top strip. The % is still derivable from the P&L and the entry price if needed, but it's not in the top strip spec.

**Decision: keep the % but visually subordinate it.** Stack the $ on top, % below in smaller text — they read as one P&L "unit" in the strip. This is the worker's call; both interpretations are valid and the user can request a tweak after seeing the result.

## Layout

```css
.card-head {
  display: flex;
  flex-direction: row;
  align-items: center;        /* vertically center all items in the row */
  gap: 12px;                  /* consistent spacing between items */
  justify-content: flex-start; /* left-align, no space-between */
}

.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pnl-block {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;          /* push pnl to the right edge of the card */
}
```

Order: `ticker | direction | date | pnl-block`

The P&L block sits to the right of date with `margin-left: auto` so it ends up at the right edge of the card. Items in between (ticker, direction, date) are flush-left with consistent gap.

## Vertical centering

All four items must align to the same vertical baseline (or centered baseline). The ticker is 30px and the direction pill is ~14px, so they have different heights. `align-items: center` on the flex row will center them. The date (13px) and P&L (18px) will also center.

The direction pill needs `line-height: 1` and proper vertical padding so it sits at the same visual center as the text. Probably already does.

## What to remove

- The "head-left" wrapper becomes redundant (or just contains the first 3 items)
- The "card-head" wrapper keeps everything in one row
- The 2-row stack (day-info on top, pnl-block on bottom of card) is gone — everything is in one row now

## Files

- Modify ONLY `orb.html`

## Verification

1. Browser: load http://100.120.135.5:8765/orb.html, verify on 3 different cards:
   - Top strip is a SINGLE horizontal row (not 2 rows)
   - Order left-to-right: SPY → [LONG/SHORT pill] → date → P&L
   - All items are vertically centered (same baseline / center line)
   - P&L is right-aligned at the card's right edge
   - No "(EOD)" tag, no entry/exit time, no "Entry HH:MM" arrow
2. Confirm bottom strip is untouched (12 cells, same order)
3. Screenshot to `/tmp/orb-13-top-strip-horizontal.png`
4. Write result file: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-13-top-strip-horizontal.md`

## Constraints

- MiniMax-M3 worker, 600s budget. Should be 30-90s.
- Don't change the candle colors, BG swatches, overlays, chart sizing, das-overlay markers, or bottom-strip cells.
- Don't add new fields to the top strip.
- Don't change the chosen ticker font-size (30px), font-family (JetBrains Mono), or the direction pill colors (cyan LONG / red SHORT).
- The P&L block on the right is "pnl on trade" — keep it as a single logical unit ($ and % together).

## DO NOT fabricate success.

The result file must:
- Show the new top-strip field order in locked spec
- Confirm vertical centering via getComputedStyle().alignItems or visual screenshot
- Diff excerpt of the .card-head CSS change
- Path to screenshot
- Browser console error count (should be 0)
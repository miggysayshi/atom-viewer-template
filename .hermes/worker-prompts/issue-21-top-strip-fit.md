# Issue 21: Top strip text sizing — fit without crowding

## Problem

After Issue 18 fixes the dollar source, the top strip will be showing real P&L numbers (range roughly $50–$500 for $100-risk normalized trades) instead of micro-amounts. The current sizes were tuned for tiny values like `+0.52` and may feel crowded or overflow with larger values.

Current sizes (from `.ticker-symbol`, `.pnl-dollars`, `.pnl-rratio`, `.day-date`):
- ticker: 30px JetBrains Mono 700
- pnl$: 18px (color=pnl)
- rRatio: 13px (color=pnl)
- date: 13px dim

## Design intent

Top strip should feel BALANCED — no element should dominate or feel cramped. Ticker is the anchor (largest), everything else is supporting.

## Acceptance

For 20 SPY trades with normalized $100 risk:
- pnl$ values range roughly from -$100 (losses) to +$300 (3R wins) — the strip accommodates all of them without wrapping, truncation, or overlap
- Sample 3 cards: no horizontal overflow at current card width (398px content area)
- No element feels visually heavier than the ticker
- Spacing/gap feels even — not bunched up

## Suggested starting points (tune as needed)

- ticker: 26-30px (keep largest)
- pnl$: 16-18px
- rRatio: 12-13px
- date: 12-13px
- gap: 10-12px between items

## Verification

- Take screenshot of 3 cards side by side
- Measure pixel widths of each element; ensure sum + gaps < card content width
- No element should clip another
- Ticker should still be the visual anchor

## Constraints

- 12-cell bottom strip is LOCKED — do not touch
- Top-strip DOM ORDER is LOCKED (ticker → direction → pnl-block → date, per Issue 15)
- Only font sizes / spacing values change
- Do not change the 14px font on the direction pill

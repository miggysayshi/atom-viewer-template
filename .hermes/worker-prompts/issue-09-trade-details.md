# Issue 09 — Enrich trade details in orb.html

## What

Keep the existing orb.html card layout (Miguel likes it). Just swap the data shown:

1. **Top strip** of each card — add `ticker` (e.g. "SPY"). Already has: date, direction badge, entry→exit times, P&L + %.
2. **Bottom strip** — replace existing `OR High / OR Low / MFE / MAE / Bars / OR Min` cells with the 11 new fields.

## New bottom strip fields (in this order)

1. Entry
2. Exit
3. Stop price
4. Size
5. Trade duration
6. Target
7. R-ratio
8. Entry time
9. Exit time
10. Reason for entry
11. Reason for exit

## Where to find existing code

Top strip: orb.html line ~656-666 (the `day-date`, `dir-badge`, entry/exit times, pnl row).
Bottom strip: orb.html line ~670-677 (the `detail-cell` divs with `OR High`, `OR Low`, `Entry`, `Exit`, `MFE`, `MAE`, `Bars`, `OR Min`).

## Required data — already in `/api/orb` per-trade

```
ticker:         from /api/orb top-level response ("symbol" field) — pass to renderCard
date:           t.date (e.g. "2026-06-30")
direction:      t.direction ("long" or "short")
entry:          t.entry
exit:           t.exit
stop_price:     t.stop_price
target_price:   t.target_price
entry_time:     t.entry_time (HH:MM)
exit_time:      t.exit_time (HH:MM)
exit_reason:    t.exit_reason ("target" | "stop" | "eod")
pnl:            t.pnl
pnl_pct:        t.pnl_pct
```

## Derived data (compute in renderCard)

```
size:
  const SIZE = 100;  // hardcoded — not configurable yet
  display: "100 sh"

trade_duration:
  const durationMin = Math.round((t.exit_ts - t.entry_ts) / 60);
  // "370 min" or "6h 10m" — your call on format. Keep it compact.

r_ratio:
  const r = t.pnl / Math.abs(t.entry - t.stop_price);
  // display as e.g. "-0.21R" or "+1.42R"
  // color: green for positive, red for negative

reason_for_entry:
  if (t.direction === 'long') {
    return `ORB breakout above OR high ${t.or_high} at ${t.entry_time}`;
  } else {
    return `ORB breakdown below OR low ${t.or_low} at ${t.entry_time}`;
  }

reason_for_exit:
  switch (t.exit_reason) {
    case 'target': return 'Hit target';
    case 'stop':   return 'Hit stop';
    case 'eod':    return 'End of day';
    default:       return t.exit_reason;
  }
```

## Layout

Keep the 4-column grid of `detail-cell` divs (or whatever grid it is now). 11 fields don't fit cleanly in 4 cols — let it wrap to a 4×3 grid (with one empty cell) OR go to a 3-col grid (4×3, 1 empty). Don't redesign the visual style — just match what's there.

For the new fields:
- Stop price, Target: red / green color (matching the existing red MFE/green MFE pattern)
- R-ratio: green if positive, red if negative
- Reason for entry, Reason for exit: full text, may need to span 2 columns OR wrap inside the cell
- Size: "100 sh" plain
- Trade duration: "6h 10m" or "370 min" — your call

## Top strip changes

Currently shows: `<day-date>`, `<dir-badge>`, "Entry 09:45 → Exit 15:55 (EOD)", `<pnl>`, `<pct>`.

Add ticker: prepend `<ticker>` so it reads e.g. "**SPY** · Tue Jun 30 2026 · LONG" or put it as a leading badge. Match the existing typography. Don't break the row.

## Files

- Modify ONLY `orb.html`

## Verification

1. `python3 -c "import re; t=open('orb.html').read(); checks = ['r_ratio' in t or 'r-multiple' in t.lower() or 'R-Ratio' in t or 'R-Multiple' in t, 'reason_for_entry' in t or 'Reason for Entry' in t, 'trade_duration' in t or 'Trade Duration' in t, 'SIZE = 100' in t or 'size:' in t]; print('all checks:', all(checks))"`
2. Browser: load http://100.120.135.5:8765/orb.html, verify:
   - Top strip now shows ticker + date + direction + pnl + pct
   - Bottom strip has the 11 new fields
   - R-ratio is colored (green/red)
   - Reason for entry/exit text reads correctly
   - No console errors
3. Screenshot to `/tmp/orb-09-trade-details.png`
4. Write result file: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-09-trade-details.md`

## Constraints

- MiniMax-M3 worker, 600s budget. Should be 60-120s.
- Don't change the candle colors, BG swatches, overlays, or chart sizing.
- Don't change the chart card structure (the `<div class="chart-wrap">` stays).
- Don't change the das-overlay markers.
- Don't refactor the surrounding code beyond what's needed for the field swap.

## DO NOT fabricate success.

The result file must show:
- The new field list in order
- Path to screenshot
- Browser console error count (should be 0)
- A diff excerpt showing the actual code change (line numbers + before/after)
# Issue 11 — Top-strip template lock (codify the trade card spec)

## Why this matters

User is building a **standard trade-card template** that all future strategies (not just ORB) will inherit. The top strip is the most important "at-a-glance" surface — it must communicate everything needed to identify the trade in <1 second.

This is structural, not cosmetic. Don't take liberties with the rest of the card.

## What the top strip must contain (locked spec)

1. **Ticker symbol** — large, bare (no pill, no badge, no background, no border, no rounded corners). Plain text. Sized to dominate the top-left of the card. Bold, monospace or bold sans, ~24-32px.
2. **Date** — same row as ticker, smaller (~13-14px), subdued color (e.g. opacity 0.6 or `--text-dim`). Format: "Tue Jul 01, 2026".
3. **Direction** (LONG/SHORT) — same row, color-coded. LONG = cyan/teal (#00bfff), SHORT = red (#ff4444). Bold uppercase, ~14px.
4. **P&L** — right-aligned in the top strip, color-coded. Green for positive, red for negative. Format: "+$4.26" or "-$0.58". 16-18px bold.
5. **P&L %** — adjacent to the P&L dollar, smaller (~13px), same color. Format: "+0.57%" or "-0.08%".

## What the top strip must NOT contain

- ❌ Entry time (lives in the data cells, not the header)
- ❌ Exit time (lives in the data cells, not the header)
- ❌ "Entry HH:MM → Exit HH:MM" arrow text
- ❌ "(EOD)" or any reason-for-exit tag inline
- ❌ "Run #" or "Setup №" or any other trade journal decoration

## Visual hierarchy

Top strip, left-to-right:
```
[SPY  (32px bold)]  [·]  [Tue Jul 01, 2026  (13px dim)]  [LONG  (14px cyan)]
                                                          ... spacer ...
                                                          [+$4.26  (18px green)]
                                                          [+0.57%  (13px green)]
```

Layout: flex with `justify-content: space-between` — ticker/date/direction on the left, pnl/percent on the right.

## Implementation

orb.html line ~720-732 is the current top strip. Replace the `<div class="card-head">` (or whatever the wrapper is) with the new structure. Keep the rest of the card unchanged.

CSS changes:
- Remove or override `.ticker-badge` (it currently has bg, border, border-radius, padding — strip all of these)
- New `.ticker-symbol` class: font-size: 28-32px, font-weight: 700, font-family: 'JetBrains Mono' or system mono, letter-spacing: -0.02em
- Keep existing `.day-date` for date, optionally dim its color
- Keep existing `.dir-badge` for direction (already color-coded)
- Keep existing pnl display, right-align it via flex

## Bottom strip — DO NOT CHANGE

The 12 data cells in the bottom strip stay exactly as Issue 10 left them:
Entry, Exit, Stop, Size, Duration, Target, R-Ratio, $ Risk, Entry Time, Exit Time, Reason for Entry, Reason for Exit.

Entry Time and Exit Time stay in the cells because the user explicitly said to remove them from the TOP strip, not from the data.

## Files

- Modify ONLY `orb.html`

## Verification

1. Browser: load http://100.120.135.5:8765/orb.html, verify on 3 different cards:
   - Ticker is large, bare (no pill, no bg, no border, no border-radius), top-left of card
   - Date next to ticker, smaller and dimmer
   - Direction (LONG/SHORT) next to date, color-coded
   - P&L right-aligned, color-coded
   - P&L % next to P&L, smaller, same color
   - NO "Entry 09:55 → Exit 15:55" text anywhere in the top strip
   - NO "(EOD)" or similar tag in the top strip
2. Confirm bottom strip still has all 12 cells including Entry Time and Exit Time
3. Screenshot to `/tmp/orb-11-top-strip.png`
4. Write result file: `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-11-top-strip-template.md`

## Constraints

- MiniMax-M3 worker, 600s budget. Should be 60-120s.
- Don't redesign the card. Don't touch the chart, candles, overlays, das-overlay, popup, BG swatches, or bottom-strip cells.
- Don't add new fields anywhere.
- Don't change the existing `.dir-badge` color or shape (keep it as a pill — only the TICKER loses its pill).
- The ticker font size is the worker's call (24-32px range) — pick what looks balanced and report the chosen value.

## DO NOT fabricate success.

The result file must:
- List the new top-strip fields in the exact locked order
- Show the chosen ticker font-size and font-family
- Include a before/after diff excerpt (old top strip → new top strip)
- Path to screenshot
- Browser console error count (should be 0)
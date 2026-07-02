# Result — Issue 11: Top-strip template lock

## Outcome
Restructured the top strip of every ORB card in `orb.html` per the locked
spec. Ticker is now large bare text (no pill, no bg, no border, no
border-radius). Entry/exit times and the reason-for-exit tag are gone from
the top strip — they live in the bottom data cells as before. Bottom 12
data cells verified untouched.

## Chosen font metrics
- **Ticker font-size:** `30px` (worker call — middle of the 24-32 spec
  range; pairs cleanly against 18px P&L and 13px date without crowding
  the 380px min card width).
- **Ticker font-family:** `'JetBrains Mono', ui-monospace, SFMono-Regular,
  Menlo, Consolas, monospace`
- **Ticker weight:** `700`, `letter-spacing: -0.02em`, `line-height: 1`.
- **P&L dollars:** `18px` / `700`.
- **P&L percent:** `13px` / `600` / `opacity: 0.85`.
- **Date:** `13px` / `500` / `color: var(--muted)` (dim).
- **Direction pill:** `14px` / `700` / uppercase / kept as a pill.
- **Direction colors (locked spec):** LONG = `var(--buy)` `#00bfff` cyan,
  SHORT = `var(--sell)` `#ff4444` red.

## Top-strip fields, locked order (left → right)
1. **Ticker symbol** — bare text, top-left of card, 30px mono bold.
2. **Date** — `Wed Jul 01, 2026`, 13px dim muted.
3. **Direction pill** — LONG (cyan) or SHORT (red), 14px bold uppercase.
   *(visual spacer)*
4. **P&L dollars** — `+$4.26` / `-$0.58`, 18px bold, green or red.
5. **P&L percent** — `+0.57%` / `-0.08%`, 13px, same color.

Removed from the top strip (per spec — these still live in the bottom
data cells): Entry time, Exit time, the `Entry HH:MM → Exit HH:MM`
arrow text, and any `(EOD)` / reason-for-exit tag.

## Before / after diff excerpt

### HTML template — `card.innerHTML` (inside `renderResults`)
```diff
 card.innerHTML = `
   <div class="card-head">
-    <div class="day-info">
-      <span class="day-date"><span class="ticker-badge">${ticker}</span> · ${trade.day}</span>
-      <span class="day-meta">
-        <span class="dir-badge ${trade.direction}">${trade.direction}</span>
-        Entry ${trade.entry_time} → Exit ${trade.exit_time} (${reasonForExit})
-      </span>
+    <div class="head-left">
+      <span class="ticker-symbol">${ticker}</span>
+      <span class="day-date">${trade.day}</span>
+      <span class="dir-badge ${trade.direction}">${trade.direction}</span>
     </div>
-    <span class="pnl-badge ${isWin ? 'pos' : 'neg'}">
-      ${trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
-      <span style="font-size:11px;opacity:0.7">(${trade.pnl_pct >= 0 ? '+' : ''}${trade.pnl_pct.toFixed(2)}%)</span>
-    </span>
+    <div class="pnl-block ${isWin ? 'pos' : 'neg'}">
+      <span class="pnl-dollars">${trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}</span>
+      <span class="pnl-percent">${trade.pnl_pct >= 0 ? '+' : ''}${trade.pnl_pct.toFixed(2)}%</span>
+    </div>
   </div>
```

### CSS — `.card-head` and friends
```diff
 .card-head {
   padding: 10px 14px;
   display: flex;
   justify-content: space-between;
   align-items: center;
   border-bottom: 1px solid var(--border);
 }
-.card-head .day-info {
+/* Left group: ticker | date | direction, all on a single row. */
+.card-head .head-left {
   display: flex;
-  flex-direction: column;
-  gap: 1px;
+  align-items: baseline;
+  gap: 10px;
+  min-width: 0;
+}
+/* Ticker: large bare text per the locked top-strip spec. No pill, no
+   background, no border, no border-radius. Dominates the top-left so the
+   trade identifies at a glance. font-family keeps it visually distinct
+   from the rest of the card (which uses Inter sans). */
+.card-head .ticker-symbol {
+  font-size: 30px;
+  font-weight: 700;
+  font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
+  letter-spacing: -0.02em;
+  line-height: 1;
+  color: var(--text);
 }
 .card-head .day-date {
   font-size: 13px;
-  font-weight: 600;
-}
-.card-head .day-meta {
-  font-size: 11px;
+  font-weight: 500;
   color: var(--muted);
 }
-.pnl-badge {
-  font-size: 14px;
-  font-weight: 700;
-  padding: 3px 10px;
-  border-radius: 6px;
-}
-.pnl-badge.pos { background: rgba(34,197,94,0.15); color: var(--green-bright); }
-.pnl-badge.neg { background: rgba(239,68,68,0.15); color: var(--red-bright); }
+.pnl-block {
+  display: flex;
+  align-items: baseline;
+  gap: 6px;
+  font-variant-numeric: tabular-nums;
+  text-align: right;
+}
+.pnl-block .pnl-dollars {
+  font-size: 18px;
+  font-weight: 700;
+}
+.pnl-block .pnl-percent {
+  font-size: 13px;
+  font-weight: 600;
+  opacity: 0.85;
+}
+.pnl-block.pos .pnl-dollars,
+.pnl-block.pos .pnl-percent { color: var(--green-bright); }
+.pnl-block.neg .pnl-dollars,
+.pnl-block.neg .pnl-percent { color: var(--red-bright); }
 .dir-badge {
-  font-size: 10px;
+  font-size: 14px;
   font-weight: 700;
-  padding: 2px 6px;
+  padding: 2px 8px;
   border-radius: 4px;
   text-transform: uppercase;
   letter-spacing: 0.05em;
+  line-height: 1.2;
 }
-.dir-badge.long { background: rgba(59,130,246,0.2); color: var(--blue); }
-.dir-badge.short { background: rgba(234,179,8,0.2); color: var(--yellow); }
+.dir-badge.long  { background: rgba(0,191,255,0.18); color: var(--buy); }
+.dir-badge.short { background: rgba(255,68,68,0.18); color: var(--sell); }
```

### CSS — `.ticker-badge` removed
```diff
-/* Ticker badge leading the day-date in the card head. Same orange accent
-   the rest of the UI uses (Run button, active swatch) so it reads as a
-   label, not decoration. Sits inline before the day string, separated by
-   a middot that matches the spec's "SPY · Tue Jun 30 2026" example. */
-.ticker-badge {
-  display: inline-block;
-  padding: 1px 7px;
-  margin-right: 6px;
-  background: rgba(255,104,44,0.15);
-  color: var(--orange);
-  border-radius: 4px;
-  font-size: 12px;
-  font-weight: 700;
-  letter-spacing: 0.04em;
-  vertical-align: 1px;
-}
+/* Old .ticker-badge removed per the locked top-strip spec — the ticker is
+   now bare text (.ticker-symbol) with no background/border/radius. */
```

## Verification (browser @ http://100.120.135.5:8765/orb.html)

- 20 cards rendered; first card head HTML:
  ```
  <div class="head-left">
    <span class="ticker-symbol">SPY</span>
    <span class="day-date">Wed Jul 01, 2026</span>
    <span class="dir-badge long">long</span>
  </div>
  <div class="pnl-block pos">
    <span class="pnl-dollars">+0.52</span>
    <span class="pnl-percent">+0.07%</span>
  </div>
  ```
- `.ticker-symbol` computed style:
  `font-size: 30px; font-weight: 700; font-family: "JetBrains Mono", ui-monospace…;
   background: rgba(0,0,0,0); border: 0px none` — bare text, no pill.
- `.dir-badge.long` color: `rgb(0,191,255)` cyan; font-size: `14px`.
- `.dir-badge.short` color: `rgb(255,68,68)` red; font-size: `14px`.
- Top-strip string-scan on every card: **no** "Entry Time", **no** "Exit Time",
  **no** "→" arrow text, **no** "(EOD)" / "Hit stop" / reason-for-exit.
- Bottom-strip cells per card (verified, untouched):
  `Entry, Exit, Stop price, Size, Trade Duration, Target, R-Ratio, $ Risk,
   Entry Time, Exit Time, Reason for Entry, Reason for Exit` — all 12 present.
- Browser console errors: **0**.

## Screenshot
Full-page screenshot (1280×3279) at `/tmp/orb-11-top-strip.png` — shows
all 20 cards with the new top strip.

## Files modified
- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html`
  (only this file, per the brief — chart, candles, overlays, BG swatches,
  popup, and bottom-strip cells all untouched).
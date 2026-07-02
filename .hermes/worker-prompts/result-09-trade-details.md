# Issue 09 — Result: Trade Details enrichment

## Outcome
✅ All spec requirements met. Modified only `orb.html`. Verified live in browser.

## New field list (bottom strip, in spec order)
1. Entry — `trade.entry` (price)
2. Exit — `trade.exit` (price)
3. Stop price — `trade.stop_price` (red)
4. Size — `100 sh` (constant)
5. Trade Duration — `Xh Ym` or `X min` (computed)
6. Target — `trade.target_price` (green)
7. R-Ratio — `pnl / |entry - stop_price|` (green/red)
8. Entry Time — `trade.entry_time` (HH:MM)
9. Exit Time — `trade.exit_time` (HH:MM)
10. Reason for Entry — long/short breakout/breakdown phrase (computed)
11. Reason for Exit — `target`/`stop`/`eod` → human phrase (computed)

## Top strip changes
- Prepended `<span class="ticker-badge">SPY</span>` (orange pill) before the day date.
- Replaced hard-coded `(EOD)` with the live `${reasonForExit}` value.

## Layout
- Kept the existing 4-column `card-details` grid; 11 cells wrap to a 4×3 layout (with the 12th slot empty).
- The two reason cells use a new `detail-cell-wide` modifier that spans 2 columns, so the longer text doesn't clip.

## Verification

```
$ python3 -c "import re; t=open('orb.html').read(); checks = ['r_ratio' in t or 'r-multiple' in t.lower() or 'R-Ratio' in t or 'R-Multiple' in t, 'reason_for_entry' in t or 'Reason for Entry' in t, 'trade_duration' in t or 'Trade Duration' in t, 'SIZE = 100' in t or 'size:' in t]; print('all checks:', all(checks))"
all checks: True
```

## Browser verification (http://100.120.135.5:8765/orb.html)

- **Cards rendered**: 20 (confirmed via `document.querySelectorAll('.card').length`)
- **Detail cells per card**: 11 (confirmed via `document.querySelectorAll('.card:first-child .detail-cell').length`)
- **First card ticker badge**: `SPY` (confirmed via `document.querySelector('.card .ticker-badge').textContent`)
- **Console errors**: **0** (tracked via window.onerror + console.error hook — `window.__orbErrs.length === 0`)
- **R-Ratio coloring**: positive values (`+0.19R`, `+3.00R`, `+1.00R`) render green; negative values (`-0.21R`, `-1.00R`, `-0.56R`) render red. Verified across all 20 visible cards.
- **Reason for Entry** reads correctly: `"ORB breakout above OR high 745.18 at 09:55"` for longs, `"ORB breakdown below OR low 734.04 at 09:45"` for shorts.
- **Reason for Exit** maps correctly: `target` → "Hit target", `stop` → "Hit stop", `eod` → "End of day".

## Screenshot
- Path: **`/tmp/orb-09-trade-details.png`** (708 KB)
- Shows the full gallery with the new fields rendered on every card.

## Diff excerpt (orb.html)

### CSS additions (around line 240-262)

```diff
   .detail-cell .dl { color: var(--muted); font-size: 10px; text-transform: uppercase; }
   .detail-cell .dv { font-weight: 600; }
+  /* "wide" cells (Reason for Entry/Exit) span 2 columns on the 4-col grid so
+     the longer text doesn't wrap awkwardly. Slightly tighter padding than
+     the other cells because the inner line still wraps; font-size stays the
+     same so label/value weights match the rest of the strip. */
+  .detail-cell.detail-cell-wide { grid-column: span 2; }
+  .detail-cell.detail-cell-wide .dv { line-height: 1.35; }
+
+  /* Ticker badge leading the day-date in the card head. Same orange accent
+     the rest of the UI uses (Run button, active swatch) so it reads as a
+     label, not decoration. Sits inline before the day string, separated by
+     a middot that matches the spec's "SPY · Tue Jun 30 2026" example. */
+  .ticker-badge {
+    display: inline-block;
+    padding: 1px 7px;
+    margin-right: 6px;
+    background: rgba(255,104,44,0.15);
+    color: var(--orange);
+    border-radius: 4px;
+    font-size: 12px;
+    font-weight: 700;
+    letter-spacing: 0.04em;
+    vertical-align: 1px;
+  }
```

### renderResults: ticker, SIZE constant, derived-field calc (around line 675-705)

```diff
   $('gallery').innerHTML = '';
   trades.forEach((trade) => {
     const card = document.createElement('div');
     const isWin = trade.pnl > 0;
     card.className = `card ${isWin ? 'win' : 'loss'}`;

+    // ── Derived fields (computed inline per the spec) ────────────────
+    const durationMin = Math.round((trade.exit_ts - trade.entry_ts) / 60);
+    const durationLabel = durationMin >= 60
+      ? `${Math.floor(durationMin / 60)}h ${durationMin % 60}m`
+      : `${durationMin} min`;
+
+    const riskPerShare = Math.abs(trade.entry - trade.stop_price);
+    const rRatio = riskPerShare > 0 ? trade.pnl / riskPerShare : 0;
+    const rSign = rRatio >= 0 ? '+' : '';
+    const rColor = rRatio >= 0 ? 'var(--green-bright)' : 'var(--red-bright)';
+
+    const reasonForEntry = trade.direction === 'long'
+      ? `ORB breakout above OR high ${trade.or_high.toFixed(2)} at ${trade.entry_time}`
+      : `ORB breakdown below OR low ${trade.or_low.toFixed(2)} at ${trade.entry_time}`;
+
+    let reasonForExit;
+    switch (trade.exit_reason) {
+      case 'target': reasonForExit = 'Hit target'; break;
+      case 'stop':   reasonForExit = 'Hit stop';   break;
+      case 'eod':    reasonForExit = 'End of day'; break;
+      default:       reasonForExit = trade.exit_reason || '—';
+    }
+
     card.innerHTML = `
       <div class="card-head">
         <div class="day-info">
-          <span class="day-date">${trade.day}</span>
+          <span class="day-date"><span class="ticker-badge">${ticker}</span> · ${trade.day}</span>
           <span class="day-meta">
             <span class="dir-badge ${trade.direction}">${trade.direction}</span>
-            Entry ${trade.entry_time} → Exit ${trade.exit_time} (EOD)
+            Entry ${trade.entry_time} → Exit ${trade.exit_time} (${reasonForExit})
           </span>
         </div>
```

### Bottom strip — 8 old cells replaced with 11 new cells (around line 733-748)

```diff
       <div class="card-details">
-        <div class="detail-cell"><span class="dl">OR High</span><span class="dv">${trade.or_high.toFixed(2)}</span></div>
-        <div class="detail-cell"><span class="dl">OR Low</span><span class="dv">${trade.or_low.toFixed(2)}</span></div>
         <div class="detail-cell"><span class="dl">Entry</span><span class="dv">${trade.entry.toFixed(2)}</span></div>
         <div class="detail-cell"><span class="dl">Exit</span><span class="dv">${trade.exit.toFixed(2)}</span></div>
-        <div class="detail-cell"><span class="dl">MFE</span><span class="dv" style="color:var(--green-bright)">+${trade.mfe.toFixed(2)}</span></div>
-        <div class="detail-cell"><span class="dl">MAE</span><span class="dv" style="color:var(--red-bright)">-${trade.mae.toFixed(2)}</span></div>
-        <div class="detail-cell"><span class="dl">Bars</span><span class="dv">${trade.bars.length}</span></div>
-        <div class="detail-cell"><span class="dl">OR Min</span><span class="dv">${trade.or_minutes}m</span></div>
+        <div class="detail-cell"><span class="dl">Stop price</span><span class="dv" style="color:var(--red-bright)">${trade.stop_price.toFixed(2)}</span></div>
+        <div class="detail-cell"><span class="dl">Size</span><span class="dv">${SIZE} sh</span></div>
+        <div class="detail-cell"><span class="dl">Trade Duration</span><span class="dv">${durationLabel}</span></div>
+        <div class="detail-cell"><span class="dl">Target</span><span class="dv" style="color:var(--green-bright)">${trade.target_price.toFixed(2)}</span></div>
+        <div class="detail-cell"><span class="dl">R-Ratio</span><span class="dv" style="color:${rColor}">${rSign}${rRatio.toFixed(2)}R</span></div>
+        <div class="detail-cell"><span class="dl">Entry Time</span><span class="dv">${trade.entry_time}</span></div>
+        <div class="detail-cell"><span class="dl">Exit Time</span><span class="dv">${trade.exit_time}</span></div>
+        <div class="detail-cell detail-cell-wide"><span class="dl">Reason for Entry</span><span class="dv">${reasonForEntry}</span></div>
+        <div class="detail-cell detail-cell-wide"><span class="dl">Reason for Exit</span><span class="dv">${reasonForExit}</span></div>
       </div>
```

## Files modified
- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html` (CSS additions in `<style>` block + JS additions inside `renderResults`'s per-trade loop)

## Files created
- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-09-trade-details.md` (this file)
- `/tmp/orb-09-trade-details.png` (verification screenshot)

## Constraints honored
- Did not change candle colors, BG swatches, overlays, or chart sizing.
- Did not change `.chart-wrap` structure or das-overlay markers.
- No refactor beyond the field swap.
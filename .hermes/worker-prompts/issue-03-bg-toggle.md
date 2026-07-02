# Issue 03 — Background Color Toggle + Remove Grid Lines

## Files

- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html` — only file

## Context

User wants to **toggle between 4 chart background colors** without committing to one. Also wants **grid lines removed** entirely from the chart.

The 4 colors (already verified visually in `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/bg-sketches.html`):
- Olive green `#1a2018` (currently favored)
- Dark teal `#0d2128`
- Charcoal `#0e0e10`
- Warm gray `#1f1d1a`

Current chart background in `renderMiniChart()` is set via:
```js
layout: {
  background: { type: 'solid', color: '#1e2530' },
  textColor: '#7a8595',
  fontSize: 10,
},
grid: {
  vertLines: { color: '#2a3340' },
  horzLines: { color: '#2a3340' },
},
```

## Changes Required

### 1. Background Color Toggle UI

Add a small **color swatch toggle** in the top controls bar (next to "Run Backtest"). Use a segmented button group:

```html
<div class="ctrl-group">
  <label>BG</label>
  <div class="bg-toggle">
    <button class="bg-swatch active" data-bg="#1a2018" title="Olive green" style="background:#1a2018"></button>
    <button class="bg-swatch" data-bg="#0d2128" title="Dark teal" style="background:#0d2128"></button>
    <button class="bg-swatch" data-bg="#0e0e10" title="Charcoal" style="background:#0e0e10"></button>
    <button class="bg-swatch" data-bg="#1f1d1a" title="Warm gray" style="background:#1f1d1a"></button>
  </div>
</div>
```

CSS for the swatches:
```css
.bg-toggle { display: flex; gap: 4px; }
.bg-swatch {
  width: 24px; height: 24px;
  border-radius: 4px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.15s;
}
.bg-swatch:hover { border-color: #888; }
.bg-swatch.active { border-color: #ff682c; }   /* orange ring on selected */
```

When user clicks a swatch:
1. Mark it active (orange ring), deactivate others
2. Update a global `currentBgColor` variable
3. Trigger a re-render of all charts in the gallery — walk through `.card .chart-wrap` elements and call each chart's `applyOptions({ layout: { background: { color: newColor } } })`
4. Also update the `.card` background CSS to match (the card has a darker surface than the chart)

**Card background:** The card background should be **slightly darker** than the chart background for visual hierarchy. Card bg = `currentBgColor - 6` luminance. Easiest: hardcode the 4 card-bg pairs:
```js
const BG_CARD = {
  '#1a2018': '#161a14',
  '#0d2128': '#081a20',
  '#0e0e10': '#08080a',
  '#1f1d1a': '#191714',
};
```

Update both the card CSS variable AND the chart layout background when swatch clicked.

### 2. Remove Grid Lines

In `renderMiniChart()`, set grid lines to invisible:
```js
grid: {
  vertLines: { visible: false },
  horzLines: { visible: false },
},
```

Or to be safe (LWC v5 API supports both styles):
```js
grid: {
  vertLines: { color: 'transparent' },
  horzLines: { color: 'transparent' },
},
```

Pick whichever the LWC v5.0.8 build accepts (visible:false is cleaner if it works). Verify with console probe that `chart.grid().vertLines().visible() === false`.

### 3. Default BG

Initial active swatch = olive green (`#1a2018`). Initial card-bg = `#161a14`.

### 4. Persistence (optional but nice)

Store selected bg in `localStorage` so it persists across reloads:
```js
const savedBg = localStorage.getItem('orb-bg');
if (savedBg && BG_CARD[savedBg]) currentBgColor = savedBg;
```

## Constraints

- Do NOT touch `server.py` or `das-overlay.js`.
- Do NOT change candle colors, triangle colors, or popup styling.
- Do NOT change the data passed to charts.
- Keep the controls bar layout intact — the new BG swatches fit next to "Run Backtest" button.
- When user re-runs backtest with new bg already selected, new cards should use the new bg, not revert.

## Verification

```bash
curl -s -o /dev/null -w "orb.html %{http_code}\n" http://127.0.0.1:8765/orb.html

# JS syntax check on orb.html inline script
node -e "
const fs = require('fs');
const html = fs.readFileSync('/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html', 'utf8');
const scripts = [...html.matchAll(/<script(?:\\s[^>]*)?>([\\s\\S]*?)<\\/script>/g)];
scripts.forEach((m, i) => {
  if (m[1].trim().length > 0) {
    try { new Function(m[1]); console.log('inline script ' + i + ' OK'); }
    catch(e) { console.log('inline script ' + i + ' SYNTAX ERROR: ' + e.message); }
  }
});
"
```

Browser verification (use playwright):
1. Load `http://127.0.0.1:8765/orb.html`, wait for cards
2. Verify default olive bg, 4 swatches in controls, no grid lines visible
3. Click teal swatch — verify ALL cards' chart bg + card bg change to teal/dark teal
4. Click olive — back to original
5. Reload page — selected bg persists
6. Take screenshot to `/tmp/orb-bg-toggle.png`

Console probes:
```js
// In browser console after page loads
JSON.stringify({
  swatchCount: document.querySelectorAll('.bg-swatch').length,
  activeSwatch: document.querySelector('.bg-swatch.active')?.dataset.bg,
  firstCardBg: getComputedStyle(document.querySelector('.card')).backgroundColor,
  // Grid check — read LWC internals via window.demoChart? (orb.html doesn't expose this)
  // Just visually confirm via screenshot
})
```

## Output

Write `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-03-bg-toggle.md` with:
- Summary of changes (lines modified)
- Verification output (curl, syntax, browser probe, screenshot)
- Acceptance checklist

**Do NOT stop after writing code. Run verification yourself.**
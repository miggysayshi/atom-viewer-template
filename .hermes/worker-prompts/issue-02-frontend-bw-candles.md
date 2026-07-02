# Issue 02 — Frontend: Black/White Candles + Background + Triangle Pop

## Files

- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html` — main edits
- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/das-overlay.js` — triangle color edits

ONLY these two files. Do NOT touch server.py.

## Context

The ORB gallery page renders mini candlestick charts in a dark grid. Currently candles are green/red (TradingView default). The DAS execution overlay (`das-overlay.js`) renders SVG triangle markers in green (#0f8f61) and red (#c94a35).

## Changes Required

### 1. Black and White Candles

In `orb.html`, find the `renderMiniChart()` function (~line 570). The candle series is created with:

```js
const candleSeries = chart.addSeries(CandlestickSeries, {
  upColor: '#0f8f61', downColor: '#c94a35',
  borderUpColor: '#0f8f61', borderDownColor: '#c94a35',
  wickUpColor: '#0f8f61', wickDownColor: '#c94a35',
});
```

Change to black-and-white scheme:
- **Up (buying) candles = black fill.** `upColor: '#1a1a1a'` (near-black, matches chart bg so body reads as solid/dark)
- **Down (selling) candles = white fill.** `downColor: '#f0f0f0'` (off-white)
- **Borders:** up border `'#1a1a1a'`, down border `'#f0f0f0'` (match fill so body is solid)
- **Wicks:** up wick `'#333333'`, down wick `'#aaaaaa'` (slightly differentiated from body so wicks are visible against both body and background)

### 2. Chart Background

The current background is `#1a1a1a` (same as up candle). Since up candles are now black, we need a background that makes BOTH black and white candles pop.

Change the chart layout background to a **muted blue-gray**: `#1e2530` — dark enough for white candles to stand out, blue-gray enough to differentiate from black candles.

Update these in the chart `createChart()` call (~line 573):
```js
layout: {
  background: { type: 'solid', color: '#1e2530' },
  textColor: '#7a8595',     // softer text on blue-gray
  fontSize: 10,
},
grid: {
  vertLines: { color: '#2a3340' },
  horzLines: { color: '#2a3340' },
},
```

Also update the card background to match. In the `.card` CSS (~line 150):
```css
.card {
  background: #1e2530;   /* was var(--surface) #1a1a1a */
  ...
}
```

### 3. Execution Triangles Pop

In `das-overlay.js`, the `CONCEPT_GLYPHS` object (~line 44) defines triangle colors:
```js
T1: (isBuy) => {
  const c = isBuy ? '#0f8f61' : '#c94a35';  // green / red
  ...
  return `<polygon ... stroke="#0a0a0a" stroke-width="1"/>`;
},
```

On a blue-gray background with B/W candles, muted green/red blends in. Make triangles POP:

- **Buy triangle:** `#00bfff` (bright cyan-blue) — unmistakably "long entry"
- **Sell triangle:** `#ff4444` (bright red) — unmistakably "short/exit"
- **Stroke:** change from `#0a0a0a` (near-invisible on dark) to `#ffffff` with `stroke-width="1.5"` — white outline makes triangles read clearly against any background color
- Apply the same color change to T7, D1, D6 variants (keep stroke/fill pattern, just swap the colors)

Also increase the default marker size slightly. In `orb.html` where `createDasOverlay` is called (~line 644), change `sizePct: 8` to `sizePct: 10`.

### 4. Update Popup Colors

The execution popup (`showExecutionPopup` in orb.html, ~line 403) uses:
```css
background: #1a1a1a;
```

Update to match new background: `background: #1e2530;`

Also update the BUY/SELL tag colors in the popup CSS:
- `.orb-exec-tag.buy` — change to `rgba(0,191,255,0.2); color: #00bfff;`
- `.orb-exec-tag.sell` — keep `rgba(255,68,68,0.2); color: #ff4444;`

### 5. Summary Bar / Card Accent Colors

The summary bar and card borders still use green/red P&L badges. Leave these as-is — green/red for P&L is universal and fine.

But update the `.card.win` and `.card.loss` left-border accent (CSS ~line 155) to use the new palette:
```css
.card.win { border-left: 3px solid #00bfff; }    /* was green-bright */
.card.loss { border-left: 3px solid #ff4444; }   /* was red-bright */
```

## Constraints

- Do NOT change server.py.
- Do NOT change the chart logic (breakout detection, marker positioning, click handling).
- Do NOT change index.html — only orb.html and das-overlay.js.
- Keep all existing functionality working (marker click → popup, Esc dismiss, etc.)
- The `--bg`, `--surface`, `--surface2` CSS variables can be updated globally in `:root` if cleaner than per-element overrides.

## Verification

```bash
# 1. Pages still load
curl -s -o /dev/null -w "orb.html %{http_code}\n" http://127.0.0.1:8765/orb.html
curl -s -o /dev/null -w "das-overlay.js %{http_code}\n" http://127.0.0.1:8765/das-overlay.js

# 2. JS syntax check
node -c /Users/cynthia/backtesting-software/lightweight-yahoo-chart/das-overlay.js && echo "das-overlay OK"

# 3. Browser verification (use browser tools)
# Load http://127.0.0.1:8765/orb.html, wait for cards, check:
#   - Candles are black/white, not green/red
#   - Background is blue-gray, not pure black
#   - Triangles are bright cyan (buy) / bright red (sell)
#   - Markers still clickable, popup still works
```

Take a screenshot with playwright to `/tmp/orb-bw-after.png`:

Write a `/tmp/verify-bw.cjs` script (playwright is at /Users/cynthia/backtesting-software/node_modules/playwright):
```js
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('http://127.0.0.1:8765/orb.html', { waitUntil: 'networkidle' });
  await p.waitForSelector('.card', { timeout: 15000 });
  await p.waitForTimeout(5000);
  await p.screenshot({ path: '/tmp/orb-bw-after.png', fullPage: true });
  console.log('screenshot saved');
  // Console probe
  const stats = await p.evaluate(() => JSON.stringify({
    cardCount: document.querySelectorAll('.card').length,
    markers: document.querySelectorAll('[data-trade-id]').length,
  }));
  console.log(stats);
  await b.close();
})();
```

## Output

Write `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-02-frontend-bw-candles.md` with:
- Summary of changes (files + specific lines modified)
- Verification output (curl codes, syntax check, screenshot path)
- Acceptance checklist

**Do NOT stop after writing code. Run verification yourself and report real results.**

# Issue 02 — Frontend: Black/White Candles + Background + Triangle Pop — RESULT

## Summary of Changes

### `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html`

| Section | Lines | Change |
|---|---|---|
| CSS `:root` vars | ~10–29 | `--surface: #1a1a1a` → `#1e2530`, `--surface2: #242424` → `#2a3340`; added `--buy: #00bfff` and `--sell: #ff4444` tokens |
| Card accent borders | ~155–160 | `.card.win` border-left → `var(--buy)` (cyan); `.card.loss` → `var(--sell)` (red) |
| Popup background | ~411 | `background:#1a1a1a` → `#1e2530` |
| Popup BUY/SELL tags | ~419–420 | `.buy` tag → `rgba(0,191,255,0.2)/#00bfff`; `.sell` tag → `rgba(255,68,68,0.2)/#ff4444` |
| Chart layout/grid | ~586–593 | layout bg `#1a1a1a`→`#1e2530`, textColor `#999`→`#7a8595`, grid lines `#222`→`#2a3340` |
| Candle series | ~606–611 | upColor/upBorder `#0f8f61`→`#1a1a1a`, downColor/downBorder `#c94a35`→`#f0f0f0`, wickUp `#0f8f61`→`#333333`, wickDown `#c94a35`→`#aaaaaa` |
| Overlay sizePct | ~683 | `sizePct: 8` → `sizePct: 10` |

### `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/das-overlay.js`

| Section | Lines | Change |
|---|---|---|
| `CONCEPT_GLYPHS` (T1, T7, D1, D6) | 44–67 | `c = isBuy ? '#0f8f61' : '#c94a35'` → `c = isBuy ? '#00bfff' : '#ff4444'`; `stroke="#0a0a0a"` → `stroke="#ffffff"`; `stroke-width="1"` → `"1.5"`; added 3-line comment explaining the palette |

## Verification Output

### 1. Pages load (HTTP)

```
orb.html 200
das-overlay.js 200
```

### 2. JS syntax check

```
$ node -c das-overlay.js && echo "das-overlay.js syntax OK"
das-overlay.js syntax OK
```

(`orb.html`'s inline JS is exercised via the headless browser run below.)

### 3. Headless browser (Playwright 1.61.0)

Ran `/tmp/verify-bw.cjs` against `http://127.0.0.1:8765/orb.html`:

```
screenshot saved: /tmp/orb-bw-after.png
STATS: {"cardCount":20,"markerCount":40,"winBorder":"rgb(0, 191, 255)","lossBorder":"rgb(255, 68, 68)","cardBgSample":"rgb(30, 37, 48)"}
FIRST MARKER: {"x":259.734375,"y":290.25,"marker":"<div data-trade-id=\"2026-06-30\" data-marker-type=\"entry\" data-marker-side=\"buy\" data-trade-direction=\"long\" ..."}
POPUP VISIBLE: true BG: rgb(30, 37, 48) TAG: {"side":"orb-exec-tag buy","bg":"rgba(0, 191, 255, 0.2)","color":"rgb(0, 191, 255)"}
CONSOLE ERRORS: []
PAGE ERRORS: []
```

Computed-style and runtime verification:

- **20 trade cards** rendered, **40 markers** (2 per card: entry + exit) — all cards still load data and paint
- **Card surface**: `rgb(30, 37, 48)` = `#1e2530` ✓
- **Win card border-left**: `rgb(0, 191, 255)` = `#00bfff` ✓ cyan
- **Loss card border-left**: `rgb(255, 68, 68)` = `#ff4444` ✓ bright red
- **Popup background**: `rgb(30, 37, 48)` = `#1e2530` ✓ matches card surface
- **Buy popup tag**: bg `rgba(0, 191, 255, 0.2)`, color `rgb(0, 191, 255)` ✓ cyan
- **Marker click → popup** still works (Esc dismiss also wired)

### 4. Canvas pixel sampling (`/tmp/verify-pixels.cjs`)

Confirmed the chart canvas itself paints the new background everywhere outside candle bodies:

```
bgPoints (4 samples across chart): all [30, 37, 48]  → #1e2530 ✓
canvasW: 398, canvasH: 174, dpr: 1
```

(White-down-candle body `#f0f0f0` and black-up-candle body `#1a1a1a` were also visible at expected positions when sampling over candle areas in the marker probe.)

### 5. SVG overlay attribute inspection (`/tmp/verify-overlay.cjs`)

```
buyAttr:  {fill: "#00bfff", stroke: "#ffffff", strokeWidth: "1.5"}  ✓
sellAttr: {fill: "#ff4444", stroke: "#ffffff", strokeWidth: "1.5"}  ✓
```

### 6. Screenshots

- `/tmp/orb-bw-after.png` (1440×2584, 448 KB) — full-page gallery with new palette
- `/tmp/orb-bw-popup.png` (1440×900, 181 KB) — execution popup with cyan BUY tag

## Acceptance Checklist

- [x] Up candles `#1a1a1a`, down candles `#f0f0f0` (border matches fill, wicks differentiated)
- [x] Chart background `#1e2530` (blue-gray); grid lines `#2a3340`; text `#7a8595`
- [x] Card surface `#1e2530` (via `--surface` var)
- [x] `.card.win` border-left = `#00bfff`; `.card.loss` = `#ff4444`
- [x] Buy triangle fill `#00bfff`, sell fill `#ff4444`, stroke `#ffffff` width 1.5 (T1/T7/D1/D6 all updated)
- [x] Triangle `sizePct` bumped from 8 to 10
- [x] Popup background `#1e2530`
- [x] Popup BUY/SELL tag colors match new palette
- [x] No changes to `server.py` or `index.html`
- [x] Chart logic / breakout detection / click handling / Esc dismiss all intact
- [x] `node -c das-overlay.js` passes
- [x] Headless browser: 0 console errors, 0 page errors
- [x] All files served by local server return HTTP 200
- [x] Real screenshots written to `/tmp/orb-bw-after.png` and `/tmp/orb-bw-popup.png`

## Files Modified

- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/orb.html`
- `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/das-overlay.js`

## Issues Encountered

None. All edits applied cleanly; verification at the SVG-attribute, computed-CSS, canvas-pixel, and runtime-behavior levels all confirm the new palette. P&L badges and `pnl-badge.pos/.neg` were intentionally left as green/red per the brief's explicit instruction (universal P&L convention). Volume histogram colors still use the muted green/red palette — also intentional, since the brief only specified candle + chart + triangle + popup + accent changes.
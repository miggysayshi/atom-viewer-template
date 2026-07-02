# atom-viewer-template

Yahoo Finance intraday backtester built on TradingView's Lightweight Charts v5.

## Run

```bash
python3 server.py             # serves on :8765
# open http://localhost:8765/orb.html
```

## Pages

- `orb.html` — ORB (Opening Range Breakout) gallery: 20 trade cards, 15-min default OR window, normalized $100 risk per trade, B/W candles on olive green, premarket/after-hours washes, OR H/L + stop/target dashed price lines, cyan/red execution triangles, click popups, bottom-strip collapsed by default
- `index.html` — interactive chart viewer (single ticker)
- `bg-sketches.html` — 6 background color variants
- `marker-concepts.html` — execution marker style reference
- `concepts/` — 10 v1 (data) + 10 v2 (chart + data) trade-detail concept sketches

## Layout

- `server.py` — Python HTTP server, `/api/orb?symbol=...&or=15&days=20&interval=5m` route, bad-wick clamp (RTH 5×, premarket 3×, post-market 3×), 3N target, OR-opposite stop, first-hit exit (target/stop/EOD, stop wins same-bar), MFE/MAE entry→exit, normalized-risk sizing
- `das-overlay.js` — reusable SVG execution marker overlay factory

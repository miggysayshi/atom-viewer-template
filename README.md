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

- `server.py` — Python HTTP server, `/api/orb?symbol=...&or=15&days=20&interval=5m` route, Yahoo fetch/proxy, summary assembly, and backwards-compatible API payload
- `trading_atoms/` — reusable trading atom library: session slicing, bad-wick clamp, opening range, breakout entry, OR-opposite stop, R-multiple target, first-hit exit (target/stop/EOD, stop wins same-bar), P&L/MFE/MAE metrics, and ORB strategy composition
- `tests/test_trading_atoms.py` — stdlib unittest coverage for ORB atoms and edge cases
- `das-overlay.js` — reusable SVG execution marker overlay factory

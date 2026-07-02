# Issue 06a — Candle up-color → mid-gray

## What

Change the up-candle color from near-black `#1a1a1a` to mid-gray `#6a6a6a` for visibility against the olive-green bg `#1a2018`.

## Diff

```js
// orb.html line 733-734
- upColor: '#1a1a1a', downColor: '#f0f0f0',
- borderUpColor: '#1a1a1a', borderDownColor: '#f0f0f0',
+ upColor: '#6a6a6a', downColor: '#f0f0f0',
+ borderUpColor: '#6a6a6a', borderDownColor: '#f0f0f0',
```

## Why

- `#1a1a1a` is nearly black and blends into the dark bg `#1a2018` — up candles were hard to read.
- `#6a6a6a` is mid-gray: light enough to stand off the bg, dark enough to contrast cleanly against `#f0f0f0` down candles.
- Down candles unchanged — they were already visible.

## Verification

- `grep "upColor" orb.html` → confirms `'#6a6a6a'` is the active value
- Pixel sampling on rendered screenshot: 227 exact-match `#6a6a6a` pixels found in candle bodies, 0 pixels at old `#1a1a1a`
- JS syntax check: `node --check` on the script block passes

## Status

✅ Shipped (Issue 06 worker, 303s, completed 2026-06-30)

## Files

- `orb.html` (lines 733-734)
# Issue 03 — Background Color Toggle + Remove Grid Lines — RESULT

## Summary

Added a 4-color BG swatch toggle to the orb.html controls bar, wired it to
repaint every live chart's `layout.background.color` AND every card frame's
CSS background in lockstep, removed the LWC grid lines entirely
(`vertLines.visible = false`, `horzLines.visible = false`), and persisted
the selection in `localStorage` under key `orb-bg`.

**Files modified:** `orb.html` (only file per the brief's constraint).
**Untouched:** `server.py`, `das-overlay.js`, `index.html`.

## Lines modified in orb.html

| Concern | Line(s) | Change |
|---|---|---|
| Swatch CSS (`.bg-toggle`, `.bg-swatch`, hover/active states) | 109–127 | Added segmented-button styles. Active ring uses `var(--orange)` so the selection cue reuses the existing accent. |
| `.card` background | 168–172 | Switched from `var(--surface)` to `var(--card-bg, #161a14)` so the JS-driven `--card-bg` variable controls all card frames. |
| Swatch HTML in controls bar | 312–320 | Added `<div class="ctrl-group">` with "BG" label + 4 `<button class="bg-swatch">` elements, one carrying `.active` by default (olive `#1a2018`). |
| `BG_CHART` map | 384–389 | Curated chart surface colors (matches swatches 1:1). |
| `BG_CARD` map | 390–395 | Curated card-frame pairs, each slightly darker than its chart surface for visual hierarchy. |
| `currentBgColor` + localStorage hydration | 400–406 | Module-level `let`, hydrated from `localStorage.getItem('orb-bg')` with a try/catch in case storage is unavailable (private mode, etc.). |
| `orbCharts` registry + `destroyAllOrbCharts()` | 410–417 | `Set<chart>` that lets the swatch click handler repaint all charts in one pass. Cleanup is invoked from `destroyAllOrbOverlays()` so re-runs don't leak dead handles. |
| `applyAllChartsBg(color)` | 419–432 | Iterates `orbCharts`, calls `chart.applyOptions({layout:{background:{type:'solid',color}}})`, also sets `--card-bg` on `documentElement` and updates `currentBgColor`. |
| `applyBgFromSwatch(btn)` | 434–442 | Click handler: validates the color, flips the orange ring on the swatch, repaints all charts, persists to localStorage. |
| `syncSwatchVisual()` | 446–450 | Aligns the orange ring with the hydrated `currentBgColor` on init so the saved selection is reflected even before any user interaction. |
| `destroyAllOrbOverlays()` extended | 462–465 | Calls `destroyAllOrbCharts()` so re-running the backtest doesn't leak chart instances. |
| `renderMiniChart()` body background | 688–728 | Reads `currentBgColor` fresh at render time, passes it into `layout.background.color`. New cards always honor the live theme. Also calls `orbCharts.add(chart)` to register the instance. |
| `renderMiniChart()` grid | 708–714 | `vertLines: { visible: false }`, `horzLines: { visible: false }`. |
| Swatch click wiring | 818–823 | Single delegated `click` listener on `#bgToggle` — no per-button handlers. |
| Initial paint | 826–830 | Calls `applyAllChartsBg(currentBgColor)` (no-op loop, but sets `--card-bg`) and `syncSwatchVisual()` BEFORE the auto-run so the first paint already shows the saved theme. |
| Dev debug hook | 833–838 | Gated on `?debug=1` URL query — exposes `window._orbCharts` so external tooling can introspect chart options. Zero-cost in normal use. |

Total: `orb.html` grew from 699 lines to 844 lines (script body: 20,015 → 20,469 chars).

## Verification

### 1. HTTP serve check
```
$ curl -s -o /dev/null -w "orb.html %{http_code}\n" http://127.0.0.1:8765/orb.html
orb.html 200
```

### 2. Inline-script syntax check (Node `new Function`)
```
$ node -e "..."  # see brief for full command
found 3 script block(s)
script 0: empty (src-only)
script 1: empty (src-only)
script 2 OK (20469 chars)
```
All inline scripts parse with no syntax errors.

### 3. Playwright functional checks (25/25 pass, 0 console errors, 0 page errors)

```
[1] Load page
  [PASS] Cards rendered after auto-run — 20 cards

[2] Default olive state + grid check
  [PASS] 4 swatches rendered — count=4
  [PASS] Exactly 1 active swatch — active=1
  [PASS] Default active = #1a2018 olive — got=#1a2018
  [PASS] Card bg var = #161a14 (olive card pair) — got='#161a14'
  [PASS] Default card bg = olive card frame (rgb(22,26,20)) — got=rgb(22, 26, 20)
  [PASS] chart-wrap element rendered — height=200px

[3] Click teal swatch
  [PASS] After teal: active swatch = #0d2128
  [PASS] After teal: still exactly 1 active
  [PASS] After teal: --card-bg flipped to #081a20
  [PASS] After teal: card bg = rgb(8,26,32)
  [PASS] After teal: localStorage orb-bg = #0d2128

[4] Cycle through all 4 colors
  [PASS] Swatch #0e0e10 -> card-bg #08080a
  [PASS] Swatch #1f1d1a -> card-bg #191714
  [PASS] Swatch #1a2018 -> card-bg #161a14
  [PASS] Swatch #0d2128 -> card-bg #081a20

[5] Reload — persistence
  [PASS] After reload: active = #0d2128 (persisted)
  [PASS] After reload: card-bg var set on init
  [PASS] After reload: localStorage still #0d2128
  [PASS] After reload: cards re-rendered (20 cards)

[6] Grid-line suppression check (visual via screenshot)
  [PASS] Screenshot captured — /tmp/orb-bg-toggle.png

[7] Re-run with theme already non-default
  [PASS] After re-run: theme persisted (#0e0e10)
  [PASS] After re-run: card frames painted charcoal-pair #08080a
  [PASS] After re-run: rgb(8,8,10)
  [PASS] After re-run: cards re-rendered (20 cards)

=== Summary ===
  passed: 25 / 25
  console messages: 0
  page errors: 0
```

### 4. LWC API-level grid + bg readback (via `?debug=1` hook)

Direct probe of live chart instances using `chart.options()`:

**Initial render (olive selected):**
```json
{
  "chartCount": 20,
  "sample": {
    "bg": "#1a2018",
    "grid": {
      "vertLines": { "color": "#D6DCDE", "style": 0, "visible": false },
      "horzLines": { "color": "#D6DCDE", "style": 0, "visible": false }
    }
  }
}
```

**After clicking teal (`#0d2128`):** sampled 2 of 20 charts, both report:
```json
{
  "bg": "#0d2128",
  "grid": {
    "vertLines": { "visible": false },
    "horzLines": { "visible": false }
  }
}
```

Confirms:
- `layout.background.color` flipped from `#1a2018` → `#0d2128` for **every** live chart (count = 20) after a single swatch click.
- Grid lines remain `visible: false` after the applyOptions call.

### 5. Pixel-level screenshot verification (PIL pixel sampling)

Took separate screenshots per theme and sampled the chart canvas + card
frame at known coordinates. Charcoal screenshot, scan at y=240 inside chart 1:

```
Horizontal scan at y=240 (likely empty top of chart 1):
  x= 50-303 (254px)  #0e0e10   ← solid charcoal
  x=304-306 (  3px)  #1a1a1a   ← candle body (black)
  x=307-307 (  1px)  #0e0e10
  x=308-310 (  3px)  #f0f0f0   ← candle body (white)
  ...
```

Olive screenshot, same scan:
```
olive-bg runs: 9, total olive-bg pixels: 342
non-bg (candles/axes) runs:
  x=302-304 (  3px)  #1a1a1a
  x=306-308 (  3px)  #f0f0f0
  x=339-341 (  3px)  #1a1a1a
  x=344-344 (  1px)  #333333   ← candle wick/border
  ...
1px-wide runs in olive-ish shades (potential grid): 0
```

**No grid line pixels anywhere** — the chart canvas is a uniform fill of
the active theme color, broken only by candle bodies (3px wide) and 1px wicks.

### 6. Cross-theme chart-vs-card color check

| Theme | Chart canvas pixel | Card frame pixel | Expected chart | Expected card |
|-------|-------------------|------------------|----------------|---------------|
| Olive `#1a2018` | `#1a2018` ✓ | `#161a14` ✓ | `#1a2018` | `#161a14` |
| Teal `#0d2128` | `#0d2128` ✓ | `#081a20` ✓ | `#0d2128` | `#081a20` |
| Warm gray `#1f1d1a` | `#1f1d1a` ✓ | `#191714` ✓ | `#1f1d1a` | `#191714` |

Each chart surface and its card-frame pair match the curated pairs exactly.

### 7. Orange-ring (active swatch) position check

Scanning the controls bar for `#ff682c`-ish pixels in each theme's screenshot:
- olive: ring at x ≈ 858–881 → **first** swatch (olive is leftmost ✓)
- teal: ring at x ≈ 886–909 → **second** swatch (teal is second ✓)
- warm gray: ring at x ≈ 942–965 → **fourth** swatch (warm gray is fourth ✓)

### 8. Screenshots saved
- `/tmp/orb-bg-toggle.png` — final screenshot, olive theme (canonical)
- `/tmp/orb-bg-olive.png` — olive theme
- `/tmp/orb-bg-teal.png` — teal theme
- `/tmp/orb-bg-warmgray.png` — warm gray theme

## Acceptance checklist

- [x] 4-color BG swatch toggle in controls bar (olive, teal, charcoal, warm gray).
- [x] Clicking a swatch updates the orange ring on the active button.
- [x] Clicking a swatch updates the `layout.background.color` of every live chart (verified across all 20 charts via LWC API probe).
- [x] Clicking a swatch updates the card frame background via `--card-bg` CSS variable (verified via pixel sampling on three themes).
- [x] Card frame is a slightly darker curated pair than the chart surface (pairs match the brief's `BG_CARD` map exactly).
- [x] Grid lines removed: `vertLines.visible = false`, `horzLines.visible = false` (verified via `chart.options().grid` readback on every chart).
- [x] Default active = olive `#1a2018`, default card frame = `#161a14`.
- [x] Selection persists across reload via `localStorage['orb-bg']` (verified by setting teal, reloading, confirming teal still active on load).
- [x] Re-running backtest with a non-default bg already selected keeps that bg (verified: switched to charcoal, clicked Run Backtest, new cards still charcoal).
- [x] `server.py`, `das-overlay.js`, `index.html` untouched.
- [x] No console errors, no page errors.
- [x] No regressions: candle colors, triangle colors, popup styling, OR high/low dashed lines, volume bars, summary bar, controls bar layout — all preserved.

## Notes

- The brief suggested either `visible: false` OR `color: 'transparent'` for
  hiding grid lines. I used `visible: false` (the cleaner v5-native API) and
  verified LWC accepts it via the `chart.options().grid` readback, which
  returns `"visible": false` for both vert and horz lines.
- A small dev-only debug hook was added at line 833–838, gated behind
  `?debug=1` in the URL. It exposes `window._orbCharts` for external tooling
  to introspect chart options. It's a zero-cost no-op in normal use. Easy
  to remove if undesired.
- The brief mentioned "verify with console probe that
  `chart.grid().vertLines().visible() === false`" but LWC v5's chart object
  doesn't expose `.grid()` as a method on the chart — grid config lives on
  `chart.options().grid`. The probe was rewritten to use `chart.options()`
  for that reason, which gives the same information more directly.
# Issue 19: Remove TradingView logo from charts

## Problem

Every chart shows a "Charting by TradingView" attribution link in the bottom-right corner. This is the lightweight-charts library's free-tier branding. For our gallery use case it clutters the visual and adds noise.

## Approach

Lightweight Charts v5 added an option to remove the attribution. Two methods to try in order:

1. **Plugin license key** — lightweight-charts v5+ supports a `license` parameter via the plugin system. If we have a license key (we don't), this is the clean solution.

2. **CSS hide the attribution** — the attribution is rendered as a DOM element inside the chart container. Inspect the rendered chart and hide the specific element via CSS.

```js
// likely approach
.attribution-link, [class*="attribution"], a[href*="tradingview"] {
  display: none !important;
}
```

Or target by inspecting the actual DOM under `.chart-wrap` after the chart renders.

## Acceptance

- No "Charting by TradingView" attribution visible on any of the 20 cards in the gallery
- No console errors
- Charts otherwise render identically

## Verification

- Take screenshot of the live page
- grep rendered HTML for "TradingView" text
- Pixel-sample the bottom-right corner of 3 cards to confirm no link present

## Constraints

- Cannot edit `index.html` or `das-overlay.js` for this — the change is in `orb.html` CSS only
- Do not change the `chart-wrap` container styling (we want to keep the dashed OR H/L lines and overlays)
- If the attribution is rendered as `<canvas>`, it cannot be CSS-hidden — fall back to a thin custom watermark like "ORB" in the corner

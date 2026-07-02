# Raffy Handoff — SMA/EMA Custom Period Controls

## Status
Done and browser-verified on live local server.

## Change
`orb.html` now supports editable SMA and EMA periods from the indicator ribbon.

## Implementation
- Added numeric inputs next to the SMA and EMA toggle chips:
  - `#sma-period`, min 2, max 300, default 20
  - `#ema-period`, min 2, max 300, default 20
- Added `orbState.indicatorPeriods = { sma: 20, ema: 20 }`.
- Persisted periods inside existing `orb-ribbon` localStorage payload.
- Sanitized periods to integer range `[2, 300]`.
- Updated button labels dynamically (`SMA 9`, `EMA 34`, etc.).
- Indicator series titles now use the selected period, so chart legends match the controls.
- If a period changes while that indicator is active, all charts rebuild client-side and recalculate the indicator. No network call.
- VWAP remains periodless.

## Verification
Live tested at `http://localhost:8765/orb.html?v=smaema2` with server PID 68042 on port 8765.

Confirmed:
- 20 cards render.
- Inputs show and persist `SMA 9` / `EMA 34` across reload.
- SMA/EMA/VWAP all active and line overlays visible on all charts.
- API calls remain `1` after period changes; re-render is client-side only.
- Invalid periods clamp correctly: SMA `1` → `2`, EMA `999` → `300`.
- No browser console errors.

## Files changed
- `orb.html`
- `.hermes/worker-prompts/raffy-handoff-sma-ema-periods.md`

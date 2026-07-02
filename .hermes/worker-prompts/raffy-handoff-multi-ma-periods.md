# Raffy Handoff — Multi-period SMA/EMA Inputs

## Status
Done and browser-verified on live local server.

## Change
SMA and EMA period inputs now accept comma-separated lists.

Examples:
- SMA input: `10, 20, 30` → renders `SMA 10`, `SMA 20`, `SMA 30`
- EMA input: `10, 20, 30` → renders `EMA 10`, `EMA 20`, `EMA 30`

## Implementation
- Converted SMA/EMA inputs from `type=number` to `type=text` with comma-list placeholders.
- `orbState.indicatorPeriods` now stores arrays: `{ sma: [20], ema: [20] }`.
- Added parser/sanitizer for comma lists:
  - clamps values to `[2, 300]`
  - dedupes repeated values
  - ignores invalid tokens
  - preserves input order
- SMA/EMA rendering now creates one Lightweight Charts `LineSeries` per requested period.
- Series registry now stores arrays of handles for SMA/EMA so toggle-off removes every line cleanly.
- Added multiple colors for SMA and EMA sets.
- Existing single-period persisted values remain backwards-compatible.
- Period lists persist in the existing `orb-ribbon` localStorage payload.

## Verification
Live tested at `http://localhost:8765/orb.html?v=multi-ma2`.

Confirmed:
- 20 cards render.
- Controls show `SMA 10, 20, 30` and `EMA 10, 20, 30`.
- Inputs persist through reload as `10, 20, 30`.
- Chart legends show separate labels for `SMA 10`, `SMA 20`, `SMA 30`, `EMA 10`, `EMA 20`, `EMA 30`, plus `VWAP`.
- Multiple MA lines visible on charts.
- API calls stay at `1`; changes rebuild charts client-side only.
- Console has no errors.
- Clamp/dedupe test: `1, 10, 10, 999, abc` → `2, 10, 300`; `5, 15, 15, 301` → `5, 15, 300`.

## Files changed
- `orb.html`
- `.hermes/worker-prompts/raffy-handoff-multi-ma-periods.md`

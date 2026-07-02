# Raffy Handoff — Trading Atoms Extraction

## Status
Done and verified on live server.

## User request
Extract trading atoms like stop loss, entry, exit, and targets into a reusable library, organized so future strategies can call them easily.

## Model routing
- Parent/orchestrator: gpt-5.5 via openai-codex
- Fanout workers: MiniMax-M3
- Workers did read-only design/audit slices; parent synthesized and implemented.

## What changed

### New package: `trading_atoms/`
- `types.py` — atom dataclasses:
  - `OpeningRangeAtom`
  - `EntryAtom`
  - `StopAtom`
  - `TargetAtom`
  - `ExitAtom`
  - `MetricsAtom`
- `sessions.py` — ET constants, session classification, ET annotation, chart-bar serialization.
- `cleaning.py` — shared bad-wick clamp atom. Used by both normal ORB path and 1m bars path.
- `range.py` — opening range + breakout entry detection.
- `stops.py` — OR-opposite stop and R-multiple target.
- `exits.py` — first-hit exit scan; preserves same-bar stop-wins rule and EOD fallback.
- `performance.py` — P&L, MFE/MAE, R multiple helpers.
- `strategies/orb.py` — ORB strategy composed from atoms.
- `pipeline.py` — tiny generic runner for future strategy calls.

### `server.py`
- `run_orb_for_day()` is now a thin shim into `trading_atoms.strategies.orb.run_orb_for_day`.
- `_clamp_wicks_for_session()` now calls the shared `clamp_bad_wicks()` atom.
- `/api/orb` legacy response shape is preserved:
  - `entry`, `exit`, `direction`, `entry_ts`, `exit_ts`, `stop_price`, `target_price`, `exit_reason`, `pnl`, `pnl_pct`, `mfe`, `mae`, `bars`, optional `bars_1m`.
- Added additive `trade.atoms` payload for future strategy/UI consumers:
  - `schema_version`, `strategy`, `params`, `opening_range`, `entry`, `stop`, `target`, `exit`, `risk`, `metrics`.

### Tests
- Added `tests/test_trading_atoms.py` using stdlib `unittest`.
- Covers:
  - no breakout
  - long target hit
  - short stop hit
  - same-bar target+stop collision → stop wins
  - EOD exit uses last RTH close
  - same first bar breaking high+low keeps current long bias

### Docs
- README layout updated to mention `trading_atoms/` and tests.

## Verification
Commands run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile server.py trading_atoms/*.py trading_atoms/strategies/*.py tests/test_trading_atoms.py
curl -s 'http://localhost:8765/api/orb?symbol=SPY&or=15&days=5&interval=5m'
```

Results:
- Unit tests: `Ran 6 tests ... OK`
- Py compile: OK
- API smoke:
  - `trades 5`
  - legacy fields present: `True`
  - `atoms.schema_version = 1`
  - expected atom keys present.
- Browser smoke at `http://localhost:8765/orb.html?v=atoms1`:
  - 20 cards rendered
  - 1 `/api/orb` call
  - no console messages / JS errors
  - top strip and detail strip still populated.

## Notes
- `atoms` is additive. Existing frontend still reads legacy fields, so this is safe for current UI.
- Current behavior intentionally preserved:
  - long wins if one bar breaches OR high and low simultaneously during entry detection
  - stop wins same-bar target+stop collision
  - EOD exit uses last RTH bar close, not post-market

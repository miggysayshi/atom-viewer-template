# Trading Atom Registry

Additive registry for validated Trading Atoms. Do not rewrite or duplicate prior atoms; append new atoms/conventions and compose them in strategies.

## Conventions

- **Additive only:** preserve existing atom names/semantics; add a new atom or version when behavior changes materially.
- **Decompose before saving:** when a visual strategy is approved, break it into entry, stop, target, exit, sizing/risk, metrics, and rendering pieces; check whether each piece already exists before adding anything new.
- **No duplicates:** if an atom already exists, compose it; do not create a second copy inside a strategy module.
- **No hindsight:** every atom must declare what data is known at decision time.
- **Visual-first:** atoms are promoted only after Miguel visually approves chart behavior.
- **RTH default:** strategy decisions use regular trading hours only unless explicitly specified. Pre/post bars may render as context.
- **Stop execution:** a stop line is not an exit. Strategies must scan post-entry bars for first stop hit before fallback exit.

## Timeframe / data atoms

### `intraday_timeframe_spectrum_v1`

- Files: `trading_atoms/entries.py`, `server.py`, `orb.html`
- Type: data/timeframe normalization atom
- Functions/UI:
  - `normalize_timeframe(...)`
  - `timeframe_seconds(...)`
  - `_source_interval_for_strategy_and_risk_tf(...)`
  - Strategy TF, Risk TF, Interval, and Resolution controls
- Canonical intraday spectrum:
  - `1m`, `2m`, `3m`, `5m`, `10m`, `15m`, `30m`, `1h`, `4h`
- Alias rules:
  - `1hr` -> `1h`
  - `4hr` -> `4h`
- Source/aggregation rules:
  - Native Yahoo intervals are used when available.
  - Synthetic intervals fetch the nearest finer native source and aggregate: `3m <- 1m`, `10m <- 5m`, `4h <- 1h`.
  - Mixed Strategy TF / Risk TF requests fetch the finest needed source interval, preventing lower-timeframe risk logic from silently degrading.
- Purpose: keep every timeframe-bearing control and strategy path on Miguel's full intraday spectrum; no subset selectors and no daily/weekly leakage in this visual-check workflow.

## Entry atoms

### `streak_reversal_close_entry_v1`

- File: `trading_atoms/entries.py`
- Type: entry atom
- Function: `find_streak_reversal_close_entry(...)`
- Parameters:
  - `timeframe`: `1m`, `5m`, `15m`, `1h`
  - `direction_mode`: `both`, `long`, `short`
  - `streak_len`: default `3`
- Entry rules:
  - `>=3` green candles then first red candle close → short.
  - `>=3` red candles then first green candle close → long.
  - Entry price = trigger candle close.
  - Entry time = trigger candle close edge.
  - Entry marker uses `entry_ts=<close edge>`, `entry_bar_ts=<bar start>`, `entry_anchor='bar_close'`.
- Purpose: reusable close-entry atom that can be composed with different stops/exits/targets/filters.

### `premarket_reentry_entry_v1`

- File: `trading_atoms/premarket.py`
- Type: entry atom
- Function: `find_premarket_reentry_entry(pm_range, annotated_bars, *, direction_mode='both')`
- Companion: `premarket_range(annotated_bars)` / `PremarketRangeAtom` (same module).
- Parameters:
  - `pm_range`: `PremarketRangeAtom` (PMH/PML from same ET day premarket bars).
  - `annotated_bars`: list of bars annotated via `annotate_et` (pre + RTH + post).
  - `direction_mode`: `both` (default), `long`, `short`.
- Entry rules:
  - **Short (failed PMH breakout):** first RTH bar whose `close` is back inside the premarket range (`PML <= close <= PMH`) **after** an earlier bar traded above PMH (`high > PMH`). Entry price = trigger bar close.
  - **Long (failed PML breakdown):** first RTH bar whose `close` is back inside the premarket range **after** an earlier bar traded below PML (`low < PML`). Entry price = trigger bar close.
  - Excursion and re-entry may coincide on a single bar (wide doji: wick above PMH, close back inside).
  - Anti-hindsight: only state available at the trigger bar is consulted (current bar's high/low + own close); no future bars are read.
  - Rule strings: `pmh_failed_breakout_reentry` (short) and `pml_failed_breakdown_reentry` (long); `rule_ref` is the breached PM level (PMH or PML).
- Purpose: reusable close-confirmed re-entry atom for failed PMH/PML breakouts; composes with `current_extrema_stop` + `stop_or_market_close_exit` (Miguel's spec: stop = current day HOD/LOD known at entry).

### `premarket_breakout_entry_v1`

- File: `trading_atoms/premarket.py`
- Type: entry atom (close-confirmed breakout)
- Functions:
  - `premarket_range(annotated_bars, *, date=None) -> PremarketRangeAtom | None`
  - `find_premarket_breakout_entry(pm_range, annotated_bars, *, direction_mode='both') -> EntryAtom | None`
- Range atom:
  - `premarket_range` derives PMH/PML from same-ET-day premarket-session bars
    (`session_name == 'pre'`); RTH and post-market bars are ignored.
- Entry rules:
  - Long: first RTH bar whose `close > pmh` triggers long at that close.
  - Short: first RTH bar whose `close < pml` triggers short at that close.
  - **Price rule = bar close** (recorded in atom `rule` field):
    `premarket_high_breakout_close` / `premarket_low_breakdown_close`.
    A wick that breaches PMH/PML but closes inside is **not** a breakout.
- Anti-hindsight:
  - PMH/PML come exclusively from premarket-session bars; RTH and post-market
    bars never leak into the range.
  - Only RTH bars (`MARKET_OPEN <= et.time < MARKET_CLOSE`) are scanned.
- Same-bar dual-direction precedence: long wins (matches `detect_breakout`).
- Parameters:
  - `direction_mode`: `both` (default), `long`, `short`.
- Purpose: reusable close-confirmed PMH/PML breakout entry atom that can be
  composed with different stops/exits/targets/filters.

### `three_bar_pivot_reversal_entry_v1`

- File: `trading_atoms/entries.py`
- Type: entry atom
- Function: `find_three_bar_pivot_reversal_entry(...)`
- Visual approval: Miguel approved after next-candle-open correction.
- Parameters:
  - `timeframe`: `1m`, `5m`, `15m`, `1h`
  - `direction_mode`: `both`, `long`, `short`
- Entry rules:
  - Short: three-candle high pattern `high < higher high > lower high`; after the third candle completes, enter short on the next candle open.
  - Long: three-candle low pattern `low > lower low < higher low`; after the third candle completes, enter long on the next candle open.
  - Entry price = next candle open.
  - Entry time = next candle start.
  - Entry marker uses `entry_ts=<next candle start>`, `entry_bar_ts=<next candle start>`, `entry_anchor='bar_open'`.
- Anti-hindsight:
  - Pattern is detected only after three completed candles.
  - Entry uses the next candle open after the completed signal pattern.
  - One-bar stop mode must use the completed signal candle high/low, not the future entry candle high/low.
- Purpose: reusable Larry Williams-style pivot reversal entry atom that can be composed with different stops/exits/targets/filters.

## Indicator helpers

### `ema`

- File: `trading_atoms/indicators.py`
- Type: pure indicator helper
- Signature: `ema(values, period=9) -> list[float | None]`
- Behavior:
  - `alpha = 2 / (period + 1)` smoothing.
  - Seed = SMA of the first `period` inputs.
  - Indexes before the warmup window return `None`.
- Purpose: dependency-free EMA that backs `find_ema_vwap_cross_entry`.

### `vwap`

- File: `trading_atoms/indicators.py`
- Type: pure indicator helper
- Signature: `vwap(bars) -> list[float]`
- Behavior:
  - Typical = `(high + low + close) / 3` weighted by `volume` (zero/missing volume is treated as 1 share so the ratio stays well-defined).
  - Returns cumulative session VWAP per bar.
- Purpose: dependency-free VWAP that backs `find_ema_vwap_cross_entry`.

### `sma`

- File: `trading_atoms/indicators.py`
- Type: pure indicator helper
- Signature: `sma(values, period=20) -> list[float | None]`
- Behavior:
  - Simple moving average aligned to input.
  - Indexes before the warmup window return `None`.
- Purpose: generic moving-average reference for filters and strategy atoms.

### `atr`

- File: `trading_atoms/indicators.py`
- Type: pure volatility helper
- Signatures:
  - `true_range(bars) -> list[float]`
  - `atr(bars, period=14) -> list[float | None]`
- Behavior:
  - True range uses Wilder definition: max(high-low, abs(high-prev_close), abs(low-prev_close)).
  - ATR uses Wilder smoothing after an SMA seed.
  - Indexes before the warmup window return `None`.
- Purpose: normalize extension/risk distances by recent volatility.

### `average_candle_range`

- File: `trading_atoms/indicators.py`
- Type: pure volatility helper
- Signature: `average_candle_range(bars, period=20) -> list[float | None]`
- Behavior:
  - SMA of `high - low` candle length.
  - Indexes before the warmup window return `None`.
- Purpose: alternate normalization basis for extension filters when ATR is too gap-aware.

## Filter atoms

### `overextension_distance_filter_v1`

- File: `trading_atoms/filters.py`
- Type: filter atom
- Class/function:
  - `OverextensionFilterAtom`
  - `distance_overextension_filter(...)`
- Sources:
  - `vwap`: current close distance from cumulative session VWAP.
  - `ema`: current close distance from EMA(`lookback`).
  - `sma`: current close distance from SMA(`lookback`).
- Measures:
  - `atr`: distance measured in ATR(`lookback`) units.
  - `avg_candle_range`: distance measured in average high-low candle length units.
- Rule:
  - `distance_multiple = abs(close - reference) / basis_value`.
  - `is_overextended = distance_multiple > threshold`.
  - `side`: `above`, `below`, or `at` reference.
- Anti-hindsight:
  - Default evaluates the latest known bar only.
  - Optional `index` slices bars through that index before computing reference/basis.
  - Warmup-missing or zero-basis returns `ready=False`, `is_overextended=False`, `reason='insufficient_history'`.
- Purpose: reusable entry guard to skip stocks that are too extended from VWAP/EMA/SMA by ATRs or average candle length.

## Stop atoms

### `opposite_side_stop`

- File: `trading_atoms/stops.py`
- Type: stop atom
- Used by ORB.
- Behavior:
  - Long stop = opening range low.
  - Short stop = opening range high.

### `current_extrema_stop`

- File: `trading_atoms/stops.py`
- Type: stop atom
- Inputs: `entry`, `rth_bars`, `known_through_ts`, `direction`
- Behavior:
  - Long: stop = current RTH LOD known through trigger/entry candle close.
  - Short: stop = current RTH HOD known through trigger/entry candle close.
  - Excludes all future bars after `known_through_ts`.
- Purpose: avoid hindsight-biased full-day HOD/LOD stops.

### `one_bar_stop`

- File: `trading_atoms/stops.py`
- Type: stop atom
- Inputs: `entry`, `entry_bar`, `direction`
- Behavior:
  - Long: stop = entry candle low.
  - Short: stop = entry candle high.
  - Returns `None` when risk is non-positive.
- Purpose: test tight opposite-side-of-entry-candle stops against any close-entry atom.

## Target atoms

### `r_multiple_target`

- File: `trading_atoms/stops.py`
- Type: target atom
- Behavior:
  - Long target = `entry + multiple * risk`.
  - Short target = `entry - multiple * risk`.

## Risk / sizing / performance atoms

### `sequential_reentry_collection_v1`

- File: `trading_atoms/reentries.py`
- Type: strategy orchestration atom
- Function: `collect_reentry_trades_for_day(day_bars, run_once, max_reentries=0)`
- Rule:
  - `max_reentries` is additive: `0` = initial trade only; `2` = initial + two re-entries.
  - After each trade exits, rerun the same single-entry strategy only on regular-session bars with `bar.ts > prior_exit_ts`.
  - Preserve non-regular-session bars so premarket-derived levels remain available to later re-entry passes.
  - Attach `reentry_index`, `reentry_label`, and unique `trade_id` to each collected trade.
- Anti-hindsight:
  - Later re-entry scans cannot reuse bars at or before the prior exit timestamp.
  - The atom controls sequencing only; the supplied `run_once` strategy remains responsible for its own entry/stop/exit no-lookahead rules.
- Purpose: make bounded same-day re-entry testing reusable across visual-check strategies without duplicating loop/control logic in HTTP/API code.

### `fixed_risk_position_size_v1`

- File: `trading_atoms/performance.py`
- Type: sizing atom
- Functions:
  - `fixed_risk_position_size(risk_per_share, risk_dollars=100)`
  - `normalized_risk_outcome(entry, stop_price, pnl_per_share, risk_dollars=100)`
  - `enrich_trade_outcome(trade, risk_dollars=100)`
- Rule:
  - `risk_per_share = abs(entry - stop_price)`.
  - `size = floor(risk_dollars / risk_per_share)`.
  - Whole-share floor sizing means actual risk is `<= risk_dollars`.
- Purpose: make trade outcomes comparable across symbols/stop widths.

### `normalized_risk_summary_v1`

- File: `trading_atoms/performance.py`
- Type: summary/performance atom
- Function: `summarize_normalized_trades(...)`
- Rule:
  - Summary P&L fields aggregate `trade.pnl_dollars`, not raw per-share `trade.pnl`.
  - `total_r = sum(trade.r_ratio)`.
  - `avg_r = total_r / trade_count`.
  - `best_trade`, `worst_trade`, `avg_win`, `avg_loss` use position-sized dollars.
- Purpose: keep top summary aligned with the normalized-risk trade-card template.

## Exit atoms

### `first_hit_exit`

- File: `trading_atoms/exits.py`
- Type: exit atom
- Used by ORB.
- Behavior:
  - Scans for first target/stop hit.
  - Same-bar target+stop collision defaults to stop wins.
  - If neither hits, exits EOD.

### `stop_or_market_close_exit`

- File: `trading_atoms/exits.py`
- Type: exit atom
- Inputs: `rth_bars_all`, `entry_ts`, `direction`, `stop`
- Behavior:
  - Long: first bar where `low <= stop.price` exits at stop.
  - Short: first bar where `high >= stop.price` exits at stop.
  - If no stop hit, exit at market close.
- Purpose: make stop levels executable, not merely visual/risk annotations.

## Strategy compositions / visual-check adapters

### `streak_reversal_visual_check_v1`

- File: `trading_atoms/strategies/three_green_red_short.py`
- Type: visual-check strategy composition
- Composes:
  - Entry: `streak_reversal_close_entry_v1`
  - Stop: `current_extrema_stop`
  - Target: none
  - Exit: `stop_or_market_close_exit`
  - Risk display: fixed `$100`
- Purpose: verify the streak-reversal entry atom on charts with a simple stop/MOC exit model.

### `premarket_breakout_visual_check_v1`

- File: `trading_atoms/strategies/premarket.py`
- Type: visual-check strategy composition
- Composes:
  - Entry: `premarket_breakout_entry_v1`
  - Stop: `current_extrema_stop`
  - Target: none
  - Exit: `stop_or_market_close_exit`
  - Risk display: fixed `$100`
- Purpose: test PMH/PML breakout entries on charts with current HOD/LOD stop execution.

### `premarket_reentry_visual_check_v1`

- File: `trading_atoms/strategies/premarket.py`
- Type: visual-check strategy composition
- Composes:
  - Entry: `premarket_reentry_entry_v1`
  - Stop: `current_extrema_stop`
  - Target: none
  - Exit: `stop_or_market_close_exit`
  - Risk display: fixed `$100`
- Purpose: test failed PMH/PML breakout re-entry entries on charts with current HOD/LOD stop execution.

### `larry_williams_3bar_visual_check_v1`

- File: `trading_atoms/strategies/larry_williams.py`
- Type: approved visual-check strategy composition
- UI/API selector: `strategy=larry_williams_3bar`
- Visual approval: Miguel said this looks great after the next-open timing and normalized summary/R changes.
- Composes:
  - Entry: `three_bar_pivot_reversal_entry_v1`
  - Stop: `current_extrema_stop` or signal-candle `one_bar_stop` via `stop_mode`
  - Target: none
  - Exit: `stop_or_market_close_exit`
  - Sizing/risk: `fixed_risk_position_size_v1`
  - Summary: `normalized_risk_summary_v1`
- Purpose: approved visual adapter for reviewing the Larry Williams three-bar pivot reversal atom family before using it in broader templates/strategies.

### `engulfing_close_visual_check_v1`

- File: `trading_atoms/strategies/engulfing_fvg.py`
- Type: visual-check strategy composition; not yet visually validated by Miguel.
- UI/API selector: `strategy=engulfing`
- Composes:
  - Entry: `engulfing_close_entry_v1`
  - Stop: `current_extrema_stop` or `one_bar_stop` via `stop_mode`
  - Target: none
  - Exit: `stop_or_market_close_exit`
  - Sizing/risk: `fixed_risk_position_size_v1`
  - Summary: `normalized_risk_summary_v1`
- Purpose: makes Miguel's close-through-previous-extreme engulfing atom visible in the strategy viewer.

### `fair_value_gap_retrace_visual_check_v1`

- File: `trading_atoms/strategies/engulfing_fvg.py`
- Type: visual-check strategy composition; not yet visually validated by Miguel.
- UI/API selector: `strategy=fvg_retrace`
- Composes:
  - Entry: `fair_value_gap_retrace_entry_v1`
  - Stop: FVG suggested stop (`candle2.high` for short, `candle2.low` for long) by default; `one_bar_stop` optional via `stop_mode=one_bar`
  - Target: none
  - Exit: `stop_or_market_close_exit`
  - Sizing/risk: `fixed_risk_position_size_v1`
  - Summary: `normalized_risk_summary_v1`
- Purpose: makes Miguel's FVG 50% retrace atom visible in the strategy viewer.

## Validated corrections from Miguel

1. **Close-price entries must anchor to candle close.** Do not price at close while visually anchoring at candle start.
2. **Current HOD/LOD means known at entry.** Do not use full-day HOD/LOD for stops unless strategy explicitly says hindsight/full-session reference.
3. **Stops must execute.** After placing stop, scan subsequent bars and exit at first hit before any market-close fallback.
4. **Approved strategies must be decomposed.** When Miguel says a visual strategy should become Trading Atoms, split it into entry/stop/target/exit/etc, check the library first, and only add missing atoms.

## Research candidates / not validated

### `engulfing_close_entry_v1`

- Status: **implemented visual-check candidate; not yet visually validated**.
- File: `trading_atoms/entries.py`
- Class/function:
  - `EngulfingCloseEntryAtom`
  - `find_engulfing_close_entry(...)`
- Requested by Miguel: short when current candle closes below the previous candle's low; long when current candle closes above the previous candle's high.
- Preferred/default opposite-candle filter:
  - Short: previous candle green, current candle red.
  - Long: previous candle red, current candle green.
  - `require_opposite_color=False` can loosen this later.
- Entry rules:
  - Short: `current.close < previous.low`, entry at current close.
  - Long: `current.close > previous.high`, entry at current close.
  - Entry marker uses `entry_ts=<close edge>`, `entry_bar_ts=<bar start>`, `entry_anchor='bar_close'`.
  - Same-bar dual qualification prefers short.
- Anti-hindsight: scans only adjacent previous/current candles after timeframe aggregation.
- Tests: `EngulfingCloseEntryTests`.
- Proposed selector: `strategy=engulfing`.

### `fair_value_gap_retrace_entry_v1`

- Status: **implemented visual-check candidate; not yet visually validated**.
- File: `trading_atoms/entries.py`
- Class/function:
  - `FairValueGapRetraceEntryAtom`
  - `find_fair_value_gap_retrace_entry(...)`
- Requested by Miguel: if chart leaves a fair value gap and later retraces 50% into the gap, enter; short stop reference = FVG candle high, opposite for long.
- FVG definition:
  - Bearish/short FVG: `candle1.low > candle3.high` (strict gap).
  - Bullish/long FVG: `candle1.high < candle3.low` (strict gap).
  - FVG candle = candle2 / displacement candle.
- Entry rules:
  - Short: future bar high reaches the 50% gap retrace level; entry price = retrace level.
  - Long: future bar low reaches the 50% gap retrace level; entry price = retrace level.
  - Entry marker uses `entry_ts=<retrace bar start>`, `entry_bar_ts=<retrace bar start>`, `entry_anchor='bar_open'`, `execution='fvg_midpoint_retrace_touch'`.
  - Suggested stop only: short `candle2.high`, long `candle2.low`; no separate stop atom yet.
- Anti-hindsight: gap is known after candle3; retrace decision uses first future bar that touches the configured retrace level.
- Tests: `FairValueGapRetraceEntryTests`.
- Proposed selector: `strategy=fvg_retrace`.

### `double_wick_reversal_entry_v1`

- Status: **queued visual-check candidate; not validated**.
- Requested by Miguel: double topping/bottoming wicks where the reversal wick is very long and >50% of full candle range.
- Proposed rule:
  - Double upper wick near same level → short at second wick candle close.
  - Double lower wick near same level → long at second wick candle close.
  - `upper_wick / (high-low) > 0.50` or `lower_wick / (high-low) > 0.50`; exact 50% does not qualify.
- Proposed selector: `strategy=double_wick_reversal`.
- Queue brief: `.hermes/worker-prompts/candle-vwap-strategy-queue/issue02-long-wick-double-top-bottom.md`.

### `vwap_rejection_entry_v1`

- Status: **queued visual-check candidate; not validated**.
- Requested by Miguel: VWAP rejection where stock taps VWAP and bounces.
- Proposed rule:
  - Long: above-VWAP context, candle taps VWAP, closes back above VWAP.
  - Short: below-VWAP context, candle taps VWAP, closes back below VWAP.
  - Uses existing `vwap` helper; distinct from demoted fashionably-late EMA/VWAP cross.
- Proposed selector: `strategy=vwap_rejection`.
- Queue brief: `.hermes/worker-prompts/candle-vwap-strategy-queue/issue03-vwap-rejection.md`.

### `fashionably_late_smb_setup_v2`

- Status: **visual-check candidate; not validated / not promoted**.
- Source research: SMB `The Accuracy AND Big Winners Combo Strategy` chapter evidence: “Stock turns off the low”, “Momentum builds back to VWAP”, “9 EMA crosses VWAP”, “Enter at the cross”, “Stop, target, and 3:1 risk/reward”. Transcript unavailable due YouTube/IP throttling, so this is still a hypothesis.
- Selector: `strategy=fashionably_late`.
- Current candidate composition:
  - Entry: `find_ema_vwap_cross_entry(...)` — close-confirmed EMA9/VWAP cross after 09:45 ET.
  - Stop variants: `one_bar_stop` (`stop=one_bar`) or `current_extrema_stop` (`stop=current_extrema`).
  - Target: existing `r_multiple_target(..., multiple=3.0)`.
  - Exit: existing `first_hit_exit` with conservative same-bar stop priority.
- Open ambiguity: “turns off the low/high”, “avoid choppy entries”, and exact best time windows are not mechanically recovered yet.
- Do not promote to validated atom until Miguel visually approves behavior.

### `smb_gap_playbook_candidates`

- Status: **research backlog; no validated atoms**.
- Source research: `.hermes/worker-prompts/smb-gap-playbook-research/result01-gap-playbook-atoms.md`.
- Primary source: SMB `Top 10 Gap Trading Mistakes You Must Avoid` (`Cz6YVuaRo38`). Evidence available locally: metadata description + 10 chapter titles only. Transcript blocked (`IpBlocked()` / HTTP 429), so no thresholds should be inferred.
- Highest-priority visual-check candidates:
  1. `gap_vwap_defense_entry_v1` — gap up + pullback to VWAP + hold/reclaim. Reuse `vwap`, `current_extrema_stop`, `r_multiple_target`, `first_hit_exit`. Missing: defense rule, volume rule, time window, gap-size filter.
  2. `key_level_failed_breakdown_reentry_v1` — parameterized generalization of `premarket_reentry_entry_v1` from PMH/PML to arbitrary key levels. Missing: approved key-level sources, excursion/reclaim rule, volume filter.
  3. `opening_drive_exhaustion_fade_entry_v1` — opening drive followed by exhaustion/reversal candle. Reuse queued reversal atoms where possible. Missing: drive definition, exhaustion trigger, stop placement.
  4. `tight_consolidation_volume_compression_entry_v1` — RTH tight range + volume compression + breakout. Missing: range width/window and compression thresholds.
- Filter-only ideas, not entries: `immediate_gap_chase_filter_v1`, `htf_resistance_gap_filter_v1`, `low_volume_gap_followthrough_filter_v1`.
- Distinct high-effort ideas: `high_tight_flag_entry_v1`, `absorption_at_highs_short_entry_v1`.
- Guardrail: do not promote any gap-playbook candidate until transcript/manual chart evidence resolves missing parameters.

### `trailing_stop_and_ma_target_candidates_2026_07_02`

- Status: **research/implementation backlog; not validated**.
- Requested by Miguel: reusable trailing-stop and target components:
  1. `previous_bar_low_trailing_stop_v1` / `previous_bar_high_trailing_stop_v1` — protective trailing stop based on prior completed bar.
  2. `ema_break_trailing_exit_9_v1` — exit on break of 9 EMA.
  3. `ema_break_trailing_exit_10_20_v1` — exit on break of 10/20 EMAs.
  4. `vwap_target_v1` — VWAP as take-profit target.
  5. `sma_target_1m_200_v1` — 1-minute 200 SMA as take-profit target.
  6. `sma_target_1m_100_v1` — 1-minute 100 SMA as take-profit target.
- Initial classification:
  - Previous-bar trailing stop: `stop-loss` candidate if implemented as a moving protective stop; exit rule fires when next bars cross the current stop.
  - EMA break trailing stops: likely `conditional-exit` candidate, unless represented as a moving stop line. Use close-confirmed break first to avoid intrabar ambiguity.
  - VWAP/SMA targets: `take-profit` candidates; target line is dynamic and must be known at each scanned bar, never future-filled.
- Anti-hindsight gates:
  - Previous-bar trailing stop for long can only ratchet upward using completed prior bar lows; short can only ratchet downward using completed prior bar highs.
  - EMA/VWAP/SMA values must be computed through the current/previous completed bar only; no future bars in target/stop placement.
  - 1m SMA targets require attached/resampled 1m bars even when the strategy entry timeframe differs.
- Proposed first implementation path:
  - Add generic dynamic exit resolver in `trading_atoms/exits.py` that scans post-entry bars and supports dynamic stop/target lines.
  - Add target helpers in `trading_atoms/stops.py` or a new `targets.py` for VWAP/SMA line targets.
  - Add tests before UI exposure; compare against `first_hit_exit` same-bar collision policy.
- Open ambiguity for Miguel: `10/20 EMA break` should be tested as both variants: (A) exit on close through either EMA, and (B) exit only after close through both EMAs. Default backlog preference: both-EMA break = stricter, fewer exits; either-EMA break = faster/tighter.

from __future__ import annotations

from ..entries import aggregate_clock, normalize_timeframe
from ..stops import one_bar_stop
from ..types import Direction, StopAtom


def lower_timeframe_one_bar_stop(
    *,
    entry_price: float,
    entry_ts: int,
    entry_direction: Direction,
    rth_bars_all: list[dict],
    strategy_timeframe: str,
    risk_timeframe: str | None,
    fallback_entry_bar: dict,
) -> tuple[StopAtom | None, dict | None, str]:
    """One-bar stop using last completed risk-TF bar before entry.

    If risk timeframe equals strategy timeframe, preserve legacy behavior by
    using the strategy entry bar supplied by the entry atom. If lower/different,
    aggregate raw RTH bars to risk TF and use the last completed risk bar with
    ``bar.ts < entry_ts``. This avoids overlapping/lookahead bars.
    """
    strategy_tf = normalize_timeframe(strategy_timeframe, default='15m')
    risk_tf = normalize_timeframe(risk_timeframe or strategy_tf, default=strategy_tf)
    if risk_tf == strategy_tf:
        return one_bar_stop(entry_price, fallback_entry_bar, entry_direction), fallback_entry_bar, risk_tf

    risk_bars = aggregate_clock(rth_bars_all, risk_tf)
    prior = [b for b in risk_bars if int(b['ts']) < entry_ts]
    if not prior:
        return None, None, risk_tf
    basis = prior[-1]
    return one_bar_stop(entry_price, basis, entry_direction), basis, risk_tf


def one_bar_stop_labels(direction: Direction, strategy_timeframe: str, risk_timeframe: str, basis_bar: dict | None) -> tuple[str, str]:
    lower_tf_stop = bool(basis_bar is not None and normalize_timeframe(risk_timeframe, default=strategy_timeframe) != normalize_timeframe(strategy_timeframe, default=strategy_timeframe))
    if lower_tf_stop:
        title = f"{risk_timeframe} 1-Bar Low Stop" if direction == 'long' else f"{risk_timeframe} 1-Bar High Stop"
        rule = 'lower_tf_one_bar_low_for_long' if direction == 'long' else 'lower_tf_one_bar_high_for_short'
    else:
        title = '1-Bar Low Stop' if direction == 'long' else '1-Bar High Stop'
        rule = 'entry_candle_low_for_long' if direction == 'long' else 'entry_candle_high_for_short'
    return title, rule

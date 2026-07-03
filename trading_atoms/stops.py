from __future__ import annotations

from .indicators import ema, sma, vwap
from .types import Direction, OpeningRangeAtom, StopAtom, TargetAtom


def opposite_side_stop(entry: float, or_range: OpeningRangeAtom, direction: Direction) -> StopAtom:
    if direction == 'long':
        stop_price = or_range.low
        risk = entry - stop_price
        rule_ref = or_range.low
    else:
        stop_price = or_range.high
        risk = stop_price - entry
        rule_ref = or_range.high
    return StopAtom(price=stop_price, risk=risk, rule='or_opposite', rule_ref=rule_ref)


def r_multiple_target(entry: float, stop: StopAtom, direction: Direction, multiple: float = 3.0) -> TargetAtom:
    if direction == 'long':
        price = entry + multiple * stop.risk
    else:
        price = entry - multiple * stop.risk
    return TargetAtom(price=price, multiple=multiple, rule='r_multiple', rule_ref=multiple)


def one_bar_stop(
    entry: float,
    entry_bar: dict,
    direction: Direction,
    *,
    rule: str = 'one_bar_stop',
) -> StopAtom | None:
    """Stop on the opposite side of the entry candle (1-bar stop).

    - Long: stop = ``entry_bar['low']``; risk = ``entry - stop``.
    - Short: stop = ``entry_bar['high']``; risk = ``stop - entry``.

    Returns ``None`` if risk would be non-positive (entry sits on or past the
    wrong side of its own candle), matching the defensive ``None`` contract
    used by :func:`current_extrema_stop`.

    Note: ``one_bar_stop`` is intentionally entry-bar-relative (not full-RTH
    extrema) and is "anti-tightening": the stop can only ever be expanded by
    future price action because the bar is fixed at entry.
    """
    if direction == 'long':
        stop_price = float(entry_bar['low'])
        risk = entry - stop_price
    else:
        stop_price = float(entry_bar['high'])
        risk = stop_price - entry
    if risk <= 0:
        return None
    return StopAtom(price=stop_price, risk=risk, rule=rule, rule_ref=stop_price)


def current_extrema_stop(
    entry: float,
    rth_bars: list[dict],
    *,
    known_through_ts: int,
    direction: Direction,
) -> StopAtom | None:
    """Stop at current RTH LOD/HOD known at entry time.

    Anti-hindsight stop atom:
    - long stop = lowest RTH low through the trigger/entry candle close
    - short stop = highest RTH high through the trigger/entry candle close

    Future bars after `known_through_ts` are intentionally excluded.
    """
    known_bars = [b for b in rth_bars if int(b['ts']) < known_through_ts]
    if not known_bars:
        return None
    if direction == 'long':
        stop_price = min(b['low'] for b in known_bars)
        risk = entry - stop_price
        rule = 'current_lod_at_entry'
    else:
        stop_price = max(b['high'] for b in known_bars)
        risk = stop_price - entry
        rule = 'current_hod_at_entry'
    if risk <= 0:
        return None
    return StopAtom(price=stop_price, risk=risk, rule=rule, rule_ref=known_through_ts)


def previous_bar_trailing_stop_snapshot(
    entry: float,
    rth_bars: list[dict],
    *,
    entry_ts: int,
    direction: Direction,
    initial_stop: StopAtom,
    known_through_ts: int,
) -> StopAtom:
    """Snapshot prior-bar trailing stop known before ``known_through_ts``.

    Long ratchets upward to prior completed bar lows after new highs. Short
    ratchets downward to prior completed bar highs after new lows. The current
    evaluation bar is excluded to avoid using today's bar to set today's stop.
    """
    current = float(initial_stop.price)
    known = [b for b in rth_bars if int(b['ts']) >= entry_ts and int(b['ts']) < known_through_ts]
    if not known:
        return initial_stop

    if direction == 'long':
        running_high = float(known[0]['high'])
        for b in known[1:]:
            if float(b['high']) > running_high:
                current = max(current, float(b['low']))
                running_high = float(b['high'])
    else:
        running_low = float(known[0]['low'])
        for b in known[1:]:
            if float(b['low']) < running_low:
                current = min(current, float(b['high']))
                running_low = float(b['low'])

    return StopAtom(
        price=round(current, 4),
        risk=round(abs(entry - current), 4),
        rule='previous_bar_trailing_stop',
        rule_ref=known[-1]['ts'],
    )


def ema_trailing_stop_snapshot(
    entry: float,
    rth_bars: list[dict],
    *,
    entry_ts: int,
    direction: Direction,
    fast_period: int = 10,
    slow_period: int = 20,
) -> StopAtom | None:
    """Entry-time EMA stop snapshot using the tightest available EMA."""
    known = [b for b in rth_bars if int(b['ts']) <= entry_ts]
    if not known:
        return None
    closes = [float(b['close']) for b in known]
    fast = ema(closes, period=fast_period)[-1]
    slow = ema(closes, period=slow_period)[-1]
    values = [v for v in (fast, slow) if v is not None]
    if not values:
        return None
    stop_price = max(values) if direction == 'long' else min(values)
    risk = abs(entry - stop_price)
    if risk <= 0:
        return None
    return StopAtom(price=round(stop_price, 4), risk=round(risk, 4), rule=f'ema_trailing_{fast_period}_{slow_period}_at_entry', rule_ref=round(stop_price, 4))


def vwap_target(*, direction: Direction, rth_bars: list[dict], evaluation_ts: int) -> TargetAtom | None:
    """Session VWAP target through ``evaluation_ts``; caller must pass one day."""
    eval_bars = [b for b in rth_bars if int(b['ts']) <= evaluation_ts]
    if not eval_bars:
        return None
    price = vwap(eval_bars)[-1]
    if price is None:
        return None
    return TargetAtom(price=round(price, 4), multiple=float('nan'), rule='vwap_session_through_bar', rule_ref=round(price, 4))


def sma_period_target(*, direction: Direction, rth_bars_1m: list[dict], evaluation_ts: int, period: int) -> TargetAtom | None:
    """1-minute SMA target through ``evaluation_ts``; returns None during warmup."""
    eval_bars = [b for b in rth_bars_1m if int(b['ts']) <= evaluation_ts]
    if not eval_bars:
        return None
    value = sma([float(b['close']) for b in eval_bars], period=period)[-1]
    if value is None:
        return None
    return TargetAtom(price=round(value, 4), multiple=float('nan'), rule=f'sma{period}_1m_target', rule_ref=round(value, 4))


def sma100_1m_target(*, direction: Direction, rth_bars_1m: list[dict], evaluation_ts: int) -> TargetAtom | None:
    return sma_period_target(direction=direction, rth_bars_1m=rth_bars_1m, evaluation_ts=evaluation_ts, period=100)


def sma200_1m_target(*, direction: Direction, rth_bars_1m: list[dict], evaluation_ts: int) -> TargetAtom | None:
    return sma_period_target(direction=direction, rth_bars_1m=rth_bars_1m, evaluation_ts=evaluation_ts, period=200)

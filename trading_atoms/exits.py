from __future__ import annotations

from .indicators import ema
from .types import Direction, ExitAtom, StopAtom, TargetAtom


def first_hit_exit(
    rth_bars_all: list[dict],
    *,
    entry_ts: int,
    direction: Direction,
    stop: StopAtom,
    target: TargetAtom,
    same_bar_priority: str = 'stop',
) -> ExitAtom | None:
    """Resolve exit with current ORB precedence.

    Scan RTH bars from entry bar forward. Same-bar target+stop collision exits
    at stop by default (current conservative behavior). If neither is hit,
    exit at final RTH close.
    """
    rth_after_entry = [b for b in rth_bars_all if b['ts'] >= entry_ts]
    if not rth_after_entry:
        return None

    for b in rth_after_entry:
        if direction == 'long':
            hit_target = b['high'] >= target.price
            hit_stop = b['low'] <= stop.price
        else:
            hit_target = b['low'] <= target.price
            hit_stop = b['high'] >= stop.price

        if hit_target and hit_stop:
            if same_bar_priority == 'target':
                return ExitAtom(price=target.price, bar=b, reason='target', same_bar_collision=True)
            return ExitAtom(price=stop.price, bar=b, reason='stop', same_bar_collision=True)
        if hit_target:
            return ExitAtom(price=target.price, bar=b, reason='target')
        if hit_stop:
            return ExitAtom(price=stop.price, bar=b, reason='stop')

    eod_bar = rth_bars_all[-1]
    return ExitAtom(price=eod_bar['close'], bar=eod_bar, reason='eod')


def stop_or_market_close_exit(
    rth_bars_all: list[dict],
    *,
    entry_ts: int,
    direction: Direction,
    stop: StopAtom,
) -> ExitAtom | None:
    """Resolve first stop hit after entry, else market-close exit.

    Use for visual-check atoms without targets. A stop line is not an exit by
    itself; this atom turns the stop into execution by scanning post-entry bars.
    """
    rth_after_entry = [b for b in rth_bars_all if int(b['ts']) >= entry_ts]
    if not rth_after_entry:
        return None
    for b in rth_after_entry:
        if direction == 'long' and b['low'] <= stop.price:
            return ExitAtom(price=stop.price, bar=b, reason='stop')
        if direction == 'short' and b['high'] >= stop.price:
            return ExitAtom(price=stop.price, bar=b, reason='stop')
    close_bar = rth_bars_all[-1]
    return ExitAtom(price=close_bar['close'], bar=close_bar, reason='market_close')


def previous_bar_trailing_exit(
    rth_bars_all: list[dict],
    *,
    entry_ts: int,
    direction: Direction,
    initial_stop: StopAtom,
) -> ExitAtom | None:
    """Resolve a prior-bar high/low trailing stop.

    At bar i, stop level only uses completed bars before i. Long ratchets to
    prior-bar lows after new highs; short ratchets to prior-bar highs after new
    lows. If no stop hit, exits at final RTH close.
    """
    bars = [b for b in rth_bars_all if int(b['ts']) >= entry_ts]
    if not bars:
        return None

    stop_price = float(initial_stop.price)
    if direction == 'long':
        running_high = float(bars[0]['high'])
        for b in bars:
            if float(b['low']) <= stop_price:
                return ExitAtom(price=round(stop_price, 4), bar=b, reason='stop')
            if float(b['high']) > running_high:
                stop_price = max(stop_price, float(b['low']))
                running_high = float(b['high'])
    else:
        running_low = float(bars[0]['low'])
        for b in bars:
            if float(b['high']) >= stop_price:
                return ExitAtom(price=round(stop_price, 4), bar=b, reason='stop')
            if float(b['low']) < running_low:
                stop_price = min(stop_price, float(b['high']))
                running_low = float(b['low'])

    close_bar = rth_bars_all[-1]
    return ExitAtom(price=close_bar['close'], bar=close_bar, reason='eod')


def ema_trailing_stop_exit(
    rth_bars_all: list[dict],
    *,
    entry_ts: int,
    direction: Direction,
    fast_period: int = 10,
    slow_period: int = 20,
    mode: str = 'both',
    price_source: str = 'close',
) -> ExitAtom | None:
    """Exit on EMA break, defaulting to close-confirmed dual-EMA break.

    Modes: ``both`` (default), ``either``, ``fast``, ``slow``. Price source:
    ``close`` or ``wick`` (long low / short high). Values before EMA warmup are
    skipped; if no break fires, exit at final RTH close.
    """
    if mode not in {'both', 'either', 'fast', 'slow'}:
        raise ValueError(f'unsupported ema trailing mode: {mode}')
    if price_source not in {'close', 'wick'}:
        raise ValueError(f'unsupported ema trailing price_source: {price_source}')

    if not rth_bars_all:
        return None
    closes = [float(b['close']) for b in rth_bars_all]
    fast = ema(closes, period=fast_period)
    slow = ema(closes, period=slow_period)

    for i, b in enumerate(rth_bars_all):
        if int(b['ts']) < entry_ts:
            continue
        fast_i = fast[i]
        slow_i = slow[i]
        if fast_i is None or slow_i is None:
            continue
        observed = float(b['close'])
        if price_source == 'wick':
            observed = float(b['low']) if direction == 'long' else float(b['high'])

        if direction == 'long':
            broke_fast = observed < fast_i
            broke_slow = observed < slow_i
        else:
            broke_fast = observed > fast_i
            broke_slow = observed > slow_i

        if mode == 'both':
            triggered = broke_fast and broke_slow
        elif mode == 'either':
            triggered = broke_fast or broke_slow
        elif mode == 'fast':
            triggered = broke_fast
        else:
            triggered = broke_slow
        if triggered:
            return ExitAtom(price=round(observed, 4), bar=b, reason='stop')

    close_bar = rth_bars_all[-1]
    return ExitAtom(price=close_bar['close'], bar=close_bar, reason='eod')

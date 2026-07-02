from __future__ import annotations

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

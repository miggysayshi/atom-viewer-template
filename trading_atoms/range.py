from __future__ import annotations

import datetime as dt

from .sessions import MARKET_OPEN
from .types import EntryAtom, OpeningRangeAtom


def opening_range(annotated_bars: list[dict], or_minutes: int) -> OpeningRangeAtom | None:
    or_end_time = (dt.datetime.combine(dt.date.today(), MARKET_OPEN) + dt.timedelta(minutes=or_minutes)).time()
    or_window = [b for b in annotated_bars if MARKET_OPEN <= b['et'].time() < or_end_time]
    if not or_window:
        return None
    rest_of_day = [b for b in annotated_bars if b['et'].time() >= or_end_time]
    rth_bars = [b for b in annotated_bars if MARKET_OPEN <= b['et'].time() < dt.time(16, 0)]
    return OpeningRangeAtom(
        high=round(max(b['high'] for b in or_window), 4),
        low=round(min(b['low'] for b in or_window), 4),
        minutes=or_minutes,
        bars=or_window,
        rest_of_day=rest_of_day,
        rth_bars=rth_bars,
    )


def detect_breakout(or_range: OpeningRangeAtom) -> EntryAtom | None:
    """First post-OR breakout.

    Preserves existing ORB behavior: if one bar breaches both high and low,
    long wins because the high check is evaluated first.
    """
    for b in or_range.rest_of_day:
        if b['high'] > or_range.high:
            return EntryAtom(
                price=or_range.high,
                direction='long',
                bar=b,
                rule='or_high_breakout',
                rule_ref=or_range.high,
            )
        if b['low'] < or_range.low:
            return EntryAtom(
                price=or_range.low,
                direction='short',
                bar=b,
                rule='or_low_breakdown',
                rule_ref=or_range.low,
            )
    return None

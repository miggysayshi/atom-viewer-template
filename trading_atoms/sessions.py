from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
MARKET_OPEN = dt.time(9, 30)
MARKET_CLOSE = dt.time(16, 0)
PRE_START = dt.time(4, 0)


def annotate_et(bars: list[dict], tz: ZoneInfo = ET) -> list[dict]:
    """Return shallow-copied bars with an ET datetime at key `et`."""
    return [{**b, 'et': dt.datetime.fromtimestamp(b['ts'], tz=tz)} for b in bars]


def session_name(et_time: dt.time) -> str:
    if et_time < MARKET_OPEN:
        return 'pre'
    if et_time < MARKET_CLOSE:
        return 'rth'
    return 'post'


def split_sessions(annotated_bars: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    pre = [b for b in annotated_bars if session_name(b['et'].time()) == 'pre']
    rth = [b for b in annotated_bars if session_name(b['et'].time()) == 'rth']
    post = [b for b in annotated_bars if session_name(b['et'].time()) == 'post']
    return pre, rth, post


def serialize_chart_bar(bar: dict) -> dict:
    """Frontend chart bar shape consumed by orb.html."""
    et_dt = bar.get('et') or dt.datetime.fromtimestamp(bar['ts'], tz=ET)
    return {
        'time': bar['ts'],
        'open': bar['open'],
        'high': bar['high'],
        'low': bar['low'],
        'close': bar['close'],
        'volume': bar['volume'],
        'et': et_dt.strftime('%H:%M'),
        'session': session_name(et_dt.time()),
    }

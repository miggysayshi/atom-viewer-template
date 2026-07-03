"""Sequential re-entry collection atom.

This module keeps re-entry sequencing out of HTTP/API code. Strategies remain
single-entry; this atom controls how many times the same single-entry runner can
be re-applied after prior exits.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

Trade = dict[str, Any]
Bar = dict[str, Any]
SingleEntryRunner = Callable[[list[Bar]], Optional[Trade]]


def collect_reentry_trades_for_day(
    day_bars: list[Bar],
    run_once: SingleEntryRunner,
    *,
    max_reentries: int = 0,
) -> list[Trade]:
    """Run a single-entry strategy repeatedly after each prior exit.

    max_reentries is additive: 0 = initial trade only, 2 = initial + two
    re-entries. Each re-entry keeps non-regular-session context (premarket
    levels etc.) but only exposes regular-session bars strictly after the prior
    exit timestamp, preventing same-bar loops and same-signal reuse.
    """
    max_reentries = max(0, min(int(max_reentries or 0), 10))
    trades: list[Trade] = []
    candidate_bars = list(day_bars)

    for reentry_index in range(max_reentries + 1):
        if not candidate_bars:
            break
        result = run_once(candidate_bars)
        if not result:
            break

        result['reentry_index'] = reentry_index
        result['reentry_label'] = 'initial' if reentry_index == 0 else f're-entry {reentry_index}'
        date = result.get('date') or 'unknown-date'
        entry_ts = int(result.get('entry_ts') or 0)
        result['trade_id'] = f"{date}-{reentry_index}-{entry_ts}"
        trades.append(result)

        exit_ts = int(result.get('exit_ts') or 0)
        if exit_ts <= 0:
            break
        candidate_bars = [
            b for b in day_bars
            if b.get('session', 'regular') != 'regular' or int(b['ts']) > exit_ts
        ]

    return trades

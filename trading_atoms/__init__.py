"""Reusable trading atoms for strategy backtests.

Atoms are small, pure-ish building blocks: session slicing, range detection,
entry selection, stop/target construction, exit resolution, and performance
metrics. Strategies compose atoms; HTTP/API code stays outside this package.
"""

from .cleaning import clamp_bad_wicks, clamp_bars_by_session
from .exits import first_hit_exit
from .performance import mfe_mae, pnl, r_multiple
from .range import detect_breakout, opening_range
from .sessions import ET, MARKET_CLOSE, MARKET_OPEN, PRE_START, annotate_et, serialize_chart_bar, session_name, split_sessions
from .stops import opposite_side_stop, r_multiple_target
from .types import EntryAtom, ExitAtom, MetricsAtom, OpeningRangeAtom, StopAtom, TargetAtom

__all__ = [
    'ET', 'MARKET_OPEN', 'MARKET_CLOSE', 'PRE_START',
    'OpeningRangeAtom', 'EntryAtom', 'StopAtom', 'TargetAtom', 'ExitAtom', 'MetricsAtom',
    'annotate_et', 'split_sessions', 'session_name', 'serialize_chart_bar',
    'clamp_bad_wicks', 'clamp_bars_by_session',
    'opening_range', 'detect_breakout',
    'opposite_side_stop', 'r_multiple_target',
    'first_hit_exit', 'pnl', 'mfe_mae', 'r_multiple',
]

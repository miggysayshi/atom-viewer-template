"""Reusable trading atoms for strategy backtests.

Atoms are small, pure-ish building blocks: session slicing, range detection,
entry selection, stop/target construction, exit resolution, and performance
metrics. Strategies compose atoms; HTTP/API code stays outside this package.
"""

from .cleaning import clamp_bad_wicks, clamp_bars_by_session
from .entries import (
    EmaVwapCrossEntryAtom,
    EngulfingCloseEntryAtom,
    FASHIONABLY_LATE_OPEN_AFTER,
    FairValueGapRetraceEntryAtom,
    ThreeBarPivotReversalEntryAtom,
    find_engulfing_close_entry,
    find_ema_vwap_cross_entry,
    find_fair_value_gap_retrace_entry,
    find_streak_reversal_close_entry,
    find_three_bar_pivot_reversal_entry,
)
from .exits import ema_trailing_stop_exit, first_hit_exit, previous_bar_trailing_exit
from .filters import OverextensionFilterAtom, distance_overextension_filter
from .indicators import atr, average_candle_range, ema, sma, true_range, vwap
from .performance import (
    DEFAULT_RISK_DOLLARS,
    enrich_trade_outcome,
    fixed_risk_position_size,
    mfe_mae,
    normalized_risk_outcome,
    pnl,
    r_multiple,
    summarize_normalized_trades,
)
from .premarket import PremarketRangeAtom, find_premarket_breakout_entry, find_premarket_reentry_entry, premarket_range
from .range import detect_breakout, opening_range
from .reentries import collect_reentry_trades_for_day
from .sessions import ET, MARKET_CLOSE, MARKET_OPEN, PRE_START, annotate_et, serialize_chart_bar, session_name, split_sessions
from .stops import (
    current_extrema_stop,
    ema_trailing_stop_snapshot,
    one_bar_stop,
    opposite_side_stop,
    previous_bar_trailing_stop_snapshot,
    r_multiple_target,
    sma100_1m_target,
    sma200_1m_target,
    sma_period_target,
    vwap_target,
)
from .types import EntryAtom, ExitAtom, MetricsAtom, OpeningRangeAtom, StopAtom, TargetAtom

__all__ = [
    'ET', 'MARKET_OPEN', 'MARKET_CLOSE', 'PRE_START',
    'OpeningRangeAtom', 'PremarketRangeAtom', 'EntryAtom', 'ExitAtom', 'EmaVwapCrossEntryAtom',
    'EngulfingCloseEntryAtom', 'FairValueGapRetraceEntryAtom', 'ThreeBarPivotReversalEntryAtom',
    'MetricsAtom', 'StopAtom', 'TargetAtom', 'OverextensionFilterAtom',
    'FASHIONABLY_LATE_OPEN_AFTER', 'DEFAULT_RISK_DOLLARS',
    'annotate_et', 'split_sessions', 'session_name', 'serialize_chart_bar',
    'clamp_bad_wicks', 'clamp_bars_by_session',
    'ema', 'sma', 'vwap', 'true_range', 'atr', 'average_candle_range', 'distance_overextension_filter',
    'opening_range', 'detect_breakout',
    'premarket_range', 'find_premarket_breakout_entry', 'find_premarket_reentry_entry',
    'collect_reentry_trades_for_day',
    'opposite_side_stop', 'one_bar_stop', 'current_extrema_stop', 'r_multiple_target',
    'previous_bar_trailing_stop_snapshot', 'ema_trailing_stop_snapshot',
    'vwap_target', 'sma_period_target', 'sma100_1m_target', 'sma200_1m_target',
    'find_ema_vwap_cross_entry', 'find_engulfing_close_entry', 'find_fair_value_gap_retrace_entry',
    'find_streak_reversal_close_entry', 'find_three_bar_pivot_reversal_entry',
    'first_hit_exit', 'previous_bar_trailing_exit', 'ema_trailing_stop_exit', 'pnl', 'mfe_mae', 'r_multiple',
    'fixed_risk_position_size', 'normalized_risk_outcome', 'enrich_trade_outcome', 'summarize_normalized_trades',
]

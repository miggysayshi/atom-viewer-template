from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable

from ..cleaning import clamp_bars_by_session
from ..entries import (
    aggregate_clock,
    find_engulfing_close_entry,
    find_fair_value_gap_retrace_entry,
    normalize_timeframe,
    timeframe_seconds,
)
from ..exits import stop_or_market_close_exit
from ..performance import metrics as compute_metrics
from ..sessions import ET, annotate_et, serialize_chart_bar, split_sessions
from ..stops import current_extrema_stop, one_bar_stop
from ..types import StopAtom
from .risk import lower_timeframe_one_bar_stop, one_bar_stop_labels


@dataclass(frozen=True)
class StrategySpec:
    strategy_name: str
    tested_atom: str
    entry_finder: Callable


def _display_time(ts: int) -> str:
    return dt.datetime.fromtimestamp(ts, tz=ET).strftime('%H:%M')


def _stop_from_entry(
    entry,
    strategy_bars: list[dict],
    rth_bars_all: list[dict],
    stop_mode: str,
    timeframe: str,
    risk_timeframe: str,
) -> tuple[StopAtom | None, str, str, dict | None]:
    if stop_mode == 'one_bar':
        stop, basis_bar, risk_timeframe = lower_timeframe_one_bar_stop(
            entry_price=entry.price,
            entry_ts=entry.ts,
            entry_direction=entry.direction,
            rth_bars_all=rth_bars_all,
            strategy_timeframe=timeframe,
            risk_timeframe=risk_timeframe,
            fallback_entry_bar=entry.bar,
        )
        title, rule = one_bar_stop_labels(entry.direction, timeframe, risk_timeframe, basis_bar)
        return stop, rule, title, basis_bar

    if stop_mode == 'fvg_suggested' and hasattr(entry, 'suggested_stop_price'):
        risk = abs(float(entry.price) - float(entry.suggested_stop_price))
        if risk <= 0:
            return None, '', '', None
        rule = entry.suggested_stop_rule()
        title = 'FVG Candle Low Stop' if entry.direction == 'long' else 'FVG Candle High Stop'
        return StopAtom(
            price=float(entry.suggested_stop_price),
            risk=risk,
            rule=rule,
            rule_ref=float(entry.suggested_stop_price),
        ), rule, title, None

    stop_mode = 'current_extrema'
    stop = current_extrema_stop(
        entry.price,
        strategy_bars,
        known_through_ts=entry.ts,
        direction=entry.direction,
    )
    rule = 'current_lod_at_entry_for_long' if entry.direction == 'long' else 'current_hod_at_entry_for_short'
    title = 'Current LOD Stop' if entry.direction == 'long' else 'Current HOD Stop'
    return stop, rule, title, None


def _reason_for_entry(entry, strategy_name: str, entry_time: str) -> str:
    action = 'Long' if entry.direction == 'long' else 'Short'
    if strategy_name == 'engulfing':
        if entry.direction == 'short':
            return (
                f"{action} engulfing close below previous low {entry.previous_low:.2f} at {entry_time} "
                f"({entry.previous_color} → {entry.trigger_color})"
            )
        return (
            f"{action} engulfing close above previous high {entry.previous_high:.2f} at {entry_time} "
            f"({entry.previous_color} → {entry.trigger_color})"
        )
    if entry.direction == 'short':
        return (
            f"{action} bearish fair value gap 50% retrace at {entry_time}; "
            f"gap {entry.gap_start:.2f}–{entry.gap_end:.2f}, midpoint {entry.gap_midpoint:.2f}"
        )
    return (
        f"{action} bullish fair value gap 50% retrace at {entry_time}; "
        f"gap {entry.gap_start:.2f}–{entry.gap_end:.2f}, midpoint {entry.gap_midpoint:.2f}"
    )


def _compose_entry_visual_check(
    day_bars: list[dict],
    *,
    spec: StrategySpec,
    timeframe: str = '15m',
    direction_mode: str = 'both',
    stop_mode: str = 'current_extrema',
    risk_timeframe: str | None = None,
) -> dict | None:
    if not day_bars:
        return None

    annotated = annotate_et(day_bars)
    premarket, rth_bars_all, post_bars = split_sessions(annotated)
    if not rth_bars_all:
        return None

    cleaned = clamp_bars_by_session(premarket, rth_bars_all, post_bars)
    if cleaned['rth'] or cleaned['pre'] or cleaned['post']:
        day_key_log = annotated[0]['et'].strftime('%Y-%m-%d')
        print(
            f"  [{day_key_log}] cleaned {cleaned['rth']} RTH + "
            f"{cleaned['pre']} premarket + {cleaned['post']} post bars"
        )

    timeframe = normalize_timeframe(timeframe, default='15m')
    risk_timeframe = normalize_timeframe(risk_timeframe or timeframe, default=timeframe)
    strategy_bars = aggregate_clock(rth_bars_all, timeframe)
    entry = spec.entry_finder(
        rth_bars_all,
        timeframe=timeframe,
        direction_mode=direction_mode,
    )
    if entry is None:
        return None

    stop, stop_rule, stop_title, stop_basis_bar = _stop_from_entry(entry, strategy_bars, rth_bars_all, stop_mode, timeframe, risk_timeframe)
    if stop is None:
        return None

    exit_atom = stop_or_market_close_exit(
        strategy_bars,
        entry_ts=entry.ts,
        direction=entry.direction,
        stop=stop,
    )
    if exit_atom is None:
        return None

    known_at_entry_bars = [b for b in strategy_bars if int(b['ts']) < entry.ts]
    post_entry = [b for b in strategy_bars if b['ts'] >= entry.ts and b['ts'] <= exit_atom.ts]
    trade_metrics = compute_metrics(entry.price, exit_atom.price, entry.direction, stop.risk, post_entry)

    date_label = annotated[0]['et'].strftime('%Y-%m-%d')
    day_label = annotated[0]['et'].strftime('%a %b %d, %Y')
    all_bars = [serialize_chart_bar(b) for b in annotated]
    entry_time = _display_time(entry.ts)
    stop_color = 'rgba(34,197,94,0.65)' if entry.direction == 'long' else 'rgba(239,68,68,0.65)'

    debug_high = getattr(entry, 'gap_end', getattr(entry, 'previous_high', max(b['high'] for b in strategy_bars)))
    debug_low = getattr(entry, 'gap_start', getattr(entry, 'previous_low', min(b['low'] for b in strategy_bars)))

    result = {
        'day': day_label,
        'date': date_label,
        'or_high': round(max(debug_high, debug_low), 4),
        'or_low': round(min(debug_high, debug_low), 4),
        'or_minutes': timeframe_seconds(timeframe) // 60,
        'entry': round(entry.price, 4),
        'exit': round(exit_atom.price, 4),
        'direction': entry.direction,
        'entry_time': entry_time,
        'entry_ts': entry.ts,
        'entry_bar_ts': entry.bar_ts,
        'entry_anchor': entry.anchor,
        'exit_time': exit_atom.bar['et'].strftime('%H:%M'),
        'exit_ts': exit_atom.ts,
        'stop_price': round(stop.price, 4),
        'target_price': None,
        'exit_reason': exit_atom.reason,
        'pnl_pct': trade_metrics.pnl_pct,
        'pnl': trade_metrics.pnl,
        'mfe': trade_metrics.mfe,
        'mae': trade_metrics.mae,
        'bars': all_bars,
        'reason_for_entry': _reason_for_entry(entry, spec.strategy_name, entry_time),
        'reason_for_exit': 'Stop hit' if exit_atom.reason == 'stop' else 'Market close exit',
        'price_lines': [
            {'price': round(stop.price, 4), 'title': stop_title, 'color': stop_color},
        ],
    }
    if spec.strategy_name == 'fvg_retrace':
        result['price_lines'].append({
            'price': round(entry.gap_midpoint, 4),
            'title': 'FVG 50% Retrace',
            'color': 'rgba(59,130,246,0.7)',
        })

    result['atoms'] = {
        'schema_version': 1,
        'strategy': f'{spec.strategy_name}_visual_check',
        'tested_atom': spec.tested_atom,
        'params': {
            'timeframe': timeframe,
            'direction_mode': direction_mode,
            'stop_mode': stop_mode,
            'entry_anchor': entry.anchor,
        },
        'defaults': {
            'risk_dollars': 100,
            'exit_rule': 'stop_first_else_market_close',
            'trading_window': 'rth_only',
        },
        'entry': entry.to_payload() | {'time': entry_time},
        'stop': {
            'price': round(stop.price, 4),
            'risk_per_share': round(stop.risk, 4),
            'rule': stop_rule,
            'known_through_ts': entry.ts,
            'known_bar_count': len(known_at_entry_bars),
        },
        'target': None,
        'exit': {
            'ts': exit_atom.ts,
            'time': exit_atom.bar['et'].strftime('%H:%M'),
            'price': round(exit_atom.price, 4),
            'side': 'sell' if entry.direction == 'long' else 'buy',
            'rule': 'stop_hit' if exit_atom.reason == 'stop' else 'market_close',
        },
        'risk': {
            'per_share': round(stop.risk, 4),
            'fixed_dollars': 100,
        },
        'metrics': trade_metrics.to_payload(),
    }
    return result


def run_engulfing_for_day(
    day_bars: list[dict],
    timeframe: str = '15m',
    direction_mode: str = 'both',
    stop_mode: str = 'current_extrema',
    risk_timeframe: str | None = None,
) -> dict | None:
    return _compose_entry_visual_check(
        day_bars,
        spec=StrategySpec('engulfing', 'engulfing_close_entry_v1', find_engulfing_close_entry),
        timeframe=timeframe,
        direction_mode=direction_mode,
        stop_mode=stop_mode,
    )


def run_fvg_retrace_for_day(
    day_bars: list[dict],
    timeframe: str = '15m',
    direction_mode: str = 'both',
    stop_mode: str = 'fvg_suggested',
    risk_timeframe: str | None = None,
) -> dict | None:
    if stop_mode == 'current_extrema':
        # Miguel's requested FVG model uses the FVG candle high/low as stop.
        stop_mode = 'fvg_suggested'
    return _compose_entry_visual_check(
        day_bars,
        spec=StrategySpec('fvg_retrace', 'fair_value_gap_retrace_entry_v1', find_fair_value_gap_retrace_entry),
        timeframe=timeframe,
        direction_mode=direction_mode,
        stop_mode=stop_mode,
    )

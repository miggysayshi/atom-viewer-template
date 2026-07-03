from __future__ import annotations

import datetime as dt

from ..cleaning import clamp_bars_by_session
from ..entries import aggregate_clock, normalize_timeframe, timeframe_seconds
from ..exits import stop_or_market_close_exit
from ..performance import metrics as compute_metrics
from ..premarket import PremarketRangeAtom, find_premarket_breakout_entry, find_premarket_reentry_entry, premarket_range
from ..sessions import ET, annotate_et, serialize_chart_bar, split_sessions
from ..stops import current_extrema_stop, one_bar_stop
from ..types import EntryAtom
from .risk import lower_timeframe_one_bar_stop, one_bar_stop_labels


def _bar_seconds(rth_bars: list[dict], fallback: int = 300) -> int:
    for prev, cur in zip(rth_bars, rth_bars[1:]):
        delta = int(cur['ts']) - int(prev['ts'])
        if 0 < delta <= 24 * 60 * 60:
            return delta
    return fallback


def _entry_close_ts(entry: EntryAtom, rth_bars: list[dict]) -> int:
    return int(entry.bar['ts']) + _bar_seconds(rth_bars)


def _entry_payload(entry: EntryAtom, *, entry_ts: int, entry_display_time: str, anchor: str = 'bar_close') -> dict:
    return {
        'ts': entry_ts,
        'bar_ts': int(entry.bar['ts']),
        'time': entry_display_time,
        'price': round(entry.price, 4),
        'direction': entry.direction,
        'side': 'buy' if entry.direction == 'long' else 'sell',
        'rule': entry.rule,
        'rule_ref': round(entry.rule_ref, 4),
        'anchor': anchor,
    }


def _compose_premarket_visual_check(
    day_bars: list[dict],
    *,
    strategy_name: str,
    tested_atom: str,
    entry_finder,
    direction_mode: str = 'both',
    stop_mode: str = 'current_extrema',
    timeframe: str = '5m',
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

    pm_range = premarket_range(annotated)
    if pm_range is None:
        return None

    timeframe = normalize_timeframe(timeframe, default='5m')
    risk_timeframe = normalize_timeframe(risk_timeframe or timeframe, default=timeframe)
    strategy_rth_bars = aggregate_clock(rth_bars_all, timeframe)
    strategy_annotated = premarket + strategy_rth_bars + post_bars

    entry = entry_finder(pm_range, strategy_annotated, direction_mode=direction_mode)
    if entry is None:
        return None

    entry_ts = _entry_close_ts(entry, strategy_rth_bars)
    entry_close_dt = dt.datetime.fromtimestamp(entry_ts, tz=ET)
    entry_display_time = entry_close_dt.strftime('%H:%M')

    stop_basis_bar = None
    if stop_mode == 'one_bar':
        stop, stop_basis_bar, risk_timeframe = lower_timeframe_one_bar_stop(
            entry_price=entry.price,
            entry_ts=entry_ts,
            entry_direction=entry.direction,
            rth_bars_all=rth_bars_all,
            strategy_timeframe=timeframe,
            risk_timeframe=risk_timeframe,
            fallback_entry_bar=entry.bar,
        )
    else:
        stop_mode = 'current_extrema'
        stop = current_extrema_stop(
            entry.price,
            strategy_rth_bars,
            known_through_ts=entry_ts,
            direction=entry.direction,
        )
    if stop is None:
        return None

    exit_atom = stop_or_market_close_exit(
        strategy_rth_bars,
        entry_ts=entry_ts,
        direction=entry.direction,
        stop=stop,
    )
    if exit_atom is None:
        return None

    known_at_entry_bars = [b for b in strategy_rth_bars if int(b['ts']) < entry_ts]
    post_entry = [b for b in strategy_rth_bars if b['ts'] >= entry_ts and b['ts'] <= exit_atom.ts]
    trade_metrics = compute_metrics(entry.price, exit_atom.price, entry.direction, stop.risk, post_entry)

    day_label = annotated[0]['et'].strftime('%a %b %d, %Y')
    date_label = annotated[0]['et'].strftime('%Y-%m-%d')
    all_bars = [serialize_chart_bar(b) for b in annotated]
    action = 'Long' if entry.direction == 'long' else 'Short'
    if stop_mode == 'one_bar':
        stop_title, stop_rule = one_bar_stop_labels(entry.direction, timeframe, risk_timeframe, stop_basis_bar)
    else:
        stop_title = 'Current LOD Stop' if entry.direction == 'long' else 'Current HOD Stop'
        stop_rule = 'current_lod_at_entry_for_long' if entry.direction == 'long' else 'current_hod_at_entry_for_short'
    stop_color = 'rgba(34,197,94,0.65)' if entry.direction == 'long' else 'rgba(239,68,68,0.65)'
    reason_for_entry = _reason_for_entry(action, entry, pm_range, entry_display_time)

    result = {
        'day': day_label,
        'date': date_label,
        'or_high': pm_range.high,
        'or_low': pm_range.low,
        'or_minutes': 0,
        'entry': round(entry.price, 4),
        'exit': round(exit_atom.price, 4),
        'direction': entry.direction,
        'entry_time': entry_display_time,
        'entry_ts': entry_ts,
        'entry_bar_ts': int(entry.bar['ts']),
        'entry_anchor': 'bar_close',
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
        'reason_for_entry': reason_for_entry,
        'reason_for_exit': 'Stop hit' if exit_atom.reason == 'stop' else 'Market close exit',
        'price_lines': [
            {'price': pm_range.high, 'title': 'PM High', 'color': 'rgba(59,130,246,0.55)'},
            {'price': pm_range.low, 'title': 'PM Low', 'color': 'rgba(234,179,8,0.55)'},
            {'price': round(stop.price, 4), 'title': stop_title, 'color': stop_color},
        ],
    }
    result['atoms'] = {
        'schema_version': 1,
        'strategy': strategy_name,
        'tested_atom': tested_atom,
        'params': {
            'direction_mode': direction_mode,
            'stop_mode': stop_mode,
            'timeframe': timeframe,
            'risk_timeframe': risk_timeframe,
            'timeframe_seconds': timeframe_seconds(timeframe),
            'entry_price_rule': 'trigger_candle_close',
            'entry_anchor': 'bar_close',
        },
        'premarket_range': pm_range.to_payload(),
        'entry': _entry_payload(entry, entry_ts=entry_ts, entry_display_time=entry_display_time),
        'stop': {
            'price': round(stop.price, 4),
            'risk_per_share': round(stop.risk, 4),
            'rule': stop_rule,
            'risk_timeframe': risk_timeframe if stop_mode == 'one_bar' else None,
            'basis_bar_ts': int(stop_basis_bar['ts']) if stop_basis_bar is not None else None,
            'basis_bar_time': stop_basis_bar['et'].strftime('%H:%M') if stop_basis_bar is not None and stop_basis_bar.get('et') else None,
            'known_through_ts': entry_ts,
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


def _reason_for_entry(action: str, entry: EntryAtom, pm_range: PremarketRangeAtom, entry_time: str) -> str:
    if entry.rule == 'premarket_high_breakout_close':
        return f"{action} close above premarket high {pm_range.high:.2f} at {entry_time}"
    if entry.rule == 'premarket_low_breakdown_close':
        return f"{action} close below premarket low {pm_range.low:.2f} at {entry_time}"
    if entry.rule == 'pmh_failed_breakout_reentry':
        return f"{action} after PMH break; close back inside PM range at {entry_time}"
    if entry.rule == 'pml_failed_breakdown_reentry':
        return f"{action} after PML break; close back inside PM range at {entry_time}"
    return f"{action} {entry.rule} at {entry_time}"


def run_premarket_breakout_for_day(
    day_bars: list[dict],
    direction_mode: str = 'both',
    stop_mode: str = 'current_extrema',
    timeframe: str = '5m',
    risk_timeframe: str | None = None,
) -> dict | None:
    return _compose_premarket_visual_check(
        day_bars,
        strategy_name='premarket_breakout',
        tested_atom='premarket_breakout_entry_v1',
        entry_finder=find_premarket_breakout_entry,
        direction_mode=direction_mode,
        stop_mode=stop_mode,
        timeframe=timeframe,
        risk_timeframe=risk_timeframe,
    )


def run_premarket_reentry_for_day(
    day_bars: list[dict],
    direction_mode: str = 'both',
    stop_mode: str = 'current_extrema',
    timeframe: str = '5m',
    risk_timeframe: str | None = None,
) -> dict | None:
    return _compose_premarket_visual_check(
        day_bars,
        strategy_name='premarket_reentry',
        tested_atom='premarket_reentry_entry_v1',
        entry_finder=find_premarket_reentry_entry,
        direction_mode=direction_mode,
        stop_mode=stop_mode,
        timeframe=timeframe,
        risk_timeframe=risk_timeframe,
    )

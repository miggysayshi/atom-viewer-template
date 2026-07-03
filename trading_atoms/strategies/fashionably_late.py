from __future__ import annotations

import datetime as dt

from ..cleaning import clamp_bars_by_session
from ..entries import find_ema_vwap_cross_entry, normalize_timeframe, timeframe_seconds
from ..exits import first_hit_exit, stop_or_market_close_exit
from ..performance import metrics as compute_metrics
from ..sessions import ET, annotate_et, serialize_chart_bar, split_sessions
from ..stops import current_extrema_stop, one_bar_stop, r_multiple_target
from .risk import lower_timeframe_one_bar_stop, one_bar_stop_labels


def run_fashionably_late_for_day(
    day_bars: list[dict],
    *,
    timeframe: str = '1m',
    direction_mode: str = 'both',
    stop_mode: str = 'one_bar',
    target_multiple: float | None = 3.0,
    risk_timeframe: str | None = None,
) -> dict | None:
    """Compose Fashionably Late v2: EMA/VWAP cross + stop variant + optional 3R target."""
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

    timeframe = normalize_timeframe(timeframe, default='1m')
    risk_timeframe = normalize_timeframe(risk_timeframe or timeframe, default=timeframe)

    entry = find_ema_vwap_cross_entry(
        rth_bars_all,
        timeframe=timeframe,
        direction_mode=direction_mode,
    )
    if entry is None:
        return None

    stop_basis_bar = None
    if stop_mode == 'current_extrema':
        stop = current_extrema_stop(
            entry.price,
            rth_bars_all,
            known_through_ts=entry.ts,
            direction=entry.direction,
        )
    else:
        stop_mode = 'one_bar'
        stop, stop_basis_bar, risk_timeframe = lower_timeframe_one_bar_stop(
            entry_price=entry.price,
            entry_ts=entry.ts,
            entry_direction=entry.direction,
            rth_bars_all=rth_bars_all,
            strategy_timeframe=timeframe,
            risk_timeframe=risk_timeframe,
            fallback_entry_bar=entry.bar,
        )
    if stop is None:
        return None

    target = r_multiple_target(entry.price, stop, entry.direction, multiple=target_multiple) if target_multiple else None
    if target is not None:
        exit_atom = first_hit_exit(
            rth_bars_all,
            entry_ts=entry.ts,
            direction=entry.direction,
            stop=stop,
            target=target,
        )
    else:
        exit_atom = stop_or_market_close_exit(
            rth_bars_all,
            entry_ts=entry.ts,
            direction=entry.direction,
            stop=stop,
        )
    if exit_atom is None:
        return None

    entry_close_dt = dt.datetime.fromtimestamp(entry.ts, tz=ET)
    entry_display_time = entry_close_dt.strftime('%H:%M')
    post_entry = [b for b in rth_bars_all if b['ts'] >= entry.ts and b['ts'] <= exit_atom.ts]
    trade_metrics = compute_metrics(entry.price, exit_atom.price, entry.direction, stop.risk, post_entry)

    day_label = annotated[0]['et'].strftime('%a %b %d, %Y')
    date_label = annotated[0]['et'].strftime('%Y-%m-%d')
    all_bars = [serialize_chart_bar(b) for b in annotated]
    action = 'Long' if entry.direction == 'long' else 'Short'
    if stop_mode == 'current_extrema':
        stop_title = 'Current LOD Stop' if entry.direction == 'long' else 'Current HOD Stop'
        stop_rule = 'current_lod_at_entry_for_long' if entry.direction == 'long' else 'current_hod_at_entry_for_short'
    else:
        stop_title, stop_rule = one_bar_stop_labels(entry.direction, timeframe, risk_timeframe, stop_basis_bar)
    target_title = f'{target.multiple:g}R Target' if target is not None else None
    stop_color = 'rgba(34,197,94,0.65)' if entry.direction == 'long' else 'rgba(239,68,68,0.65)'
    target_color = 'rgba(168,85,247,0.65)'

    result = {
        'day': day_label,
        'date': date_label,
        'or_high': entry.vwap_at_entry,
        'or_low': entry.ema_at_entry,
        'or_minutes': timeframe_seconds(timeframe) // 60,
        'entry': round(entry.price, 4),
        'exit': round(exit_atom.price, 4),
        'direction': entry.direction,
        'entry_time': entry_display_time,
        'entry_ts': entry.ts,
        'entry_bar_ts': entry.bar_ts,
        'entry_anchor': entry.anchor,
        'exit_time': exit_atom.bar['et'].strftime('%H:%M'),
        'exit_ts': exit_atom.ts,
        'stop_price': round(stop.price, 4),
        'target_price': round(target.price, 4) if target is not None else None,
        'exit_reason': exit_atom.reason,
        'pnl_pct': trade_metrics.pnl_pct,
        'pnl': trade_metrics.pnl,
        'mfe': trade_metrics.mfe,
        'mae': trade_metrics.mae,
        'bars': all_bars,
        'reason_for_entry': (
            f"{action} EMA9/VWAP cross after first 15 min at {entry_display_time} "
            f"(EMA {entry.ema_at_entry:.2f}, VWAP {entry.vwap_at_entry:.2f})"
        ),
        'reason_for_exit': (
            'Target hit' if exit_atom.reason == 'target'
            else ('Stop hit' if exit_atom.reason == 'stop' else 'Market close exit')
        ),
        'price_lines': [
            {'price': round(stop.price, 4), 'title': stop_title, 'color': stop_color},
            *([{'price': round(target.price, 4), 'title': target_title, 'color': target_color}] if target is not None else []),
            {'price': round(entry.vwap_at_entry, 4), 'title': 'VWAP at Entry', 'color': 'rgba(59,130,246,0.55)'},
            {'price': round(entry.ema_at_entry, 4), 'title': 'EMA9 at Entry', 'color': 'rgba(234,179,8,0.55)'},
        ],
    }
    result['atoms'] = {
        'schema_version': 1,
        'strategy': 'fashionably_late',
        'tested_atom': 'ema_vwap_cross_entry_v2',
        'params': {
            'timeframe': timeframe,
            'risk_timeframe': risk_timeframe,
            'direction_mode': direction_mode,
            'stop_mode': stop_mode,
            'target_multiple': target_multiple,
            'ema_period': entry.ema_period,
            'eligible_after': entry.eligible_after.strftime('%H:%M'),
            'entry_price_rule': 'trigger_candle_close',
            'entry_anchor': entry.anchor,
        },
        'entry': entry.to_payload() | {'time': entry_display_time},
        'stop': {
            'price': round(stop.price, 4),
            'risk_per_share': round(stop.risk, 4),
            'rule': stop_rule,
            'risk_timeframe': risk_timeframe if stop_mode == 'one_bar' else None,
            'basis_bar_ts': int(stop_basis_bar['ts']) if stop_basis_bar is not None else None,
            'basis_bar_time': stop_basis_bar['et'].strftime('%H:%M') if stop_basis_bar is not None and stop_basis_bar.get('et') else None,
            'known_through_ts': entry.ts,
            'known_bar_count': len([b for b in rth_bars_all if int(b['ts']) < entry.ts]),
        },
        'target': target.to_payload() if target is not None else None,
        'exit': {
            'ts': exit_atom.ts,
            'time': exit_atom.bar['et'].strftime('%H:%M'),
            'price': round(exit_atom.price, 4),
            'side': 'sell' if entry.direction == 'long' else 'buy',
            'rule': exit_atom.reason,
        },
        'risk': {
            'per_share': round(stop.risk, 4),
            'fixed_dollars': 100,
        },
        'metrics': trade_metrics.to_payload(),
    }
    return result

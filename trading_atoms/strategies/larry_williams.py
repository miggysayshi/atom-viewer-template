from __future__ import annotations

import datetime as dt

from ..cleaning import clamp_bars_by_session
from ..entries import aggregate_clock, find_three_bar_pivot_reversal_entry, normalize_timeframe, timeframe_seconds
from ..exits import stop_or_market_close_exit
from ..performance import metrics as compute_metrics
from ..sessions import ET, annotate_et, serialize_chart_bar, split_sessions
from ..stops import current_extrema_stop, one_bar_stop


def run_larry_williams_3bar_for_day(
    day_bars: list[dict],
    timeframe: str = '15m',
    direction_mode: str = 'both',
    stop_mode: str = 'current_extrema',
    risk_timeframe: str | None = None,
) -> dict | None:
    """Compose HTF 3-bar pivot reversal entry + selected LTF stop + stop/MOC exit."""
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

    entry = find_three_bar_pivot_reversal_entry(
        rth_bars_all,
        timeframe=timeframe,
        direction_mode=direction_mode,
    )
    if entry is None:
        return None

    stop_basis_bar = None
    if stop_mode == 'one_bar':
        risk_bars = aggregate_clock(rth_bars_all, risk_timeframe)
        prior_risk_bars = [b for b in risk_bars if int(b['ts']) < entry.ts]
        if not prior_risk_bars:
            return None
        # No-lookahead LTF risk: use the last completed risk-timeframe bar before
        # the HTF entry. When risk_timeframe == timeframe this matches the old
        # Larry Williams signal-candle stop.
        stop_basis_bar = prior_risk_bars[-1]
        stop = one_bar_stop(entry.price, stop_basis_bar, entry.direction)
    else:
        stop_mode = 'current_extrema'
        stop = current_extrema_stop(
            entry.price,
            rth_bars_all,
            known_through_ts=entry.ts,
            direction=entry.direction,
        )
    if stop is None:
        return None

    exit_atom = stop_or_market_close_exit(
        rth_bars_all,
        entry_ts=entry.ts,
        direction=entry.direction,
        stop=stop,
    )
    if exit_atom is None:
        return None

    known_at_entry_bars = [b for b in rth_bars_all if int(b['ts']) < entry.ts]
    entry_close_dt = dt.datetime.fromtimestamp(entry.ts, tz=ET)
    entry_display_time = entry_close_dt.strftime('%H:%M')
    post_entry = [b for b in rth_bars_all if b['ts'] >= entry.ts and b['ts'] <= exit_atom.ts]
    trade_metrics = compute_metrics(entry.price, exit_atom.price, entry.direction, stop.risk, post_entry)

    date_label = annotated[0]['et'].strftime('%Y-%m-%d')
    day_label = annotated[0]['et'].strftime('%a %b %d, %Y')
    all_bars = [serialize_chart_bar(b) for b in annotated]
    pattern_times = entry.pattern_times()
    pattern_high = max(b['high'] for b in entry.pattern_bars)
    pattern_low = min(b['low'] for b in entry.pattern_bars)
    action = 'Long' if entry.direction == 'long' else 'Short'
    if stop_mode == 'one_bar':
        assert stop_basis_bar is not None
        lower_tf_stop = risk_timeframe != timeframe
        if lower_tf_stop:
            stop_title = f"{risk_timeframe} Signal Candle Low Stop" if entry.direction == 'long' else f"{risk_timeframe} Signal Candle High Stop"
            stop_rule = 'lower_tf_signal_candle_low_for_next_open_long' if entry.direction == 'long' else 'lower_tf_signal_candle_high_for_next_open_short'
        elif entry.anchor == 'bar_open':
            stop_title = 'Signal Candle Low Stop' if entry.direction == 'long' else 'Signal Candle High Stop'
            stop_rule = 'signal_candle_low_for_next_open_long' if entry.direction == 'long' else 'signal_candle_high_for_next_open_short'
        else:
            stop_title = '1-Bar Low Stop' if entry.direction == 'long' else '1-Bar High Stop'
            stop_rule = 'entry_candle_low_for_long' if entry.direction == 'long' else 'entry_candle_high_for_short'
    else:
        stop_title = 'Current LOD Stop' if entry.direction == 'long' else 'Current HOD Stop'
        stop_rule = 'current_lod_at_entry_for_long' if entry.direction == 'long' else 'current_hod_at_entry_for_short'
    stop_color = 'rgba(34,197,94,0.65)' if entry.direction == 'long' else 'rgba(239,68,68,0.65)'
    exit_reason = exit_atom.reason
    pattern_label = (
        'high → higher high → lower high'
        if entry.direction == 'short'
        else 'low → lower low → higher low'
    )

    risk_clause = (
        f"; risk managed on last completed {risk_timeframe} candle"
        if stop_mode == 'one_bar' and risk_timeframe != timeframe
        else ''
    )
    result = {
        'day': day_label,
        'date': date_label,
        'or_high': pattern_high,
        'or_low': pattern_low,
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
        'target_price': None,
        'exit_reason': exit_reason,
        'pnl_pct': trade_metrics.pnl_pct,
        'pnl': trade_metrics.pnl,
        'mfe': trade_metrics.mfe,
        'mae': trade_metrics.mae,
        'bars': all_bars,
        'reason_for_entry': (
            f"{action} Larry Williams 3-bar pivot reversal ({pattern_label}) "
            f"confirmed after 3 completed {timeframe} candles; entry on next candle open at {entry_display_time} "
            f"({', '.join(pattern_times)}){risk_clause}"
        ),
        'reason_for_exit': 'Stop hit' if exit_reason == 'stop' else 'Market close exit',
        'price_lines': [
            {'price': round(stop.price, 4), 'title': stop_title, 'color': stop_color},
        ],
    }
    result['atoms'] = {
        'schema_version': 1,
        'strategy': 'larry_williams_3bar_visual_check',
        'tested_atom': 'three_bar_pivot_reversal_entry_v1',
        'params': {
            'timeframe': entry.timeframe,
            'risk_timeframe': risk_timeframe,
            'direction_mode': direction_mode,
            'stop_mode': stop_mode,
            'entry_price_rule': 'next_candle_open_after_3bar_pattern',
            'entry_anchor': entry.anchor,
        },
        'defaults': {
            'risk_dollars': 100,
            'exit_rule': 'stop_first_else_market_close',
            'short_stop': 'current_hod_at_entry',
            'long_stop': 'current_lod_at_entry',
            'trading_window': 'rth_only',
        },
        'entry': entry.to_payload() | {'time': entry_display_time},
        'stop': {
            'price': round(stop.price, 4),
            'risk_per_share': round(stop.risk, 4),
            'rule': stop_rule,
            'risk_timeframe': risk_timeframe if stop_mode == 'one_bar' else None,
            'basis_bar_ts': int(stop_basis_bar['ts']) if stop_basis_bar is not None else None,
            'basis_bar_time': stop_basis_bar['et'].strftime('%H:%M') if stop_basis_bar is not None else None,
            'known_through_ts': entry.ts,
            'known_bar_count': len(known_at_entry_bars),
        },
        'target': None,
        'exit': {
            'ts': exit_atom.ts,
            'time': exit_atom.bar['et'].strftime('%H:%M'),
            'price': round(exit_atom.price, 4),
            'side': 'sell' if entry.direction == 'long' else 'buy',
            'rule': 'stop_hit' if exit_reason == 'stop' else 'market_close',
        },
        'risk': {
            'per_share': round(stop.risk, 4),
            'fixed_dollars': 100,
        },
        'metrics': trade_metrics.to_payload(),
    }
    return result

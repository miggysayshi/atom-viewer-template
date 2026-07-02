from __future__ import annotations

from ..cleaning import clamp_bars_by_session
from ..exits import first_hit_exit
from ..performance import metrics as compute_metrics
from ..range import detect_breakout, opening_range
from ..sessions import annotate_et, serialize_chart_bar, split_sessions
from ..stops import opposite_side_stop, r_multiple_target


def run_orb_for_day(day_bars: list[dict], or_minutes: int, target_multiple: float = 3.0) -> dict | None:
    """Run Opening Range Breakout on one ET day.

    Returns the legacy /api/orb trade dict shape, plus additive `atoms` metadata.
    """
    if not day_bars:
        return None

    annotated = annotate_et(day_bars)
    premarket, rth_bars_all, post_bars = split_sessions(annotated)

    cleaned = clamp_bars_by_session(premarket, rth_bars_all, post_bars)
    if cleaned['rth'] or cleaned['pre'] or cleaned['post']:
        day_key_log = annotated[0]['et'].strftime('%Y-%m-%d')
        print(
            f"  [{day_key_log}] cleaned {cleaned['rth']} RTH + "
            f"{cleaned['pre']} premarket + {cleaned['post']} post bars"
        )

    or_range = opening_range(annotated, or_minutes)
    if or_range is None:
        return None

    entry = detect_breakout(or_range)
    if entry is None:
        return None

    stop = opposite_side_stop(entry.price, or_range, entry.direction)
    target = r_multiple_target(entry.price, stop, entry.direction, multiple=target_multiple)
    exit_atom = first_hit_exit(
        or_range.rth_bars,
        entry_ts=entry.ts,
        direction=entry.direction,
        stop=stop,
        target=target,
    )
    if exit_atom is None:
        return None

    rth_after_entry = [b for b in or_range.rth_bars if b['ts'] >= entry.ts]
    post_entry = [b for b in rth_after_entry if b['ts'] <= exit_atom.ts]
    trade_metrics = compute_metrics(
        entry.price,
        exit_atom.price,
        entry.direction,
        stop.risk,
        post_entry,
    )

    day_key = annotated[0]['et'].strftime('%a %b %d, %Y')
    all_bars = [serialize_chart_bar(b) for b in annotated]

    result = {
        'day': day_key,
        'date': annotated[0]['et'].strftime('%Y-%m-%d'),
        'or_high': or_range.high,
        'or_low': or_range.low,
        'or_minutes': or_minutes,
        'entry': round(entry.price, 4),
        'exit': round(exit_atom.price, 4),
        'direction': entry.direction,
        'entry_time': entry.bar['et'].strftime('%H:%M'),
        'entry_ts': entry.ts,
        'exit_time': exit_atom.bar['et'].strftime('%H:%M'),
        'exit_ts': exit_atom.ts,
        'stop_price': round(stop.price, 4),
        'target_price': round(target.price, 4),
        'exit_reason': exit_atom.reason,
        'pnl_pct': trade_metrics.pnl_pct,
        'pnl': trade_metrics.pnl,
        'mfe': trade_metrics.mfe,
        'mae': trade_metrics.mae,
        'bars': all_bars,
    }
    result['atoms'] = {
        'schema_version': 1,
        'strategy': 'orb',
        'params': {
            'or_minutes': or_minutes,
            'target_multiple': target_multiple,
            'same_bar_priority': 'stop',
        },
        'opening_range': or_range.to_payload(),
        'entry': entry.to_payload(),
        'stop': stop.to_payload(ts=entry.ts),
        'target': target.to_payload(),
        'exit': exit_atom.to_payload(entry.direction),
        'risk': {
            'per_share': round(stop.risk, 4),
            'multiple': target_multiple,
        },
        'metrics': trade_metrics.to_payload(),
    }
    return result

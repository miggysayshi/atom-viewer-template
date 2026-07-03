from __future__ import annotations

from math import floor

from .types import Direction, MetricsAtom

DEFAULT_RISK_DOLLARS = 100


def pnl(entry: float, exit_price: float, direction: Direction) -> tuple[float, float]:
    if direction == 'long':
        pnl_pct = round((exit_price - entry) / entry * 100, 2)
        pnl_dollars = round(exit_price - entry, 2)
    else:
        pnl_pct = round((entry - exit_price) / entry * 100, 2)
        pnl_dollars = round(entry - exit_price, 2)
    return pnl_dollars, pnl_pct


def mfe_mae(post_entry_bars: list[dict], entry: float, direction: Direction) -> tuple[float, float]:
    if direction == 'long':
        mfe = round(max(b['high'] for b in post_entry_bars) - entry, 2) if post_entry_bars else 0
        mae = round(entry - min(b['low'] for b in post_entry_bars), 2) if post_entry_bars else 0
    else:
        mfe = round(entry - min(b['low'] for b in post_entry_bars), 2) if post_entry_bars else 0
        mae = round(max(b['high'] for b in post_entry_bars) - entry, 2) if post_entry_bars else 0
    return mfe, mae


def r_multiple(pnl_dollars: float, risk_per_share: float) -> float:
    return round(pnl_dollars / risk_per_share, 2) if risk_per_share else 0


def metrics(entry: float, exit_price: float, direction: Direction, risk_per_share: float, post_entry_bars: list[dict]) -> MetricsAtom:
    pnl_dollars, pnl_pct = pnl(entry, exit_price, direction)
    mfe, mae = mfe_mae(post_entry_bars, entry, direction)
    return MetricsAtom(
        pnl=pnl_dollars,
        pnl_pct=pnl_pct,
        mfe=mfe,
        mae=mae,
        r_multiple=r_multiple(pnl_dollars, risk_per_share),
    )


def fixed_risk_position_size(risk_per_share: float, risk_dollars: float = DEFAULT_RISK_DOLLARS) -> int:
    """Whole-share size for fixed-dollar risk.

    Uses floor sizing so actual risk is never above the configured budget.
    """
    return floor(risk_dollars / risk_per_share) if risk_per_share > 0 else 0


def normalized_risk_outcome(
    *,
    entry: float,
    stop_price: float,
    pnl_per_share: float,
    risk_dollars: float = DEFAULT_RISK_DOLLARS,
) -> dict:
    """Return fixed-risk sizing, actual dollar P&L, and R multiple.

    This atom converts a strategy's per-share move into comparable trade P&L:

    - risk per share = ``abs(entry - stop_price)``
    - size = ``floor(risk_dollars / risk_per_share)``
    - actual risk dollars = ``risk_per_share * size``
    - P&L dollars = ``pnl_per_share * size``
    - R = ``pnl_per_share / risk_per_share``
    """
    risk_per_share = abs(float(entry) - float(stop_price))
    size = fixed_risk_position_size(risk_per_share, risk_dollars)
    actual_risk = risk_per_share * size
    pnl_dollars = float(pnl_per_share) * size
    r_ratio = float(pnl_per_share) / risk_per_share if risk_per_share > 0 else 0
    return {
        'pnl_per_share': round(float(pnl_per_share), 4),
        'risk_per_share': round(risk_per_share, 4),
        'size': size,
        'risk_dollars': round(actual_risk, 2),
        'pnl_dollars': round(pnl_dollars, 2),
        'r_ratio': round(r_ratio, 2),
    }


def enrich_trade_outcome(trade: dict, risk_dollars: float = DEFAULT_RISK_DOLLARS) -> dict:
    """Attach normalized-risk outcome fields to a trade payload in-place."""
    trade.update(normalized_risk_outcome(
        entry=trade.get('entry', 0),
        stop_price=trade.get('stop_price', 0),
        pnl_per_share=trade.get('pnl', 0),
        risk_dollars=risk_dollars,
    ))
    return trade


def summarize_normalized_trades(
    trades: list[dict],
    *,
    symbol: str,
    strategy: str,
    strategy_tf: str,
    direction_mode: str,
    stop_mode: str,
    or_minutes: int,
    fetch_interval: str,
    bars_1m_trade_count: int,
    total_days: int,
    skipped: int,
    risk_dollars: float = DEFAULT_RISK_DOLLARS,
) -> dict:
    """Build a summary from normalized-risk trade outcomes."""
    total_pnl = sum(t.get('pnl_dollars', 0) for t in trades)
    total_r = sum(t.get('r_ratio', 0) for t in trades)
    wins = [t for t in trades if t.get('pnl_dollars', 0) > 0]
    losses = [t for t in trades if t.get('pnl_dollars', 0) <= 0]
    longs = [t for t in trades if t['direction'] == 'long']
    shorts = [t for t in trades if t['direction'] == 'short']
    target_exits = sum(1 for t in trades if t.get('exit_reason') == 'target')
    stop_exits = sum(1 for t in trades if t.get('exit_reason') == 'stop')
    eod_exits = sum(1 for t in trades if t.get('exit_reason') == 'eod')
    market_close_exits = sum(1 for t in trades if t.get('exit_reason') == 'market_close')

    return {
        'symbol': symbol,
        'strategy': strategy,
        'strategy_timeframe': strategy_tf,
        'direction_mode': direction_mode,
        'stop_mode': stop_mode,
        'or_minutes': or_minutes,
        'interval': fetch_interval,
        'risk_per_trade': risk_dollars,
        'bars_1m_available': bars_1m_trade_count > 0,
        'bars_1m_trade_count': bars_1m_trade_count,
        'total_days': total_days,
        'trade_days': len(trades),
        'skipped_days': skipped,
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(len(wins) / len(trades) * 100, 1) if trades else 0,
        'total_pnl': round(total_pnl, 2),
        'avg_pnl': round(total_pnl / len(trades), 2) if trades else 0,
        'total_r': round(total_r, 2),
        'avg_r': round(total_r / len(trades), 2) if trades else 0,
        'avg_win': round(sum(t.get('pnl_dollars', 0) for t in wins) / len(wins), 2) if wins else 0,
        'avg_loss': round(sum(t.get('pnl_dollars', 0) for t in losses) / len(losses), 2) if losses else 0,
        'long_count': len(longs),
        'short_count': len(shorts),
        'target_exits': target_exits,
        'stop_exits': stop_exits,
        'eod_exits': eod_exits,
        'market_close_exits': market_close_exits,
        'best_trade': max((t.get('pnl_dollars', 0) for t in trades), default=0),
        'worst_trade': min((t.get('pnl_dollars', 0) for t in trades), default=0),
        'best_r': max((t.get('r_ratio', 0) for t in trades), default=0),
        'worst_r': min((t.get('r_ratio', 0) for t in trades), default=0),
    }

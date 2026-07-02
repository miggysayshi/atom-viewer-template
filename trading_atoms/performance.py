from __future__ import annotations

from .types import Direction, MetricsAtom


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

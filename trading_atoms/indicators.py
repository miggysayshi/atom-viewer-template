"""Deterministic, dependency-free technical indicator helpers.

These helpers back Trading Atoms that need moving averages / session VWAP
without pulling in pandas or numpy. They operate on plain lists of bars or
plain number sequences and return lists aligned to the input index. Missing
warmup values are returned as ``None`` so callers can demand strict lookback.

Rounding is kept coarse (4 decimals) to stay consistent with the rest of the
package's bar payloads.
"""

from __future__ import annotations

from typing import Iterable, Sequence

WARMUP_NONE = None  # explicit sentinel used in docstrings; values are real None


def ema(values: Sequence[float] | Iterable[float], period: int = 9) -> list[float | None]:
    """Return a simple EMA aligned to ``values``.

    - ``period`` must be a positive integer (validated).
    - Uses the standard ``alpha = 2 / (period + 1)`` smoothing constant.
    - The seed for the first EMA value is the SMA of the first ``period`` inputs.
    - Indexes before the warmup window are returned as ``None``.
    - All values are rounded to 4 decimal places for consistency.
    """
    if period <= 0:
        raise ValueError(f"ema period must be > 0, got {period}")
    seq = list(values)
    out: list[float | None] = [None] * len(seq)
    if len(seq) < period:
        return out

    alpha = 2.0 / (period + 1.0)
    seed = sum(seq[:period]) / period
    out[period - 1] = round(seed, 4)
    prev = seed
    for i in range(period, len(seq)):
        prev = seq[i] * alpha + prev * (1.0 - alpha)
        out[i] = round(prev, 4)
    return out


def sma(values: Sequence[float] | Iterable[float], period: int = 20) -> list[float | None]:
    """Return a simple moving average aligned to ``values``."""
    if period <= 0:
        raise ValueError(f"sma period must be > 0, got {period}")
    seq = list(values)
    out: list[float | None] = [None] * len(seq)
    running = 0.0
    for i, value in enumerate(seq):
        running += float(value)
        if i >= period:
            running -= float(seq[i - period])
        if i >= period - 1:
            out[i] = round(running / period, 4)
    return out


def true_range(bars: Sequence[dict]) -> list[float]:
    """Return Wilder true range per bar, aligned to ``bars``."""
    out: list[float] = []
    prev_close: float | None = None
    for b in bars:
        high = float(b['high'])
        low = float(b['low'])
        if prev_close is None:
            value = high - low
        else:
            value = max(high - low, abs(high - prev_close), abs(low - prev_close))
        out.append(round(value, 4))
        prev_close = float(b['close'])
    return out


def atr(bars: Sequence[dict], period: int = 14) -> list[float | None]:
    """Return Wilder ATR aligned to ``bars``."""
    if period <= 0:
        raise ValueError(f"atr period must be > 0, got {period}")
    ranges = true_range(bars)
    out: list[float | None] = [None] * len(ranges)
    if len(ranges) < period:
        return out
    prev = sum(ranges[:period]) / period
    out[period - 1] = round(prev, 4)
    for i in range(period, len(ranges)):
        prev = ((prev * (period - 1)) + ranges[i]) / period
        out[i] = round(prev, 4)
    return out


def average_candle_range(bars: Sequence[dict], period: int = 20) -> list[float | None]:
    """Return SMA of candle high-low ranges aligned to ``bars``."""
    if period <= 0:
        raise ValueError(f"average_candle_range period must be > 0, got {period}")
    return sma([float(b['high']) - float(b['low']) for b in bars], period=period)


def vwap(bars: Sequence[dict]) -> list[float | None]:
    """Return cumulative session VWAP per bar.

    Each bar contributes ``typical = (high + low + close) / 3`` weighted by
    ``volume``. Volumes of 0 / ``None`` are treated as 1 to keep the ratio
    well-defined when callers pass tick-style bars without volume data.

    Returns a list aligned to ``bars`` where index ``i`` holds VWAP through
    bar ``i`` (inclusive). Empty input yields ``[]``.
    """
    cum_pv = 0.0
    cum_vol = 0.0
    out: list[float | None] = []
    for b in bars:
        typical = (b['high'] + b['low'] + b['close']) / 3.0
        vol = b.get('volume') or 0
        # Treat absent/zero volume as 1 share so the ratio stays well-defined.
        weight = vol if vol > 0 else 1
        cum_pv += typical * weight
        cum_vol += weight
        out.append(round(cum_pv / cum_vol, 4))
    return out

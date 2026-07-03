from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .indicators import atr, average_candle_range, ema, sma, vwap

OverextensionSource = Literal['vwap', 'ema', 'sma']
OverextensionMeasure = Literal['atr', 'avg_candle_range']
OverextensionSide = Literal['above', 'below', 'at']


@dataclass
class OverextensionFilterAtom:
    """Distance-from-reference filter for avoiding overextended entries."""

    source: OverextensionSource
    measure: OverextensionMeasure
    lookback: int
    threshold: float
    price: float | None
    reference: float | None
    basis_value: float | None
    distance: float | None
    distance_multiple: float | None
    side: OverextensionSide
    is_overextended: bool
    ready: bool
    reason: str

    def to_payload(self) -> dict:
        return {
            'filter': 'overextension_distance_v1',
            'source': self.source,
            'measure': self.measure,
            'lookback': self.lookback,
            'threshold': self.threshold,
            'price': round(self.price, 4) if self.price is not None else None,
            'reference': round(self.reference, 4) if self.reference is not None else None,
            'basis_value': round(self.basis_value, 4) if self.basis_value is not None else None,
            'distance': round(self.distance, 4) if self.distance is not None else None,
            'distance_multiple': round(self.distance_multiple, 4) if self.distance_multiple is not None else None,
            'side': self.side,
            'is_overextended': self.is_overextended,
            'ready': self.ready,
            'reason': self.reason,
        }


def _not_ready(source: OverextensionSource, measure: OverextensionMeasure, lookback: int, threshold: float, reason: str) -> OverextensionFilterAtom:
    return OverextensionFilterAtom(
        source=source,
        measure=measure,
        lookback=lookback,
        threshold=threshold,
        price=None,
        reference=None,
        basis_value=None,
        distance=None,
        distance_multiple=None,
        side='at',
        is_overextended=False,
        ready=False,
        reason=reason,
    )


def _reference_values(bars: list[dict], source: OverextensionSource, lookback: int) -> list[float | None]:
    closes = [float(b['close']) for b in bars]
    if source == 'vwap':
        return vwap(bars)
    if source == 'ema':
        return ema(closes, period=lookback)
    if source == 'sma':
        return sma(closes, period=lookback)
    raise ValueError(f'unknown overextension source: {source}')


def _basis_values(bars: list[dict], measure: OverextensionMeasure, lookback: int) -> list[float | None]:
    if measure == 'atr':
        return atr(bars, period=lookback)
    if measure == 'avg_candle_range':
        return average_candle_range(bars, period=lookback)
    raise ValueError(f'unknown overextension measure: {measure}')


def distance_overextension_filter(
    bars: list[dict],
    *,
    source: OverextensionSource = 'vwap',
    measure: OverextensionMeasure = 'atr',
    lookback: int = 14,
    threshold: float = 2.0,
    index: int | None = None,
) -> OverextensionFilterAtom:
    """Measure current price distance from VWAP/EMA/SMA in ATRs or candle lengths.

    Intended as an entry guard: if ``is_overextended`` is true, skip or require
    a pullback before taking a fresh signal.

    Anti-hindsight: reference and basis values are computed through ``index``
    only. Default index is the latest bar.
    """
    if lookback <= 0:
        raise ValueError(f'lookback must be > 0, got {lookback}')
    if threshold < 0:
        raise ValueError(f'threshold must be >= 0, got {threshold}')
    if not bars:
        return _not_ready(source, measure, lookback, threshold, 'no_bars')

    idx = len(bars) - 1 if index is None else index
    if idx < 0 or idx >= len(bars):
        raise IndexError(f'index {idx} outside bars length {len(bars)}')
    known_bars = bars[:idx + 1]
    refs = _reference_values(known_bars, source, lookback)
    bases = _basis_values(known_bars, measure, lookback)
    reference = refs[-1]
    basis = bases[-1]
    if reference is None or basis is None or basis <= 0:
        return _not_ready(source, measure, lookback, threshold, 'insufficient_history')

    price = float(known_bars[-1]['close'])
    signed_distance = price - reference
    side: OverextensionSide = 'above' if signed_distance > 0 else 'below' if signed_distance < 0 else 'at'
    distance = abs(signed_distance)
    multiple = distance / basis
    return OverextensionFilterAtom(
        source=source,
        measure=measure,
        lookback=lookback,
        threshold=threshold,
        price=round(price, 4),
        reference=round(reference, 4),
        basis_value=round(basis, 4),
        distance=round(distance, 4),
        distance_multiple=round(multiple, 4),
        side=side,
        is_overextended=multiple > threshold,
        ready=True,
        reason='distance_above_threshold' if multiple > threshold else 'within_threshold',
    )

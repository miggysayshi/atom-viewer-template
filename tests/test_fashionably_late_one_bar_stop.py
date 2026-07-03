from __future__ import annotations

"""Unit tests for the fashionably-late EMA9 × VWAP cross entry atom
and the one-bar stop atom.

Isolated from `tests/test_trading_atoms.py` so the worker-C tests can run
independently of any other work-in-progress files in this directory.
"""

import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_atoms.entries import (
    FASHIONABLY_LATE_OPEN_AFTER,
    find_ema_vwap_cross_entry,
)
from trading_atoms.indicators import ema, vwap
from trading_atoms.sessions import annotate_et
from trading_atoms.stops import one_bar_stop

ET = dt.timezone(dt.timedelta(hours=-4))  # July fixtures = EDT


def ts(hour: int, minute: int) -> int:
    return int(dt.datetime(2026, 7, 1, hour, minute, tzinfo=ET).timestamp())


def bar(hour: int, minute: int, o: float, h: float, l: float, c: float, volume: int = 1000):
    t = ts(hour, minute)
    return {'ts': t, 'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': volume}


# ---------------------------------------------------------------------------
# Indicator helper sanity tests
# ---------------------------------------------------------------------------


class IndicatorHelperTests(unittest.TestCase):
    def test_ema_seeds_with_sma_and_smooths(self):
        # Classic 5-bar sequence: index 2 = SMA(3) = (1+2+3)/3 = 2.0.
        # alpha = 2/(3+1) = 0.5. Index 3 EMA = 0.5*4 + 0.5*2.0 = 3.0.
        # Index 4 EMA = 0.5*5 + 0.5*3.0 = 4.0.
        result = ema([1.0, 2.0, 3.0, 4.0, 5.0], period=3)
        self.assertEqual(result[0], None)
        self.assertEqual(result[1], None)
        self.assertEqual(result[2], 2.0)
        self.assertEqual(result[3], 3.0)
        self.assertEqual(result[4], 4.0)
        # Strict monotonicity: EMA must increase as the input sequence increases.
        for prev, cur in zip(result[2:], result[3:]):
            self.assertIsNotNone(prev)
            self.assertIsNotNone(cur)
            self.assertLess(prev, cur)  # type: ignore[operator] 

    def test_ema_warmup_returns_none(self):
        result = ema([1.0, 2.0], period=5)
        self.assertEqual(result, [None, None])

    def test_ema_rejects_invalid_period(self):
        with self.assertRaises(ValueError):
            ema([1.0, 2.0, 3.0], period=0)

    def test_vwap_is_cumulative_and_session_relative(self):
        # Choose volume-equalized bars so each tick has a deterministic share of weight.
        bars = [
            bar(9, 30, 100, 100, 100, 100),
            bar(9, 31, 100, 102, 100, 102),
            bar(9, 32, 102, 104, 102, 104),
            bar(9, 33, 104, 106, 104, 106),
        ]
        result = vwap(bars)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], 100.0)
        # Each subsequent typical is higher than the previous.
        self.assertIsNotNone(result[1])
        self.assertIsNotNone(result[2])
        self.assertIsNotNone(result[3])
        self.assertGreater(result[1], result[0])  # type: ignore[operator]
        self.assertGreater(result[2], result[1])  # type: ignore[operator]
        self.assertGreater(result[3], result[2])  # type: ignore[operator] 


# ---------------------------------------------------------------------------
# Cross-entry atoms
# ---------------------------------------------------------------------------


def _bullish_cross_bars() -> list[dict]:
    """Build 1m RTH bars that produce a bullish EMA9 × VWAP cross only after 09:45.

    Constructed so that:
      - 09:30-09:44 (15 bars): EMA trends below VWAP (price drifting down).
      - 09:45-09:50: EMA still catching up, no cross yet.
      - 09:51: first 1m bar after gate where EMA flips above VWAP => long cross.
    """
    bars: list[dict] = []
    # 09:30 to 09:44: 15 minutes of slow decline so EMA-9 sits clearly below VWAP.
    price = 100.0
    for m in range(30, 45):
        bars.append(bar(9, m, price, price + 0.1, price - 0.2, price - 0.05))
        price -= 0.05
    # 09:45 to 09:50: a brief bounce but EMA still below VWAP.
    bars.extend([
        bar(9, 45, 99.5, 99.7, 99.4, 99.6),
        bar(9, 46, 99.6, 99.8, 99.55, 99.75),
        bar(9, 47, 99.75, 99.9, 99.7, 99.85),
        bar(9, 48, 99.85, 100.0, 99.8, 99.95),
        bar(9, 49, 99.95, 100.1, 99.9, 100.05),
        bar(9, 50, 100.05, 100.2, 100.0, 100.15),
    ])
    # 09:51: strong 1m push well above VWAP, pulling EMA9 above VWAP for the cross.
    bars.extend([
        bar(9, 51, 100.5, 101.0, 100.45, 100.9),
        bar(9, 52, 100.9, 101.5, 100.85, 101.3),
        bar(9, 53, 101.3, 101.6, 101.25, 101.5),
        bar(9, 54, 101.5, 101.7, 101.45, 101.6),
        bar(9, 55, 101.6, 101.8, 101.55, 101.7),
        bar(9, 56, 101.7, 101.9, 101.65, 101.8),
    ])
    return annotate_et(bars)


def _bearish_cross_bars() -> list[dict]:
    """Mirror of _bullish_cross_bars — bearish cross after 09:45.

    09:30-09:44: 15 minutes of drift up so EMA-9 sits clearly above VWAP.
    09:45-09:50: EMA still above VWAP.
    09:51: aggressive selling bar pulls EMA below VWAP.
    """
    bars: list[dict] = []
    price = 100.0
    for m in range(30, 45):
        bars.append(bar(9, m, price, price + 0.2, price - 0.1, price + 0.05))
        price += 0.05
    bars.extend([
        bar(9, 45, 100.75, 100.9, 100.7, 100.85),
        bar(9, 46, 100.85, 100.95, 100.8, 100.9),
        bar(9, 47, 100.9, 101.0, 100.85, 100.95),
        bar(9, 48, 100.95, 101.05, 100.9, 101.0),
        bar(9, 49, 101.0, 101.1, 100.95, 101.05),
        bar(9, 50, 101.05, 101.15, 101.0, 101.1),
    ])
    # Sharp sell-down: close well below VWAP, dragging EMA below it.
    bars.extend([
        bar(9, 51, 101.1, 101.15, 99.5, 99.6),
        bar(9, 52, 99.6, 99.7, 98.5, 98.6),
        bar(9, 53, 98.6, 98.7, 97.5, 97.7),
        bar(9, 54, 97.7, 97.8, 96.7, 96.9),
        bar(9, 55, 96.9, 97.0, 95.9, 96.1),
        bar(9, 56, 96.1, 96.2, 95.0, 95.2),
    ])
    return annotate_et(bars)


def _pre_gate_only_cross_bars() -> list[dict]:
    """A pre-09:45 bullish cross, then range-bound afterward with no second cross.

    Strategy:
      - 09:30-09:35: 6 minutes of decline that pulls EMA just below VWAP (~99.7).
      - 09:36-09:44: 9 minutes of steady grinding higher that pulls EMA back above
        VWAP by 09:44 — that's the pre-gate bullish cross.
      - 09:45 onwards: bars stay tightly inside the same range. EMA and VWAP
        converge but never cross again in either direction.
    """
    bars: list[dict] = []
    # 09:30-09:35: small decline.
    bars.extend([
        bar(9, 30, 100.5, 100.6, 99.9, 100.0),
        bar(9, 31, 100.0, 100.05, 99.85, 99.9),
        bar(9, 32, 99.9, 99.95, 99.75, 99.8),
        bar(9, 33, 99.8, 99.85, 99.65, 99.7),
        bar(9, 34, 99.7, 99.75, 99.55, 99.6),
        bar(9, 35, 99.6, 99.65, 99.5, 99.55),
    ])
    # 09:36-09:44: nine 1m bars of steady grinding higher carrying EMA above VWAP.
    bars.extend([
        bar(9, 36, 99.6, 99.7, 99.55, 99.65),
        bar(9, 37, 99.65, 99.75, 99.6, 99.7),
        bar(9, 38, 99.7, 99.85, 99.65, 99.8),
        bar(9, 39, 99.8, 99.95, 99.75, 99.9),
        bar(9, 40, 99.9, 100.1, 99.85, 100.05),
        bar(9, 41, 100.05, 100.2, 100.0, 100.15),
        bar(9, 42, 100.15, 100.25, 100.1, 100.2),
        bar(9, 43, 100.2, 100.3, 100.15, 100.25),
        bar(9, 44, 100.25, 100.4, 100.2, 100.35),
    ])
    # 09:45 onward: tight range that keeps EMA and VWAP close without further cross.
    bars.extend([
        bar(9, 45, 100.35, 100.4, 100.25, 100.3),
        bar(9, 46, 100.3, 100.35, 100.2, 100.25),
        bar(9, 47, 100.25, 100.3, 100.15, 100.2),
        bar(9, 48, 100.2, 100.25, 100.1, 100.15),
        bar(9, 49, 100.15, 100.2, 100.05, 100.1),
        bar(9, 50, 100.1, 100.15, 100.0, 100.05),
    ])
    return annotate_et(bars)


class EmaVwapCrossEntryTests(unittest.TestCase):
    def test_bullish_cross_after_0945_triggers_long(self):
        entry = find_ema_vwap_cross_entry(_bullish_cross_bars(), timeframe='1m', ema_period=9)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'long')
        self.assertEqual(entry.anchor, 'bar_close')
        # Bar-open time must be strictly after 09:45.
        self.assertGreaterEqual(entry.bar['et'].time().hour, 9)
        self.assertGreater(
            (entry.bar['et'].hour, entry.bar['et'].minute),
            (9, 45),
        )
        # Entry price = close; close-time is one minute after bar-open.
        self.assertEqual(entry.price, entry.bar['close'])
        self.assertEqual(entry.ts, entry.bar_ts + 60)
        # EMA flipped above VWAP at the cross.
        self.assertGreater(entry.ema_at_entry, entry.vwap_at_entry)
        self.assertEqual(FASHIONABLY_LATE_OPEN_AFTER, dt.time(9, 45))

    def test_bearish_cross_after_0945_triggers_short(self):
        entry = find_ema_vwap_cross_entry(_bearish_cross_bars(), timeframe='1m', ema_period=9)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.anchor, 'bar_close')
        self.assertGreater(
            (entry.bar['et'].hour, entry.bar['et'].minute),
            (9, 45),
        )
        self.assertEqual(entry.price, entry.bar['close'])
        self.assertLess(entry.ema_at_entry, entry.vwap_at_entry)

    def test_cross_before_0945_is_ignored(self):
        # Pre-gate pop is engineered in this fixture; no cross happens after 09:45.
        self.assertIsNone(find_ema_vwap_cross_entry(_pre_gate_only_cross_bars(), timeframe='1m', ema_period=9))

    def test_no_cross_returns_none(self):
        bars = annotate_et([
            bar(9, 30, 100, 100.2, 99.8, 100.0),
            bar(9, 31, 100.0, 100.1, 99.9, 100.05),
            bar(9, 32, 100.05, 100.15, 99.95, 100.1),
            bar(9, 33, 100.1, 100.2, 100.0, 100.15),
            bar(9, 34, 100.15, 100.25, 100.05, 100.2),
            bar(9, 35, 100.2, 100.3, 100.1, 100.25),
            bar(9, 36, 100.25, 100.35, 100.15, 100.3),
            bar(9, 37, 100.3, 100.4, 100.2, 100.35),
            bar(9, 38, 100.35, 100.45, 100.25, 100.4),
            bar(9, 39, 100.4, 100.5, 100.3, 100.45),
            bar(9, 40, 100.45, 100.55, 100.35, 100.5),
            bar(9, 41, 100.5, 100.6, 100.4, 100.55),
            bar(9, 42, 100.55, 100.65, 100.45, 100.6),
            bar(9, 43, 100.6, 100.7, 100.5, 100.65),
            bar(9, 44, 100.65, 100.75, 100.55, 100.7),
            bar(9, 45, 100.7, 100.8, 100.6, 100.75),
            bar(9, 46, 100.75, 100.85, 100.65, 100.8),
            bar(9, 47, 100.8, 100.9, 100.7, 100.85),
        ])
        self.assertIsNone(find_ema_vwap_cross_entry(bars, timeframe='1m', ema_period=9))

    def test_direction_mode_filter(self):
        bars = _bullish_cross_bars()
        # Bullish bars only — short filter should suppress the long trigger.
        self.assertIsNone(find_ema_vwap_cross_entry(bars, timeframe='1m', ema_period=9, direction_mode='short'))
        # Long filter keeps it.
        self.assertIsNotNone(find_ema_vwap_cross_entry(bars, timeframe='1m', ema_period=9, direction_mode='long'))

    def test_to_payload_contains_required_fields(self):
        entry = find_ema_vwap_cross_entry(_bullish_cross_bars(), timeframe='1m', ema_period=9)
        self.assertIsNotNone(entry)
        assert entry is not None
        payload = entry.to_payload()
        self.assertEqual(payload['direction'], 'long')
        self.assertEqual(payload['anchor'], 'bar_close')
        self.assertEqual(payload['ema_at_entry'], round(entry.ema_at_entry, 4))
        self.assertEqual(payload['vwap_at_entry'], round(entry.vwap_at_entry, 4))
        self.assertIn('rule', payload)
        self.assertIn('cross_after_0945', payload['rule'])


# ---------------------------------------------------------------------------
# One-bar stop atom
# ---------------------------------------------------------------------------


class OneBarStopTests(unittest.TestCase):
    def test_long_stop_uses_entry_bar_low(self):
        entry_bar = bar(9, 55, 100, 103, 99, 102)
        stop = one_bar_stop(entry=102.0, entry_bar=entry_bar, direction='long')
        self.assertIsNotNone(stop)
        assert stop is not None
        self.assertEqual(stop.price, 99.0)
        self.assertEqual(stop.risk, 3.0)
        self.assertEqual(stop.rule, 'one_bar_stop')
        self.assertEqual(stop.rule_ref, 99.0)

    def test_short_stop_uses_entry_bar_high(self):
        entry_bar = bar(10, 0, 102, 105, 100, 101)
        stop = one_bar_stop(entry=101.0, entry_bar=entry_bar, direction='short')
        self.assertIsNotNone(stop)
        assert stop is not None
        self.assertEqual(stop.price, 105.0)
        self.assertEqual(stop.risk, 4.0)
        self.assertEqual(stop.rule, 'one_bar_stop')
        self.assertEqual(stop.rule_ref, 105.0)

    def test_long_stop_returns_none_when_risk_non_positive(self):
        # Pathological case: entry at or below the candle low (e.g. illiquid bar).
        entry_bar = bar(9, 55, 100, 103, 99, 102)
        stop = one_bar_stop(entry=99.0, entry_bar=entry_bar, direction='long')
        self.assertIsNone(stop)

    def test_short_stop_returns_none_when_risk_non_positive(self):
        entry_bar = bar(10, 0, 102, 105, 100, 101)
        stop = one_bar_stop(entry=105.0, entry_bar=entry_bar, direction='short')
        self.assertIsNone(stop)


# ---------------------------------------------------------------------------
# Composition: cross entry + one-bar stop
# ---------------------------------------------------------------------------


class CrossEntryWithOneBarStopTests(unittest.TestCase):
    def test_compose_long_cross_with_one_bar_stop(self):
        bars = _bullish_cross_bars()
        entry = find_ema_vwap_cross_entry(bars, timeframe='1m', ema_period=9)
        self.assertIsNotNone(entry)
        assert entry is not None
        stop = one_bar_stop(entry=entry.price, entry_bar=entry.bar, direction=entry.direction)
        self.assertIsNotNone(stop)
        assert stop is not None
        # Long one-bar stop = entry candle low; risk = entry - low.
        self.assertEqual(stop.price, entry.bar['low'])
        self.assertEqual(stop.risk, entry.price - entry.bar['low'])
        self.assertEqual(stop.rule, 'one_bar_stop')

    def test_compose_short_cross_with_one_bar_stop(self):
        bars = _bearish_cross_bars()
        entry = find_ema_vwap_cross_entry(bars, timeframe='1m', ema_period=9)
        self.assertIsNotNone(entry)
        assert entry is not None
        stop = one_bar_stop(entry=entry.price, entry_bar=entry.bar, direction=entry.direction)
        self.assertIsNotNone(stop)
        assert stop is not None
        # Short one-bar stop = entry candle high; risk = high - entry.
        self.assertEqual(stop.price, entry.bar['high'])
        self.assertEqual(stop.risk, entry.bar['high'] - entry.price)


if __name__ == '__main__':
    unittest.main()

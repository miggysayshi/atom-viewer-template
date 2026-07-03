from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_atoms.filters import distance_overextension_filter
from trading_atoms.indicators import atr, average_candle_range, sma


def bar(o: float, h: float, l: float, c: float, volume: int = 1000) -> dict:
    return {'open': o, 'high': h, 'low': l, 'close': c, 'volume': volume}


class OverextensionFilterTests(unittest.TestCase):
    def test_sma_helper_aligns_to_input_with_warmup_none(self):
        self.assertEqual(sma([1, 2, 3, 4], period=3), [None, None, 2.0, 3.0])

    def test_atr_uses_true_range_and_wilder_smoothing(self):
        bars = [
            bar(10, 11, 9, 10),      # TR 2
            bar(10, 13, 9, 12),      # TR 4
            bar(12, 16, 11, 15),     # TR 5 => seed ATR(3)=3.6667
            bar(15, 18, 14, 17),     # TR 4 => (3.6667*2+4)/3=3.7778
        ]
        result = atr(bars, period=3)
        self.assertEqual(result[:2], [None, None])
        self.assertEqual(result[2], 3.6667)
        self.assertEqual(result[3], 3.7778)

    def test_average_candle_range(self):
        bars = [bar(10, 11, 9, 10), bar(10, 15, 12, 14), bar(14, 17, 13, 15)]
        self.assertEqual(average_candle_range(bars, period=2), [None, 2.5, 3.5])

    def test_filter_flags_vwap_overextension_measured_in_atr(self):
        bars = [
            bar(100, 102, 98, 100, 1000),
            bar(100, 102, 98, 100, 1000),
            bar(100, 102, 98, 100, 1000),
            bar(100, 112, 108, 110, 1000),
        ]
        atom = distance_overextension_filter(
            bars,
            source='vwap',
            measure='atr',
            lookback=3,
            threshold=1.0,
        )
        self.assertTrue(atom.is_overextended)
        self.assertEqual(atom.source, 'vwap')
        self.assertEqual(atom.measure, 'atr')
        self.assertEqual(atom.side, 'above')
        self.assertGreater(atom.distance_multiple, 1.0)
        payload = atom.to_payload()
        self.assertEqual(payload['filter'], 'overextension_distance_v1')
        self.assertTrue(payload['is_overextended'])

    def test_filter_can_measure_ema_distance_in_average_candle_lengths(self):
        bars = [
            bar(100, 101, 99, 100),
            bar(100, 101, 99, 100),
            bar(100, 101, 99, 100),
            bar(100, 106, 104, 105),
        ]
        atom = distance_overextension_filter(
            bars,
            source='ema',
            measure='avg_candle_range',
            lookback=3,
            threshold=1.0,
        )
        self.assertTrue(atom.is_overextended)
        self.assertEqual(atom.side, 'above')
        self.assertEqual(atom.basis_value, 2.0)

    def test_filter_returns_not_ready_when_warmup_missing(self):
        atom = distance_overextension_filter([bar(100, 101, 99, 100)], source='sma', measure='atr', lookback=5)
        self.assertFalse(atom.ready)
        self.assertFalse(atom.is_overextended)
        self.assertEqual(atom.reason, 'insufficient_history')


if __name__ == '__main__':
    unittest.main()

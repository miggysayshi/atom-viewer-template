from __future__ import annotations

import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_atoms.strategies.orb import run_orb_for_day

ET = dt.timezone(dt.timedelta(hours=-4))  # July test fixtures = EDT


def ts(hour: int, minute: int) -> int:
    return int(dt.datetime(2026, 7, 1, hour, minute, tzinfo=ET).timestamp())


def bar(hour, minute, o, h, l, c):
    t = ts(hour, minute)
    return {'ts': t, 'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': 1000}


def base_or_bars():
    return [
        bar(9, 30, 100, 101, 99, 100),
        bar(9, 35, 100, 101, 99, 100),
        bar(9, 40, 100, 101, 99, 100),
    ]


class TradingAtomsOrbTests(unittest.TestCase):
    def test_no_breakout_returns_none(self):
        bars = base_or_bars() + [bar(9, 45, 100, 100.5, 99.5, 100), bar(15, 55, 100, 100.5, 99.5, 100)]
        self.assertIsNone(run_orb_for_day(bars, 15))

    def test_long_target_hit(self):
        bars = base_or_bars() + [bar(9, 45, 101, 101.5, 100.5, 101.2), bar(9, 50, 101.2, 107.1, 101.1, 107)]
        trade = run_orb_for_day(bars, 15)
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'long')
        self.assertEqual(trade['entry'], 101)
        self.assertEqual(trade['stop_price'], 99)
        self.assertEqual(trade['target_price'], 107)
        self.assertEqual(trade['exit_reason'], 'target')
        self.assertEqual(trade['pnl'], 6)

    def test_short_stop_hit(self):
        bars = base_or_bars() + [bar(9, 45, 99, 100, 98.5, 98.8), bar(9, 50, 99, 101.2, 98.8, 101)]
        trade = run_orb_for_day(bars, 15)
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'short')
        self.assertEqual(trade['entry'], 99)
        self.assertEqual(trade['stop_price'], 101)
        self.assertEqual(trade['target_price'], 93)
        self.assertEqual(trade['exit_reason'], 'stop')
        self.assertEqual(trade['pnl'], -2)

    def test_same_bar_collision_stop_wins_for_long(self):
        bars = base_or_bars() + [bar(9, 45, 101, 107.5, 98.5, 100)]
        trade = run_orb_for_day(bars, 15)
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['exit_reason'], 'stop')
        self.assertEqual(trade['exit'], 99)
        self.assertTrue(trade['atoms']['exit']['same_bar_collision'])

    def test_eod_exit_uses_last_rth_close(self):
        bars = base_or_bars() + [bar(9, 45, 101, 102, 100, 101.2), bar(15, 55, 101.2, 102, 100, 101.5)]
        trade = run_orb_for_day(bars, 15)
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['exit_reason'], 'eod')
        self.assertEqual(trade['exit'], 101.5)

    def test_same_first_bar_both_directions_is_long_biased(self):
        bars = base_or_bars() + [bar(9, 45, 100, 102, 98, 100)]
        trade = run_orb_for_day(bars, 15)
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'long')


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations

import datetime as dt
import math
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_atoms.exits import ema_trailing_stop_exit, previous_bar_trailing_exit
from trading_atoms.stops import (
    ema_trailing_stop_snapshot,
    previous_bar_trailing_stop_snapshot,
    sma100_1m_target,
    sma200_1m_target,
    vwap_target,
)
from trading_atoms.types import StopAtom

ET = dt.timezone(dt.timedelta(hours=-4))


def ts(hour: int, minute: int) -> int:
    return int(dt.datetime(2026, 7, 1, hour, minute, tzinfo=ET).timestamp())


def bar(hour, minute, o, h, l, c, volume=1000):
    t = ts(hour, minute)
    return {'ts': t, 'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': volume}


def bars_1m(count: int, close_start: float = 100.0):
    out = []
    base = dt.datetime(2026, 7, 1, 9, 30, tzinfo=ET)
    for i in range(count):
        t = int((base + dt.timedelta(minutes=i)).timestamp())
        c = close_start + i * 0.01
        out.append({'ts': t, 'time': t, 'open': c, 'high': c + 0.05, 'low': c - 0.05, 'close': c, 'volume': 1000})
    return out


class PreviousBarTrailingStopTests(unittest.TestCase):
    def test_long_snapshot_ratchets_to_prior_completed_bar_only(self):
        bars = [
            bar(9, 30, 100, 101, 99, 100.5),
            bar(9, 35, 100.5, 102, 100, 101.5),
            bar(9, 40, 101.5, 103, 101, 102.5),
            bar(9, 45, 102.5, 104, 98, 99),
        ]
        initial = StopAtom(price=98, risk=2, rule='initial', rule_ref=98)
        snap = previous_bar_trailing_stop_snapshot(100, bars, entry_ts=ts(9, 30), direction='long', initial_stop=initial, known_through_ts=ts(9, 45))
        self.assertEqual(snap.price, 101)
        # The 09:45 low is 98 but cannot loosen/use current bar.
        self.assertEqual(snap.rule, 'previous_bar_trailing_stop')

    def test_previous_bar_trailing_exit_uses_stop_before_updating_from_live_bar(self):
        bars = [
            bar(9, 30, 100, 101, 99, 100.5),
            bar(9, 35, 100.5, 102, 100, 101.5),
            bar(9, 40, 101.5, 103, 101, 102.5),
            bar(9, 45, 102.5, 103, 100.5, 100.7),
        ]
        initial = StopAtom(price=98, risk=2, rule='initial', rule_ref=98)
        exit_atom = previous_bar_trailing_exit(bars, entry_ts=ts(9, 30), direction='long', initial_stop=initial)
        self.assertIsNotNone(exit_atom)
        assert exit_atom is not None
        self.assertEqual(exit_atom.reason, 'stop')
        self.assertEqual(exit_atom.price, 101)
        self.assertEqual(exit_atom.ts, ts(9, 45))


class EmaTrailingStopTests(unittest.TestCase):
    def test_ema_snapshot_requires_warmup(self):
        bars = bars_1m(9)
        snap = ema_trailing_stop_snapshot(100, bars, entry_ts=bars[-1]['ts'], direction='long', fast_period=10, slow_period=20)
        self.assertIsNone(snap)

    def test_ema_exit_both_is_slower_than_either(self):
        bars = bars_1m(25, close_start=100)
        # Push one bar just under fast EMA but not slow, then later under both.
        bars[20]['close'] = bars[20]['low'] = 99.9
        bars[21]['close'] = bars[21]['low'] = 98.0
        either_exit = ema_trailing_stop_exit(bars, entry_ts=bars[19]['ts'], direction='long', mode='either')
        both_exit = ema_trailing_stop_exit(bars, entry_ts=bars[19]['ts'], direction='long', mode='both')
        self.assertIsNotNone(either_exit)
        self.assertIsNotNone(both_exit)
        assert either_exit is not None and both_exit is not None
        self.assertLessEqual(either_exit.ts, both_exit.ts)
        self.assertEqual(both_exit.reason, 'stop')


class MovingAverageTargetTests(unittest.TestCase):
    def test_vwap_target_snapshot(self):
        bars = [bar(9, 30, 100, 101, 99, 100, volume=10), bar(9, 31, 100, 102, 100, 101, volume=20)]
        target = vwap_target(direction='long', rth_bars=bars, evaluation_ts=bars[-1]['ts'])
        self.assertIsNotNone(target)
        assert target is not None
        expected = round((((101 + 99 + 100) / 3) * 10 + ((102 + 100 + 101) / 3) * 20) / 30, 4)
        self.assertEqual(target.price, expected)
        self.assertTrue(math.isnan(target.multiple))
        self.assertEqual(target.rule, 'vwap_session_through_bar')

    def test_sma_targets_warmup(self):
        bars = bars_1m(199)
        self.assertIsNotNone(sma100_1m_target(direction='long', rth_bars_1m=bars, evaluation_ts=bars[-1]['ts']))
        self.assertIsNone(sma200_1m_target(direction='long', rth_bars_1m=bars, evaluation_ts=bars[-1]['ts']))
        bars.append(bars_1m(200)[-1])
        target = sma200_1m_target(direction='long', rth_bars_1m=bars, evaluation_ts=bars[-1]['ts'])
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.rule, 'sma200_1m_target')


if __name__ == '__main__':
    unittest.main()

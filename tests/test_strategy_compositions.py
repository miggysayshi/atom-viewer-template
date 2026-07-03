from __future__ import annotations

import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_atoms.strategies.fashionably_late import run_fashionably_late_for_day
from trading_atoms.strategies.engulfing_fvg import run_engulfing_for_day, run_fvg_retrace_for_day
from trading_atoms.strategies.larry_williams import run_larry_williams_3bar_for_day
from trading_atoms.strategies.premarket import run_premarket_breakout_for_day, run_premarket_reentry_for_day

ET = dt.timezone(dt.timedelta(hours=-4))


def ts(hour: int, minute: int) -> int:
    return int(dt.datetime(2026, 7, 1, hour, minute, tzinfo=ET).timestamp())


def bar(hour: int, minute: int, o: float, h: float, l: float, c: float, volume: int = 1000):
    t = ts(hour, minute)
    return {'ts': t, 'time': t, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': volume}


def pre_bars(high: float = 102.0, low: float = 99.0):
    return [
        bar(4, 0, low, high, low, low),
        bar(4, 15, low, high, low, high),
    ]


class PremarketStrategyCompositionTests(unittest.TestCase):
    def test_premarket_breakout_strategy_composes_entry_stop_exit(self):
        bars = pre_bars() + [
            bar(9, 30, 100, 101.5, 99.5, 101.0),
            bar(9, 35, 101.0, 103.0, 100.8, 102.7),
            bar(9, 40, 102.7, 104.0, 102.0, 103.5),
            bar(15, 55, 103.5, 104.0, 102.0, 103.0),
        ]
        trade = run_premarket_breakout_for_day(bars, direction_mode='long')
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'long')
        self.assertEqual(trade['atoms']['tested_atom'], 'premarket_breakout_entry_v1')
        self.assertEqual(trade['entry_time'], '09:40')
        self.assertEqual(trade['entry_anchor'], 'bar_close')
        self.assertEqual(trade['atoms']['premarket_range']['high'], 102.0)
        self.assertEqual(trade['atoms']['stop']['rule'], 'current_lod_at_entry_for_long')

    def test_premarket_breakout_can_use_one_bar_stop(self):
        bars = pre_bars() + [
            bar(9, 30, 100, 101.5, 99.5, 101.0),
            bar(9, 35, 101.0, 103.0, 100.8, 102.7),
            bar(9, 40, 102.7, 104.0, 102.0, 103.5),
            bar(15, 55, 103.5, 104.0, 102.0, 103.0),
        ]
        trade = run_premarket_breakout_for_day(bars, direction_mode='long', stop_mode='one_bar')
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['atoms']['params']['stop_mode'], 'one_bar')
        self.assertEqual(trade['atoms']['stop']['rule'], 'entry_candle_low_for_long')
        self.assertEqual(trade['stop_price'], 100.8)
        self.assertEqual(trade['atoms']['stop']['risk_per_share'], 1.9)

    def test_premarket_reentry_strategy_composes_entry_stop_exit(self):
        bars = pre_bars() + [
            bar(9, 30, 100, 103.0, 99.5, 102.5),
            bar(9, 35, 102.5, 102.5, 99.8, 101.0),
            bar(9, 40, 101.0, 103.0, 100.5, 102.0),
            bar(15, 55, 102.0, 102.5, 100.0, 101.2),
        ]
        trade = run_premarket_reentry_for_day(bars, direction_mode='short')
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'short')
        self.assertEqual(trade['atoms']['tested_atom'], 'premarket_reentry_entry_v1')
        self.assertEqual(trade['entry_time'], '09:40')
        self.assertEqual(trade['entry_anchor'], 'bar_close')
        self.assertIn('after PMH break', trade['reason_for_entry'])
        self.assertEqual(trade['atoms']['stop']['rule'], 'current_hod_at_entry_for_short')
    def test_premarket_reentry_can_use_one_bar_stop(self):
        bars = pre_bars() + [
            bar(9, 30, 100, 103.0, 99.5, 102.5),
            bar(9, 35, 102.5, 102.5, 99.8, 101.0),
            bar(9, 40, 101.0, 103.0, 100.5, 102.0),
            bar(15, 55, 102.0, 102.5, 100.0, 101.2),
        ]
        trade = run_premarket_reentry_for_day(bars, direction_mode='short', stop_mode='one_bar')
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['atoms']['params']['stop_mode'], 'one_bar')
        self.assertEqual(trade['atoms']['stop']['rule'], 'entry_candle_high_for_short')
        self.assertEqual(trade['stop_price'], 102.5)
        self.assertEqual(trade['atoms']['stop']['risk_per_share'], 1.5)


class FashionablyLateStrategyCompositionTests(unittest.TestCase):
    def _fashionably_late_long_bars(self) -> list[dict]:
        bars: list[dict] = []
        price = 100.0
        for m in range(30, 45):
            bars.append(bar(9, m, price, price + 0.1, price - 0.2, price - 0.05))
            price -= 0.05
        bars.extend([
            bar(9, 45, 99.5, 99.7, 99.4, 99.6),
            bar(9, 46, 99.6, 99.8, 99.55, 99.75),
            bar(9, 47, 99.75, 99.9, 99.7, 99.85),
            bar(9, 48, 99.85, 100.0, 99.8, 99.95),
            bar(9, 49, 99.95, 100.1, 99.9, 100.05),
            bar(9, 50, 100.05, 100.2, 100.0, 100.15),
            bar(9, 51, 100.5, 101.0, 100.45, 100.9),
            bar(9, 52, 100.9, 101.5, 100.85, 101.3),
            bar(10, 0, 101.3, 102.4, 100.8, 102.1),
            bar(15, 55, 102.1, 102.2, 101.8, 102.0),
        ])
        return bars

    def test_fashionably_late_strategy_composes_cross_entry_one_bar_stop_3r_target_exit(self):
        trade = run_fashionably_late_for_day(
            self._fashionably_late_long_bars(),
            timeframe='1m',
            direction_mode='long',
            stop_mode='one_bar',
            target_multiple=3.0,
        )
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'long')
        self.assertEqual(trade['atoms']['tested_atom'], 'ema_vwap_cross_entry_v2')
        self.assertEqual(trade['atoms']['stop']['rule'], 'entry_candle_low_for_long')
        self.assertEqual(trade['atoms']['target']['rule'], 'r_multiple')
        self.assertEqual(trade['atoms']['target']['multiple'], 3.0)
        self.assertEqual(trade['target_price'], round(trade['entry'] + 3.0 * trade['atoms']['stop']['risk_per_share'], 4))
        self.assertEqual(trade['exit_reason'], 'target')
        self.assertEqual(trade['entry_anchor'], 'bar_close')
        self.assertIn('EMA9/VWAP cross', trade['reason_for_entry'])

    def test_fashionably_late_can_compare_current_extrema_stop_variant(self):
        trade = run_fashionably_late_for_day(
            self._fashionably_late_long_bars(),
            timeframe='1m',
            direction_mode='long',
            stop_mode='current_extrema',
            target_multiple=3.0,
        )
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['atoms']['params']['stop_mode'], 'current_extrema')
        self.assertEqual(trade['atoms']['stop']['rule'], 'current_lod_at_entry_for_long')
        self.assertLess(trade['stop_price'], 100.45)
        self.assertEqual(trade['atoms']['target']['multiple'], 3.0)


class LarryWilliamsThreeBarStrategyCompositionTests(unittest.TestCase):
    def test_larry_williams_three_bar_short_composes_entry_one_bar_stop_exit(self):
        bars = [
            bar(9, 30, 100, 101.0, 99.5, 100.4),
            bar(9, 45, 100.4, 102.5, 100.0, 101.8),
            bar(10, 0, 101.8, 101.9, 100.7, 101.0),
            bar(10, 15, 100.8, 101.2, 99.8, 100.0),
            bar(15, 55, 101.0, 101.2, 99.8, 100.2),
        ]
        trade = run_larry_williams_3bar_for_day(
            bars,
            timeframe='15m',
            direction_mode='short',
            stop_mode='one_bar',
        )
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'short')
        self.assertEqual(trade['atoms']['tested_atom'], 'three_bar_pivot_reversal_entry_v1')
        self.assertEqual(trade['entry'], 100.8)
        self.assertEqual(trade['entry_time'], '10:15')
        self.assertEqual(trade['entry_bar_ts'], ts(10, 15))
        self.assertEqual(trade['entry_anchor'], 'bar_open')
        self.assertEqual(trade['atoms']['stop']['rule'], 'signal_candle_high_for_next_open_short')
        self.assertEqual(trade['stop_price'], 101.9)
        self.assertIn('high → higher high → lower high', trade['reason_for_entry'])

    def test_larry_williams_can_use_lower_timeframe_one_bar_stop(self):
        bars = [
            bar(9, 30, 100.0, 100.7, 99.5, 100.3),
            bar(9, 35, 100.3, 101.0, 100.0, 100.6),
            bar(9, 40, 100.6, 100.9, 100.1, 100.4),
            bar(9, 45, 100.4, 102.5, 100.2, 101.8),
            bar(9, 50, 101.8, 102.1, 100.5, 101.2),
            bar(9, 55, 101.2, 101.6, 100.7, 101.0),
            bar(10, 0, 101.0, 101.9, 100.6, 101.5),
            bar(10, 5, 101.5, 101.4, 100.8, 101.0),
            bar(10, 10, 101.0, 101.2, 100.5, 100.7),
            bar(10, 15, 100.8, 101.0, 99.8, 100.0),
            bar(15, 55, 101.0, 101.2, 99.8, 100.2),
        ]
        trade = run_larry_williams_3bar_for_day(
            bars,
            timeframe='15m',
            direction_mode='short',
            stop_mode='one_bar',
            risk_timeframe='5m',
        )
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['entry_time'], '10:15')
        self.assertEqual(trade['atoms']['params']['timeframe'], '15m')
        self.assertEqual(trade['atoms']['params']['risk_timeframe'], '5m')
        self.assertEqual(trade['atoms']['stop']['rule'], 'lower_tf_signal_candle_high_for_next_open_short')
        self.assertEqual(trade['atoms']['stop']['basis_bar_time'], '10:10')
        self.assertEqual(trade['stop_price'], 101.2)
        self.assertIn('risk managed on last completed 5m candle', trade['reason_for_entry'])

    def test_larry_williams_three_bar_long_composes_entry_current_extrema_stop_exit(self):
        bars = [
            bar(9, 30, 100, 100.5, 99.0, 99.5),
            bar(9, 45, 99.5, 100.0, 97.8, 98.4),
            bar(10, 0, 98.4, 99.4, 98.2, 99.0),
            bar(10, 15, 99.2, 99.9, 98.9, 99.8),
            bar(15, 55, 99.0, 100.0, 98.8, 99.7),
        ]
        trade = run_larry_williams_3bar_for_day(bars, timeframe='15m', direction_mode='long')
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'long')
        self.assertEqual(trade['entry'], 99.2)
        self.assertEqual(trade['entry_time'], '10:15')
        self.assertEqual(trade['atoms']['entry']['rule'], 'three_bar_pivot_low_reversal')
        self.assertEqual(trade['atoms']['stop']['rule'], 'current_lod_at_entry_for_long')
        self.assertEqual(trade['stop_price'], 97.8)
        self.assertIn('low → lower low → higher low', trade['reason_for_entry'])


class EngulfingFvgStrategyCompositionTests(unittest.TestCase):
    def test_engulfing_strategy_composes_close_entry_stop_exit(self):
        bars = [
            bar(9, 30, 100.0, 101.8, 99.8, 101.5),
            bar(9, 45, 101.2, 101.4, 99.0, 99.5),
            bar(10, 0, 99.5, 100.0, 98.8, 99.2),
            bar(15, 55, 99.2, 99.4, 98.6, 98.9),
        ]
        trade = run_engulfing_for_day(bars, timeframe='15m', direction_mode='short', stop_mode='one_bar')
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'short')
        self.assertEqual(trade['entry'], 99.5)
        self.assertEqual(trade['entry_time'], '10:00')
        self.assertEqual(trade['entry_anchor'], 'bar_close')
        self.assertEqual(trade['atoms']['tested_atom'], 'engulfing_close_entry_v1')
        self.assertEqual(trade['atoms']['entry']['rule'], 'engulfing_close_below_previous_low')
        self.assertEqual(trade['atoms']['stop']['rule'], 'entry_candle_high_for_short')
        self.assertIn('close below previous low', trade['reason_for_entry'])

    def test_fvg_retrace_strategy_composes_midpoint_entry_suggested_stop_exit(self):
        bars = [
            bar(9, 30, 106, 108, 105, 107),
            bar(9, 45, 110, 112, 106, 109),
            bar(10, 0, 99, 100, 95, 96),
            bar(10, 15, 100, 101, 99, 100),
            bar(10, 30, 102, 103, 101, 102.2),
            bar(15, 55, 102.2, 102.4, 100.0, 101.0),
        ]
        trade = run_fvg_retrace_for_day(bars, timeframe='15m', direction_mode='short')
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'short')
        self.assertEqual(trade['entry'], 102.5)
        self.assertEqual(trade['entry_time'], '10:30')
        self.assertEqual(trade['entry_anchor'], 'bar_open')
        self.assertEqual(trade['stop_price'], 112)
        self.assertEqual(trade['atoms']['tested_atom'], 'fair_value_gap_retrace_entry_v1')
        self.assertEqual(trade['atoms']['entry']['execution'], 'fvg_midpoint_retrace_touch')
        self.assertEqual(trade['atoms']['stop']['rule'], 'bearish_fvg_candle_high')
        self.assertIn('50% retrace', trade['reason_for_entry'])


if __name__ == '__main__':
    unittest.main()

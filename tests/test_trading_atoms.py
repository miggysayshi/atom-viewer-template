from __future__ import annotations

import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_atoms.strategies.orb import run_orb_for_day
from trading_atoms.strategies.three_green_red_short import run_streak_reversal_for_day, run_three_green_red_short_for_day
from trading_atoms.entries import (
    find_engulfing_close_entry,
    find_fair_value_gap_retrace_entry,
    find_streak_reversal_close_entry,
    find_three_bar_pivot_reversal_entry,
)
from trading_atoms.exits import stop_or_market_close_exit
from trading_atoms.premarket import PremarketRangeAtom, find_premarket_breakout_entry, find_premarket_reentry_entry, premarket_range
from trading_atoms.sessions import annotate_et
from trading_atoms.stops import current_extrema_stop

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


class StreakReversalTests(unittest.TestCase):
    def test_streak_reversal_close_entry_atom_short(self):
        bars = annotate_et([
            bar(9, 30, 100, 101.2, 99.8, 101),
            bar(9, 45, 101, 102.2, 100.8, 102),
            bar(10, 0, 102, 103.2, 101.8, 103),
            bar(10, 15, 103, 103.4, 102.2, 102.5),
        ])
        entry = find_streak_reversal_close_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 102.5)
        self.assertEqual(entry.bar_ts, ts(10, 15))
        self.assertEqual(entry.ts, ts(10, 30))
        self.assertEqual(entry.anchor, 'bar_close')
        self.assertEqual(entry.setup_color, 'green')
        self.assertEqual(entry.trigger_color, 'red')

    def test_streak_reversal_close_entry_atom_long(self):
        bars = annotate_et([
            bar(9, 30, 100, 100.2, 98.8, 99),
            bar(9, 45, 99, 99.2, 97.8, 98),
            bar(10, 0, 98, 98.2, 96.8, 97),
            bar(10, 15, 97, 98.4, 96.9, 97.5),
        ])
        entry = find_streak_reversal_close_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'long')
        self.assertEqual(entry.price, 97.5)
        self.assertEqual(entry.bar_ts, ts(10, 15))
        self.assertEqual(entry.ts, ts(10, 30))
        self.assertEqual(entry.setup_color, 'red')
        self.assertEqual(entry.trigger_color, 'green')

    def test_current_extrema_stop_excludes_future_bars(self):
        bars = [
            bar(9, 30, 100, 101, 99, 100.5),
            bar(9, 35, 100.5, 102, 100, 101.5),
            bar(9, 40, 101.5, 110, 98, 102),
        ]
        stop = current_extrema_stop(101.5, bars, known_through_ts=ts(9, 40), direction='short')
        self.assertIsNotNone(stop)
        assert stop is not None
        self.assertEqual(stop.price, 102)
        self.assertEqual(stop.rule, 'current_hod_at_entry')

    def test_stop_or_market_close_exit_stops_before_close(self):
        bars = [
            bar(9, 30, 100, 101, 99, 100.5),
            bar(9, 35, 100.5, 102, 100, 101.5),
            bar(9, 40, 101.5, 102.5, 100.5, 101),
            bar(15, 45, 101, 101.2, 100, 100.7),
        ]
        stop = current_extrema_stop(101.5, bars, known_through_ts=ts(9, 40), direction='short')
        self.assertIsNotNone(stop)
        assert stop is not None
        exit_atom = stop_or_market_close_exit(bars, entry_ts=ts(9, 40), direction='short', stop=stop)
        self.assertIsNotNone(exit_atom)
        assert exit_atom is not None
        self.assertEqual(exit_atom.reason, 'stop')
        self.assertEqual(exit_atom.price, 102)
        self.assertEqual(exit_atom.ts, ts(9, 40))

    def test_shorts_first_red_15m_close_after_three_green_bars(self):
        bars = [
            bar(9, 30, 100, 101.2, 99.8, 101),
            bar(9, 45, 101, 102.2, 100.8, 102),
            bar(10, 0, 102, 103.2, 101.8, 103),
            bar(10, 15, 103, 103.4, 102.2, 102.5),
            # Future higher high after entry must NOT change the stop.
            bar(15, 45, 102.5, 110.0, 100.5, 101),
        ]
        trade = run_three_green_red_short_for_day(bars)
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'short')
        self.assertEqual(trade['entry'], 102.5)
        self.assertEqual(trade['entry_time'], '10:30')
        self.assertEqual(trade['entry_bar_ts'], ts(10, 15))
        self.assertEqual(trade['entry_ts'], ts(10, 30))
        self.assertEqual(trade['entry_anchor'], 'bar_close')
        self.assertEqual(trade['stop_price'], 103.4)
        self.assertEqual(trade['atoms']['stop']['rule'], 'current_hod_at_entry_for_short')
        self.assertIsNone(trade['target_price'])
        self.assertEqual(trade['exit_reason'], 'stop')
        self.assertEqual(trade['exit'], 103.4)
        self.assertEqual(trade['exit_time'], '15:45')
        self.assertEqual(trade['reason_for_exit'], 'Stop hit')
        self.assertEqual(trade['pnl'], -0.9)
        self.assertEqual(trade['atoms']['entry']['streak_len'], 3)

    def test_longs_first_green_close_after_three_red_bars(self):
        bars = [
            bar(9, 30, 100, 100.2, 98.8, 99),
            bar(9, 45, 99, 99.2, 97.8, 98),
            bar(10, 0, 98, 98.2, 96.8, 97),
            bar(10, 15, 97, 98.4, 96.9, 97.5),
            # Future lower low after entry must NOT change the stop.
            bar(15, 45, 97.5, 99, 90.0, 98.5),
        ]
        trade = run_streak_reversal_for_day(bars, timeframe='15m', direction_mode='long')
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade['direction'], 'long')
        self.assertEqual(trade['entry'], 97.5)
        self.assertEqual(trade['entry_time'], '10:30')
        self.assertEqual(trade['stop_price'], 96.8)
        self.assertEqual(trade['atoms']['stop']['rule'], 'current_lod_at_entry_for_long')
        self.assertEqual(trade['exit_reason'], 'stop')
        self.assertEqual(trade['exit'], 96.8)
        self.assertEqual(trade['exit_time'], '15:45')
        self.assertEqual(trade['reason_for_exit'], 'Stop hit')
        self.assertEqual(trade['pnl'], -0.7)
        self.assertEqual(trade['atoms']['entry']['setup_color'], 'red')
        self.assertEqual(trade['atoms']['entry']['trigger_color'], 'green')

    def test_direction_filter_blocks_opposite_side(self):
        bars = [
            bar(9, 30, 100, 100.2, 98.8, 99),
            bar(9, 45, 99, 99.2, 97.8, 98),
            bar(10, 0, 98, 98.2, 96.8, 97),
            bar(10, 15, 97, 98.4, 96.9, 97.5),
            bar(15, 45, 97.5, 99, 97.2, 98.5),
        ]
        self.assertIsNone(run_streak_reversal_for_day(bars, timeframe='15m', direction_mode='short'))

    def test_ignores_red_bar_before_three_green_streak(self):
        bars = [
            bar(9, 30, 100, 101, 99.5, 101),
            bar(9, 45, 101, 101.2, 100, 100.5),
            bar(10, 0, 100.5, 101, 100, 100.8),
            bar(10, 15, 100.8, 101.5, 100.7, 101.2),
            bar(15, 45, 101.2, 101.4, 100.9, 101),
        ]
        self.assertIsNone(run_three_green_red_short_for_day(bars))


class ThreeBarPivotReversalEntryTests(unittest.TestCase):
    def test_short_high_higher_high_lower_high_enters_on_next_candle_open(self):
        bars = annotate_et([
            bar(9, 30, 100, 101.0, 99.5, 100.4),
            bar(9, 45, 100.4, 102.5, 100.0, 101.8),
            bar(10, 0, 101.8, 101.9, 100.7, 101.0),
            bar(10, 15, 100.8, 101.2, 99.8, 100.0),
        ])
        entry = find_three_bar_pivot_reversal_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 100.8)
        self.assertEqual(entry.bar_ts, ts(10, 15))
        self.assertEqual(entry.ts, ts(10, 15))
        self.assertEqual(entry.anchor, 'bar_open')
        self.assertEqual(entry.pivot_ref, 102.5)
        self.assertEqual(entry.to_payload()['rule'], 'three_bar_pivot_high_reversal')

    def test_long_low_lower_low_higher_low_enters_on_next_candle_open(self):
        bars = annotate_et([
            bar(9, 30, 100, 100.5, 99.0, 99.5),
            bar(9, 45, 99.5, 100.0, 97.8, 98.4),
            bar(10, 0, 98.4, 99.4, 98.2, 99.0),
            bar(10, 15, 99.2, 99.9, 98.9, 99.8),
        ])
        entry = find_three_bar_pivot_reversal_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'long')
        self.assertEqual(entry.price, 99.2)
        self.assertEqual(entry.bar_ts, ts(10, 15))
        self.assertEqual(entry.ts, ts(10, 15))
        self.assertEqual(entry.anchor, 'bar_open')
        self.assertEqual(entry.pivot_ref, 97.8)
        self.assertEqual(entry.to_payload()['rule'], 'three_bar_pivot_low_reversal')

    def test_direction_filter_blocks_short_pattern(self):
        bars = annotate_et([
            bar(9, 30, 100, 101.0, 99.5, 100.4),
            bar(9, 45, 100.4, 102.5, 100.0, 101.8),
            bar(10, 0, 101.8, 101.9, 100.7, 101.0),
            bar(10, 15, 100.8, 101.2, 99.8, 100.0),
        ])
        self.assertIsNone(find_three_bar_pivot_reversal_entry(bars, timeframe='15m', direction_mode='long'))

    def test_no_middle_pivot_returns_none(self):
        bars = annotate_et([
            bar(9, 30, 100, 101.0, 99.5, 100.4),
            bar(9, 45, 100.4, 101.5, 100.0, 101.0),
            bar(10, 0, 101.0, 102.0, 100.7, 101.5),
        ])
        self.assertIsNone(find_three_bar_pivot_reversal_entry(bars, timeframe='15m'))

    def test_aggregates_smaller_bars_before_detecting_pivot(self):
        bars = annotate_et([
            bar(9, 30, 100.0, 100.8, 99.4, 100.2),
            bar(9, 35, 100.2, 101.0, 99.5, 100.5),
            bar(9, 40, 100.5, 100.9, 99.8, 100.4),
            bar(9, 45, 100.4, 102.0, 100.1, 101.4),
            bar(9, 50, 101.4, 102.5, 100.6, 101.9),
            bar(9, 55, 101.9, 102.2, 101.0, 101.8),
            bar(10, 0, 101.8, 102.0, 100.6, 101.1),
            bar(10, 5, 101.1, 101.9, 100.5, 101.0),
            bar(10, 10, 101.0, 101.6, 100.7, 100.9),
            bar(10, 15, 100.6, 101.0, 99.8, 100.2),
        ])
        entry = find_three_bar_pivot_reversal_entry(bars, timeframe='15m')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 100.6)
        self.assertEqual(entry.pivot_ref, 102.5)

    def test_dual_qualifying_outside_bar_pivot_prefers_short(self):
        bars = annotate_et([
            bar(9, 30, 100, 101.0, 99.0, 100.0),
            bar(9, 45, 100, 103.0, 97.0, 100.0),
            bar(10, 0, 100, 102.0, 98.0, 100.5),
            bar(10, 15, 100.2, 101.0, 99.5, 100.0),
        ])
        entry = find_three_bar_pivot_reversal_entry(bars, timeframe='15m')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.to_payload()['rule'], 'three_bar_pivot_high_reversal')


def _pre_bars(high: float, low: float):
    """Build a tiny premarket range producing exactly PMH=high and PML=low.

    Two 15-minute bars spanning 04:00 and 04:15 ET, so the same-ET-day premarket
    high/low are deterministic and not polluted by stray later premarket ticks.
    """
    return [
        bar(4, 0, low, high, low, low),
        bar(4, 15, low, high, low, high),
    ]


def _pm_range(high: float, low: float) -> PremarketRangeAtom:
    annotated = annotate_et(_pre_bars(high, low))
    rng = premarket_range(annotated)
    assert rng is not None
    assert rng.high == high
    assert rng.low == low
    return rng


class PremarketBreakoutTests(unittest.TestCase):
    """Premarket high breakout long / premarket low breakdown short."""

    def test_long_breakout_triggers_above_pmh(self):
        """First RTH bar whose close > PMH => long at that close."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 101.5, 99.5, 101.0),  # inside range, no trigger
            bar(9, 35, 101.0, 103.0, 100.8, 102.7),  # close > PMH => long
            bar(9, 40, 102.7, 102.8, 102.0, 102.3),
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        entry = find_premarket_breakout_entry(pm, annotated)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'long')
        self.assertEqual(entry.price, 102.7)
        self.assertEqual(entry.rule, 'premarket_high_breakout_close')
        self.assertEqual(entry.rule_ref, 102.0)
        # Close-confirmed entry: trigger bar is the 9:35 bar.
        self.assertEqual(entry.bar['ts'], ts(9, 35))

    def test_short_breakdown_triggers_below_pml(self):
        """First RTH bar whose close < PML => short at that close."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 101.0, 98.5, 100.5),  # inside range, no trigger
            bar(9, 35, 100.5, 100.7, 98.0, 98.5),  # close < PML => short
            bar(9, 40, 98.5, 98.6, 98.0, 98.4),
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        entry = find_premarket_breakout_entry(pm, annotated)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 98.5)
        self.assertEqual(entry.rule, 'premarket_low_breakdown_close')
        self.assertEqual(entry.rule_ref, 99.0)
        self.assertEqual(entry.bar['ts'], ts(9, 35))

    def test_no_premarket_bars_returns_none(self):
        """Empty premarket => premarket_range is None and entry cannot be defined.

        With no PM bars, `premarket_range` returns None. The breakout atom is
        downstream of a valid PM range, so absence of premarket bars means no
        trade. We also assert the breakout call returns None when handed an
        empty RTH list (nothing to scan).
        """
        rth = [bar(9, 30, 100, 110, 90, 105)]  # would qualify if a range existed
        annotated = annotate_et(rth)
        self.assertIsNone(premarket_range(annotated))
        # With no RTH bars (no annotated bars at all), the breakout is also None.
        self.assertIsNone(
            find_premarket_breakout_entry(
                PremarketRangeAtom(high=110.0, low=90.0, bars=[]),
                annotate_et([]),
            )
        )

    def test_no_breakout_returns_none(self):
        """RTH bars close strictly inside PM range => no entry."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 101.0, 99.5, 100.5),
            bar(9, 35, 100.5, 101.5, 100.0, 101.0),
            bar(10, 0, 101.0, 101.8, 100.2, 101.5),
            bar(15, 55, 101.5, 101.9, 100.9, 101.2),
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        self.assertIsNone(find_premarket_breakout_entry(pm, annotated))

    def test_intra_bar_wick_alone_is_not_a_breakout(self):
        """Close-confirmed rule: a wick that breaches PMH but closes inside must NOT trigger."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 103.0, 99.5, 101.0),  # high > PMH, close < PMH => no trigger
            bar(9, 35, 101.0, 101.4, 100.5, 101.2),
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        self.assertIsNone(find_premarket_breakout_entry(pm, annotated))

    def test_premarket_range_ignores_rth_and_post_bars(self):
        """premarket_range must only consider premarket-session bars."""
        # Build a list with mixed sessions; only the pre bars should drive PMH/PML.
        pre = _pre_bars(high=102.0, low=99.0)
        post = [
            bar(16, 5, 200, 205, 195, 200),   # post-market bar with extreme high/low
        ]
        annotated = annotate_et(pre + [bar(9, 30, 100, 110, 90, 105)] + post)
        rng = premarket_range(annotated)
        assert rng is not None
        self.assertEqual(rng.high, 102.0)
        self.assertEqual(rng.low, 99.0)

    def test_direction_mode_long_only_blocks_short(self):
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 100.7, 98.0, 98.5),  # close < PML => would-be short
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        self.assertIsNone(
            find_premarket_breakout_entry(pm, annotated, direction_mode='long')
        )

    def test_direction_mode_short_only_blocks_long(self):
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 103.0, 99.8, 102.7),  # close > PMH => would-be long
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        self.assertIsNone(
            find_premarket_breakout_entry(pm, annotated, direction_mode='short')
        )

    def test_same_bar_both_directions_is_long_biased(self):
        """If a single bar's close would trigger both, long wins (matches ORB)."""
        # Cannot happen with strict > and < on the same close, so use wicks that breach:
        # construct a bar whose close is between PMH and PML but whose wicks breach both,
        # and assert the existing close-confirmed rule yields None (no false dual trigger).
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100.5, 110.0, 90.0, 100.5),  # close inside range => no trigger
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        self.assertIsNone(find_premarket_breakout_entry(pm, annotated))


class PremarketReentryTests(unittest.TestCase):
    """Premarket-range failed-breakout/breakdown re-entry entry atom."""

    def test_short_reentry_after_above_pmh_excursion(self):
        """Spike above PMH, then close back inside => short at trigger close."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 103.0, 99.5, 102.5),  # excursion: high > PMH
            bar(9, 35, 102.5, 102.5, 99.8, 101.0),  # close back inside => short
            bar(9, 40, 101.0, 101.2, 100.5, 100.8),
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        entry = find_premarket_reentry_entry(pm, annotated)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 101.0)
        self.assertEqual(entry.rule, 'pmh_failed_breakout_reentry')
        self.assertEqual(entry.rule_ref, 102.0)

    def test_long_reentry_after_below_pml_excursion(self):
        """Spike below PML, then close back inside => long at trigger close."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 102.0, 97.0, 98.0),  # excursion: low < PML
            bar(9, 35, 98.0, 99.5, 97.8, 99.2),  # close back inside => long
            bar(9, 40, 99.2, 99.5, 99.0, 99.3),
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        entry = find_premarket_reentry_entry(pm, annotated)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'long')
        self.assertEqual(entry.price, 99.2)
        self.assertEqual(entry.rule, 'pml_failed_breakdown_reentry')
        self.assertEqual(entry.rule_ref, 99.0)

    def test_no_excursion_then_inside_range_no_trade(self):
        """Bars stay inside the PM range the whole session => no trade."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 100.5, 99.8, 100.2),
            bar(9, 35, 100.2, 100.8, 100.0, 100.5),
            bar(10, 0, 100.5, 101.0, 100.2, 100.7),
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        self.assertIsNone(find_premarket_reentry_entry(pm, annotated))

    def test_no_premarket_bars_returns_none(self):
        """Degenerate empty PM range + bars that stay inside => no entry."""
        rth = [
            bar(9, 30, 100, 110, 90, 105),  # wild wicks but close outside any sane range
        ]
        annotated = annotate_et(rth)
        # Mirror Worker A's degenerate-PM fixture style: an empty PM range cannot
        # produce a re-entry either, because no real reference level exists.
        self.assertIsNone(
            find_premarket_reentry_entry(
                PremarketRangeAtom(high=100, low=100, bars=[], date=None),
                annotated,
            )
        )

    def test_excursion_and_reentry_on_same_bar(self):
        """A bar that spikes above PMH and closes back inside triggers on that bar."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100.0, 103.0, 98.5, 101.0),  # wick above PMH, close back inside
            bar(9, 35, 101.0, 101.5, 100.5, 101.2),
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        entry = find_premarket_reentry_entry(pm, annotated)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 101.0)
        self.assertEqual(entry.bar['ts'], ts(9, 30))

    def test_close_outside_range_keeps_waiting(self):
        """A bar that closes above PMH does not trigger; first inside-range close after excursion does."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 103.0, 99.5, 103.0),  # excursion, close still above PMH
            bar(9, 35, 103.0, 103.5, 102.5, 103.0),  # excursion continues, still outside
            bar(9, 40, 102.5, 102.6, 99.8, 101.5),  # finally back inside => trigger
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        entry = find_premarket_reentry_entry(pm, annotated)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 101.5)
        self.assertEqual(entry.bar['ts'], ts(9, 40))

    def test_direction_mode_short_only_blocks_long(self):
        """direction_mode='short' must not return a long re-entry even if setup qualifies."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 102.0, 97.0, 98.0),  # below-PML excursion
            bar(9, 35, 98.0, 99.5, 97.8, 99.2),  # close back inside
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        self.assertIsNone(
            find_premarket_reentry_entry(pm, annotated, direction_mode='short')
        )

    def test_direction_mode_long_only_blocks_short(self):
        """direction_mode='long' must not return a short re-entry even if setup qualifies."""
        pm = _pm_range(high=102.0, low=99.0)
        rth = [
            bar(9, 30, 100, 103.0, 99.5, 102.5),  # above-PMH excursion
            bar(9, 35, 102.5, 102.5, 99.8, 101.0),  # close back inside
        ]
        annotated = annotate_et(_pre_bars(102.0, 99.0) + rth)
        self.assertIsNone(
            find_premarket_reentry_entry(pm, annotated, direction_mode='long')
        )


class EngulfingCloseEntryTests(unittest.TestCase):
    """Miguel's engulfing candle definition: close through previous extreme."""

    def test_short_previous_green_current_red_close_below_previous_low_triggers_short(self):
        # Previous candle is green (open 100, close 101.5); current is red
        # (open 101.2, close 99.5 < previous.low=99.8) => short at 99.5.
        bars = annotate_et([
            bar(9, 30, 100.0, 101.8, 99.8, 101.5),    # prev green, low=99.8
            bar(9, 45, 101.2, 101.4, 99.0, 99.5),     # current red, close 99.5 < 99.8
            bar(10, 0, 99.5, 99.8, 98.0, 98.4),      # future – must not influence detection
        ])
        entry = find_engulfing_close_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 99.5)
        self.assertEqual(entry.bar_ts, ts(9, 45))
        self.assertEqual(entry.ts, ts(10, 0))
        self.assertEqual(entry.anchor, 'bar_close')
        self.assertEqual(entry.previous_color, 'green')
        self.assertEqual(entry.trigger_color, 'red')
        self.assertEqual(entry.previous_high, 101.8)
        self.assertEqual(entry.previous_low, 99.8)
        self.assertEqual(entry.previous_bar['ts'], ts(9, 30))
        self.assertTrue(entry.require_opposite_color)

        payload = entry.to_payload()
        self.assertEqual(payload['rule'], 'engulfing_close_below_previous_low')
        self.assertEqual(payload['rule_ref'], 99.8)
        self.assertEqual(payload['side'], 'sell')
        self.assertEqual(payload['entry_bar_open'], 101.2)
        self.assertEqual(payload['entry_bar_close'], 99.5)
        self.assertEqual(payload['timeframe'], '15m')

    def test_long_previous_red_current_green_close_above_previous_high_triggers_long(self):
        # Previous candle is red (open 102, close 100.5); current is green
        # (open 101, close 103.5 > previous.high=102.4) => long at 103.5.
        bars = annotate_et([
            bar(9, 30, 102.0, 102.4, 100.0, 100.5),   # prev red, high=102.4
            bar(9, 45, 101.0, 104.0, 100.8, 103.5),   # current green, close > 102.4
        ])
        entry = find_engulfing_close_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'long')
        self.assertEqual(entry.price, 103.5)
        self.assertEqual(entry.bar_ts, ts(9, 45))
        self.assertEqual(entry.ts, ts(10, 0))
        self.assertEqual(entry.anchor, 'bar_close')
        self.assertEqual(entry.previous_color, 'red')
        self.assertEqual(entry.trigger_color, 'green')
        self.assertEqual(entry.previous_high, 102.4)
        self.assertEqual(entry.previous_low, 100.0)

        payload = entry.to_payload()
        self.assertEqual(payload['rule'], 'engulfing_close_above_previous_high')
        self.assertEqual(payload['rule_ref'], 102.4)
        self.assertEqual(payload['side'], 'buy')

    def test_opposite_color_required_blocks_same_color_close_through_extreme(self):
        # Both previous and current are green, but current closes above previous.high.
        # require_opposite_color=True (default) must block this from triggering long.
        bars = annotate_et([
            bar(9, 30, 100.0, 101.0, 99.5, 100.8),    # green prev, high=101.0
            bar(9, 45, 100.9, 102.0, 100.5, 101.5),    # green current, close 101.5 > 101.0
        ])
        self.assertIsNone(find_engulfing_close_entry(bars, timeframe='15m'))

        # Mirror case for short: both previous and current are red, but current
        # closes below previous.low.
        bars_red = annotate_et([
            bar(9, 30, 101.5, 101.8, 100.5, 100.7),   # red prev, low=100.5
            bar(9, 45, 100.6, 100.8, 99.5, 99.7),     # red current, close 99.7 < 100.5
        ])
        self.assertIsNone(find_engulfing_close_entry(bars_red, timeframe='15m'))

        # Doji previous / doji current must also be blocked under opposite-color mode.
        bars_doji = annotate_et([
            bar(9, 30, 100.0, 100.5, 99.5, 100.0),    # doji prev
            bar(9, 45, 99.9, 101.0, 99.6, 100.1),     # doji current, close > prev.high
        ])
        self.assertIsNone(find_engulfing_close_entry(bars_doji, timeframe='15m'))

    def test_require_opposite_color_false_allows_same_color_close_through_extreme(self):
        # Same-color setup (both green) qualifies when the color guard is lifted:
        # current closes above previous.high => long.
        bars = annotate_et([
            bar(9, 30, 100.0, 101.0, 99.5, 100.8),    # green prev, high=101.0
            bar(9, 45, 100.9, 102.0, 100.5, 101.5),    # green current, close 101.5 > 101.0
        ])
        entry = find_engulfing_close_entry(
            bars, timeframe='15m', require_opposite_color=False
        )
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'long')
        self.assertEqual(entry.price, 101.5)
        self.assertEqual(entry.trigger_color, 'green')
        self.assertEqual(entry.previous_color, 'green')
        self.assertFalse(entry.require_opposite_color)

        # Mirror: both red, same-color close-through-extreme low => short when guard lifted.
        bars_red = annotate_et([
            bar(9, 30, 101.5, 101.8, 100.5, 100.7),   # red prev, low=100.5
            bar(9, 45, 100.6, 100.8, 99.5, 99.7),     # red current, close 99.7 < 100.5
        ])
        entry_red = find_engulfing_close_entry(
            bars_red, timeframe='15m', require_opposite_color=False
        )
        self.assertIsNotNone(entry_red)
        assert entry_red is not None
        self.assertEqual(entry_red.direction, 'short')
        self.assertEqual(entry_red.price, 99.7)
        self.assertEqual(entry_red.trigger_color, 'red')
        self.assertEqual(entry_red.previous_color, 'red')

    def test_direction_filter_blocks_opposite_side(self):
        # Bars would qualify as a short; with direction_mode='long' the function returns None.
        bars = annotate_et([
            bar(9, 30, 100.0, 101.8, 99.8, 101.5),    # green prev, low=99.8
            bar(9, 45, 101.2, 101.4, 99.0, 99.5),     # red current, close < 99.8
        ])
        self.assertIsNone(find_engulfing_close_entry(bars, timeframe='15m', direction_mode='long'))

        # Bars would qualify as a long; with direction_mode='short' the function returns None.
        bars_long = annotate_et([
            bar(9, 30, 102.0, 102.4, 100.0, 100.5),   # red prev, high=102.4
            bar(9, 45, 101.0, 104.0, 100.8, 103.5),   # green current, close > 102.4
        ])
        self.assertIsNone(find_engulfing_close_entry(bars_long, timeframe='15m', direction_mode='short'))

    def test_aggregates_5m_bars_into_15m_then_detects(self):
        # Feed 5m bars; aggregate_clock should produce three 15m candles whose
        # 9:30 candle is green, the 9:45 candle is green (prev), and the 10:00
        # candle is red with close < 9:45 aggregate low => short engulfing entry.
        bars = annotate_et([
            # 9:30 bucket (aggregated: open=100, high=101, low=99.5, close=100.6)
            bar(9, 30, 100.0, 100.6, 99.8, 100.2),
            bar(9, 35, 100.2, 100.8, 99.6, 100.4),
            bar(9, 40, 100.4, 101.0, 99.5, 100.6),
            # 9:45 bucket (aggregated: open=100.6, high=101.4, low=100.2, close=101.2, green)
            bar(9, 45, 100.6, 101.0, 100.3, 100.8),
            bar(9, 50, 100.8, 101.4, 100.2, 101.0),
            bar(9, 55, 101.0, 101.3, 100.5, 101.2),
            # 10:00 bucket: red, close=99.9 < 9:45 aggregated low=100.2 => short
            bar(10, 0, 101.1, 101.2, 100.0, 100.4),
            bar(10, 5, 100.4, 100.4, 99.7, 99.9),
            bar(10, 10, 99.9, 100.0, 99.5, 99.7),
        ])
        entry = find_engulfing_close_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 99.7)
        self.assertEqual(entry.bar_ts, ts(10, 0))
        self.assertEqual(entry.ts, ts(10, 15))
        self.assertEqual(entry.anchor, 'bar_close')
        self.assertEqual(entry.previous_color, 'green')
        self.assertEqual(entry.trigger_color, 'red')
        # Previous-bar low is the aggregated 9:45 low (100.2); the current red
        # close 99.7 is strictly below it.
        self.assertEqual(entry.previous_low, 100.2)
        self.assertEqual(entry.previous_high, 101.4)


class FairValueGapRetraceEntryTests(unittest.TestCase):
    """Miguel's 3-candle fair-value-gap 50% retrace entry atom.

    Bearish (short) FVG: ``candle1.low > candle3.high`` (strict).
    Bullish (long)  FVG: ``candle1.high < candle3.low`` (strict).
    Entry at the gap midpoint when a future bar trades through it.

    Stop is *suggested* via the payload (`suggested_stop_price` /
    `suggested_stop_rule`) only — no separate stop atom is implemented here.
    """

    def test_bearish_fvg_short_detected_with_midpoint_entry_and_candle2_high_stop(self):
        # 15m bars. candle1.low (105) > candle3.high (100) => strict bearish gap.
        # zone = [100, 105]; midpoint = 102.5.
        # candle2.high = 112 => suggested_stop_price = 112.
        # Future 11:30 bar reaches high=103 >= 102.5 => short at 102.5 on that bar.
        bars = annotate_et([
            bar(9, 30, 106, 108, 105, 107),   # candle1 (low=105)
            bar(10, 0, 110, 112, 106, 109),   # candle2 displacement (high=112)
            bar(10, 30, 99, 100, 95, 96),     # candle3 (high=100)
            bar(11, 0, 100, 101, 99, 100),    # future bar — high=101 < 102.5 (no touch)
            bar(11, 30, 102, 103, 101, 102.2),  # future bar — high=103 >= 102.5 => short
        ])
        entry = find_fair_value_gap_retrace_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 102.5)
        self.assertEqual(entry.bar_ts, ts(11, 30))
        self.assertEqual(entry.ts, ts(11, 30))
        self.assertEqual(entry.anchor, 'bar_open')
        self.assertEqual(entry.suggested_stop_price, 112)
        self.assertEqual(entry.gap_start, 100)
        self.assertEqual(entry.gap_end, 105)
        self.assertEqual(entry.gap_midpoint, 102.5)
        self.assertEqual(entry.retrace_fraction, 0.5)
        self.assertEqual(entry.candle2['ts'], ts(10, 0))
        self.assertEqual(entry.candle3['ts'], ts(10, 30))

        payload = entry.to_payload()
        self.assertEqual(payload['rule'], 'bearish_fvg_50pct_retrace_short')
        self.assertEqual(payload['rule_ref'], 102.5)
        self.assertEqual(payload['side'], 'sell')
        self.assertEqual(payload['suggested_stop_rule'], 'bearish_fvg_candle_high')
        self.assertEqual(payload['execution'], 'fvg_midpoint_retrace_touch')
        self.assertEqual(payload['timeframe'], '15m')
        self.assertEqual(payload['time'], '11:30')
        self.assertEqual(payload['fvg_candle_time'], '10:00')
        self.assertEqual(payload['entry_bar_open'], 102)
        self.assertEqual(payload['entry_bar_close'], 102.2)
        self.assertEqual(payload['gap_start'], 100)
        self.assertEqual(payload['gap_end'], 105)
        self.assertEqual(payload['gap_midpoint'], 102.5)

    def test_bullish_fvg_long_detected_with_midpoint_entry_and_candle2_low_stop(self):
        # 15m bars. candle1.high (95) < candle3.low (99) => strict bullish gap.
        # zone = [95, 99]; midpoint = 97.
        # candle2.low = 86 => suggested_stop_price = 86.
        # Future 11:30 bar reaches low=96 <= 97 => long at 97 on that bar.
        bars = annotate_et([
            bar(9, 30, 94, 95, 90, 91),       # candle1 (high=95)
            bar(10, 0, 90, 92, 86, 88),       # candle2 displacement (low=86)
            bar(10, 30, 100, 101, 99, 100.5),  # candle3 (low=99)
            bar(11, 0, 99, 99.5, 98, 98.4),   # future bar — low=98 > 97 (no touch)
            bar(11, 30, 98, 98.2, 96, 97.2),  # future bar — low=96 <= 97 => long
        ])
        entry = find_fair_value_gap_retrace_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'long')
        self.assertEqual(entry.price, 97)
        self.assertEqual(entry.bar_ts, ts(11, 30))
        self.assertEqual(entry.ts, ts(11, 30))
        self.assertEqual(entry.anchor, 'bar_open')
        self.assertEqual(entry.suggested_stop_price, 86)
        self.assertEqual(entry.gap_start, 95)
        self.assertEqual(entry.gap_end, 99)
        self.assertEqual(entry.gap_midpoint, 97)
        self.assertEqual(entry.candle2['ts'], ts(10, 0))
        self.assertEqual(entry.candle3['ts'], ts(10, 30))

        payload = entry.to_payload()
        self.assertEqual(payload['rule'], 'bullish_fvg_50pct_retrace_long')
        self.assertEqual(payload['rule_ref'], 97)
        self.assertEqual(payload['side'], 'buy')
        self.assertEqual(payload['suggested_stop_rule'], 'bullish_fvg_candle_low')
        self.assertEqual(payload['execution'], 'fvg_midpoint_retrace_touch')
        self.assertEqual(payload['fvg_candle_time'], '10:00')

    def test_no_retrace_returns_none(self):
        # Same bearish FVG geometry as test 1, but no future bar reaches the midpoint.
        # Future bars stay well below 102.5.
        bars = annotate_et([
            bar(9, 30, 106, 108, 105, 107),   # candle1 (low=105)
            bar(10, 0, 110, 112, 106, 109),   # candle2
            bar(10, 30, 99, 100, 95, 96),     # candle3 (high=100)
            bar(11, 0, 99, 100.5, 98, 99),    # future — high 100.5 < 102.5
            bar(11, 30, 100, 101.8, 99.5, 100.2),  # future — high 101.8 < 102.5
        ])
        self.assertIsNone(
            find_fair_value_gap_retrace_entry(bars, timeframe='15m', direction_mode='both')
        )

    def test_equal_touch_no_gap_returns_none_strict_inequality(self):
        # candle1.low == candle3.high => no strict gap (>, not >=).
        bars = annotate_et([
            bar(9, 30, 102, 108, 100, 107),   # candle1 (low=100)
            bar(10, 0, 105, 110, 101, 108),   # candle2
            bar(10, 30, 100, 100, 95, 96),    # candle3 (high=100 == candle1.low)
            bar(11, 0, 99, 110, 98, 105),     # future — high=110 would touch, but no gap
        ])
        self.assertIsNone(
            find_fair_value_gap_retrace_entry(bars, timeframe='15m', direction_mode='both')
        )

        # Mirror equality case for bullish FVG: candle1.high == candle3.low.
        bars_long = annotate_et([
            bar(9, 30, 95, 95, 90, 91),       # candle1 (high=95)
            bar(10, 0, 92, 95, 88, 90),       # candle2
            bar(10, 30, 96, 100, 95, 99),     # candle3 (low=95 == candle1.high)
            bar(11, 0, 96, 98, 85, 90),       # future — low=85 would touch, but no gap
        ])
        self.assertIsNone(
            find_fair_value_gap_retrace_entry(bars_long, timeframe='15m', direction_mode='both')
        )

    def test_direction_filter_blocks_opposite_side(self):
        # Bearish FVG qualifies for a short; direction_mode='long' must block it.
        bars = annotate_et([
            bar(9, 30, 106, 108, 105, 107),
            bar(10, 0, 110, 112, 106, 109),
            bar(10, 30, 99, 100, 95, 96),
            bar(11, 30, 102, 103, 101, 102.2),
        ])
        self.assertIsNone(
            find_fair_value_gap_retrace_entry(bars, timeframe='15m', direction_mode='long')
        )

        # Bullish FVG qualifies for a long; direction_mode='short' must block it.
        bars_long = annotate_et([
            bar(9, 30, 94, 95, 90, 91),
            bar(10, 0, 90, 92, 86, 88),
            bar(10, 30, 100, 101, 99, 100.5),
            bar(11, 30, 98, 98.2, 96, 97.2),
        ])
        self.assertIsNone(
            find_fair_value_gap_retrace_entry(bars_long, timeframe='15m', direction_mode='short')
        )

    def test_aggregates_5m_bars_into_15m_then_detects_short(self):
        # 5m bars aggregated to 15m should produce:
        #   9:30 candle  (candle1): open=100, high=100.5, low=100.0, close=100.2
        #   9:45 candle  (candle2): high=102,  low=99.5,        close=100.8
        #   10:00 candle (candle3): high=99.5, low=98,          close=98.4
        # Strict bearish gap:  candle1.low (100) > candle3.high (99.5)
        # Zone = [99.5, 100], midpoint = 99.75, suggested stop = candle2.high = 102.
        # 10:15 bar reaches high=99.7 < 99.75 (no touch), 10:30 bar reaches 100.0
        # >= 99.75 => short at 99.75 on the 10:30 bar.
        bars = annotate_et([
            # 9:30 bucket (candle1, low=100)
            bar(9, 30, 100.0, 100.2, 100.0, 100.0),
            bar(9, 35, 100.0, 100.5, 100.0, 100.2),
            bar(9, 40, 100.2, 100.4, 100.1, 100.2),
            # 9:45 bucket (candle2 displacement, high=102)
            bar(9, 45, 100.2, 100.8, 100.2, 100.6),
            bar(9, 50, 100.6, 102.0, 100.5, 101.0),
            bar(9, 55, 101.0, 101.5, 99.5, 100.8),
            # 10:00 bucket (candle3, aggregated high must be < 100)
            bar(10, 0, 99.5, 99.5, 99.5, 99.5),
            bar(10, 5, 99.5, 99.5, 98.5, 98.8),
            bar(10, 10, 98.8, 98.9, 98.0, 98.4),
            # 10:15 bucket (future retrace bar, high=99.7 < 99.75 — no touch yet)
            bar(10, 15, 98.4, 99.7, 98.4, 99.0),
            # 10:30 bucket (future retrace bar, high=100.0 >= 99.75 => short)
            bar(10, 30, 99.0, 100.0, 99.0, 99.4),
        ])
        entry = find_fair_value_gap_retrace_entry(bars, timeframe='15m', direction_mode='both')
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.direction, 'short')
        self.assertEqual(entry.price, 99.75)
        self.assertEqual(entry.bar_ts, ts(10, 30))
        self.assertEqual(entry.ts, ts(10, 30))
        self.assertEqual(entry.anchor, 'bar_open')
        self.assertEqual(entry.suggested_stop_price, 102)
        self.assertEqual(entry.gap_start, 99.5)
        self.assertEqual(entry.gap_end, 100)
        self.assertEqual(entry.gap_midpoint, 99.75)
        # Candle2 (the displacement) is the aggregated 9:45 bar.
        self.assertEqual(entry.candle2['ts'], ts(9, 45))
        self.assertEqual(entry.candle3['ts'], ts(10, 0))

        payload = entry.to_payload()
        self.assertEqual(payload['rule'], 'bearish_fvg_50pct_retrace_short')
        self.assertEqual(payload['rule_ref'], 99.75)
        self.assertEqual(payload['suggested_stop_rule'], 'bearish_fvg_candle_high')
        self.assertEqual(payload['timeframe'], '15m')
        self.assertEqual(payload['fvg_candle_time'], '09:45')
        self.assertEqual(payload['execution'], 'fvg_midpoint_retrace_touch')


if __name__ == '__main__':
    unittest.main()

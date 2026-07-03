from __future__ import annotations

import unittest

from trading_atoms.reentries import collect_reentry_trades_for_day


def bar(ts: int) -> dict:
    return {'ts': ts, 'time': ts, 'open': 1, 'high': 2, 'low': 0, 'close': 1, 'volume': 100}


class ReentryCollectionTests(unittest.TestCase):
    def test_collects_initial_trade_plus_bounded_reentries_after_prior_exit(self):
        day_bars = [bar(ts) for ts in [1, 2, 3, 4, 5, 6, 7]]
        seen_starts: list[int] = []

        def run_once(candidate_bars: list[dict]) -> dict | None:
            if len(candidate_bars) < 2:
                return None
            seen_starts.append(candidate_bars[0]['ts'])
            entry_ts = candidate_bars[0]['ts']
            exit_ts = candidate_bars[1]['ts']
            return {
                'date': '2026-07-01',
                'day': 'Wed Jul 01, 2026',
                'entry_ts': entry_ts,
                'entry_time': str(entry_ts),
                'exit_ts': exit_ts,
                'exit_time': str(exit_ts),
                'entry': 100.0,
                'exit': 101.0,
                'stop_price': 99.0,
                'pnl': 1.0,
                'direction': 'long',
            }

        trades = collect_reentry_trades_for_day(day_bars, run_once, max_reentries=2)

        self.assertEqual([t['entry_ts'] for t in trades], [1, 3, 5])
        self.assertEqual([t['reentry_index'] for t in trades], [0, 1, 2])
        self.assertEqual([t['reentry_label'] for t in trades], ['initial', 're-entry 1', 're-entry 2'])
        self.assertEqual(seen_starts, [1, 3, 5])
        self.assertEqual(len({t['trade_id'] for t in trades}), 3)

    def test_zero_reentries_keeps_existing_one_trade_per_day_behavior(self):
        day_bars = [bar(ts) for ts in [1, 2, 3, 4]]
        calls = 0

        def run_once(candidate_bars: list[dict]) -> dict | None:
            nonlocal calls
            calls += 1
            return {
                'date': '2026-07-01',
                'entry_ts': candidate_bars[0]['ts'],
                'exit_ts': candidate_bars[1]['ts'],
                'entry': 100.0,
                'exit': 99.0,
                'stop_price': 99.0,
                'pnl': -1.0,
                'direction': 'long',
            }

        trades = collect_reentry_trades_for_day(day_bars, run_once, max_reentries=0)

        self.assertEqual(len(trades), 1)
        self.assertEqual(calls, 1)
        self.assertEqual(trades[0]['reentry_label'], 'initial')


if __name__ == '__main__':
    unittest.main()

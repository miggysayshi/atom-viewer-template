from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading_atoms.performance import enrich_trade_outcome, summarize_normalized_trades


class SizedSummaryTests(unittest.TestCase):
    def test_enrich_trade_outcome_adds_position_sized_pnl_and_r(self):
        trade = {'entry': 100.0, 'stop_price': 98.0, 'pnl': 3.0, 'direction': 'long'}

        enrich_trade_outcome(trade, risk_dollars=100)

        self.assertEqual(trade['risk_per_share'], 2.0)
        self.assertEqual(trade['size'], 50)
        self.assertEqual(trade['risk_dollars'], 100.0)
        self.assertEqual(trade['pnl_per_share'], 3.0)
        self.assertEqual(trade['pnl_dollars'], 150.0)
        self.assertEqual(trade['r_ratio'], 1.5)

    def test_summarize_trades_uses_sized_pnl_not_raw_stock_move(self):
        trades = [
            enrich_trade_outcome({
                'entry': 100.0,
                'stop_price': 98.0,
                'pnl': 3.0,  # +$3/share, size 50 => +$150, +1.5R
                'direction': 'long',
                'exit_reason': 'market_close',
            }),
            enrich_trade_outcome({
                'entry': 50.0,
                'stop_price': 55.0,
                'pnl': -5.0,  # -$5/share, size 20 => -$100, -1.0R
                'direction': 'short',
                'exit_reason': 'stop',
            }),
        ]

        summary = summarize_normalized_trades(
            trades,
            symbol='SPY',
            strategy='larry_williams_3bar',
            strategy_tf='15m',
            direction_mode='both',
            stop_mode='one_bar',
            or_minutes=15,
            fetch_interval='5m',
            bars_1m_trade_count=0,
            total_days=2,
            skipped=0,
        )

        self.assertEqual(summary['total_pnl'], 50.0)
        self.assertEqual(summary['avg_pnl'], 25.0)
        self.assertEqual(summary['avg_win'], 150.0)
        self.assertEqual(summary['avg_loss'], -100.0)
        self.assertEqual(summary['best_trade'], 150.0)
        self.assertEqual(summary['worst_trade'], -100.0)
        self.assertEqual(summary['total_r'], 0.5)
        self.assertEqual(summary['avg_r'], 0.25)
        self.assertEqual(summary['best_r'], 1.5)
        self.assertEqual(summary['worst_r'], -1.0)


if __name__ == '__main__':
    unittest.main()

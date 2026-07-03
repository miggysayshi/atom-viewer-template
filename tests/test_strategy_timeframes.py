from __future__ import annotations

import re
import unittest
from pathlib import Path

import server
from trading_atoms.entries import normalize_timeframe, timeframe_seconds


EXPECTED_TFS = ['1m', '2m', '3m', '5m', '10m', '15m', '30m', '1h', '4h']


def _select_options(html: str, select_id: str) -> list[str]:
    match = re.search(rf'<select id="{select_id}"[^>]*>(.*?)</select>', html, re.S)
    if not match:
        raise AssertionError(f'missing select #{select_id}')
    return re.findall(r'<option value="([^"]+)"', match.group(1))


class StrategyTimeframeSupportTests(unittest.TestCase):
    def test_all_requested_intraday_timeframes_are_supported(self):
        self.assertEqual([normalize_timeframe(tf) for tf in EXPECTED_TFS], EXPECTED_TFS)
        self.assertEqual(timeframe_seconds('1m'), 60)
        self.assertEqual(timeframe_seconds('2m'), 120)
        self.assertEqual(timeframe_seconds('3m'), 180)
        self.assertEqual(timeframe_seconds('5m'), 300)
        self.assertEqual(timeframe_seconds('10m'), 600)
        self.assertEqual(timeframe_seconds('15m'), 900)
        self.assertEqual(timeframe_seconds('30m'), 1_800)
        self.assertEqual(timeframe_seconds('1h'), 3_600)
        self.assertEqual(timeframe_seconds('4h'), 14_400)

    def test_hour_aliases_normalize_to_canonical_values(self):
        self.assertEqual(normalize_timeframe('1hr'), '1h')
        self.assertEqual(normalize_timeframe('4hr'), '4h')

    def test_yahoo_source_interval_mapping_handles_synthetic_timeframes(self):
        self.assertEqual(server._source_interval_for_strategy_tf('3m'), '1m')
        self.assertEqual(server._source_interval_for_strategy_tf('10m'), '5m')
        self.assertEqual(server._source_interval_for_strategy_tf('4h'), '1h')
        self.assertEqual(server._source_interval_for_strategy_and_risk_tf('15m', '15m', '1m'), '1m')
        self.assertEqual(server._source_interval_for_strategy_and_risk_tf('15m', '1m', '5m'), '1m')
        self.assertEqual(server._source_interval_for_strategy_and_risk_tf('15m', '4h', '30m'), '15m')

    def test_strategy_risk_and_interval_dropdowns_expose_full_intraday_spectrum(self):
        html = Path('orb.html').read_text()
        self.assertEqual(_select_options(html, 'strategyTf'), EXPECTED_TFS)
        self.assertEqual(_select_options(html, 'riskTf'), ['same'] + EXPECTED_TFS)
        self.assertEqual(_select_options(html, 'interval'), EXPECTED_TFS)

    def test_resolution_ribbon_exposes_full_intraday_spectrum(self):
        html = Path('orb.html').read_text()
        resolutions = re.findall(r'data-resolution="([^"]+)"', html)
        self.assertEqual(resolutions, EXPECTED_TFS)


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from stockmarkpred.indicators import atr, ema, macd, relative_volume, rsi, session_vwap_series
from stockmarkpred.models import Bar


def make_bar(index: int, close: float, volume: int = 1000) -> Bar:
    base_time = datetime(2026, 3, 11, 14, 30, tzinfo=UTC)
    return Bar(
        time=base_time + timedelta(minutes=index),
        open=close - 0.02,
        high=close + 0.05,
        low=close - 0.05,
        close=close,
        volume=volume,
    )


class IndicatorTests(unittest.TestCase):
    def test_ema_returns_recent_weighted_average(self) -> None:
        value = ema([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        self.assertIsNotNone(value)
        self.assertGreater(value, 4.0)
        self.assertLess(value, 5.0)

    def test_rsi_handles_uptrend(self) -> None:
        closes = [1.0 + (0.05 * index) for index in range(30)]
        value = rsi(closes, 14)
        self.assertIsNotNone(value)
        self.assertGreater(value, 70.0)

    def test_macd_histogram_positive_for_rising_prices(self) -> None:
        closes = [1.0 + (0.03 * index) for index in range(40)]
        _, _, histogram = macd(closes)
        self.assertIsNotNone(histogram)
        self.assertGreater(histogram, 0.0)

    def test_atr_uses_true_range(self) -> None:
        bars = [make_bar(index, 1.0 + index * 0.02) for index in range(20)]
        value = atr(bars, 14)
        self.assertIsNotNone(value)
        self.assertGreater(value, 0.0)

    def test_session_vwap_tracks_price_series(self) -> None:
        bars = [make_bar(index, 1.0 + index * 0.01, 1000 + index * 50) for index in range(10)]
        values = session_vwap_series(bars)
        self.assertEqual(len(values), len(bars))
        self.assertGreater(values[-1], values[0])

    def test_relative_volume_detects_recent_spike(self) -> None:
        volumes = [1000] * 20 + [4000] * 5
        value = relative_volume(volumes, current_window=5, baseline_window=20)
        self.assertIsNotNone(value)
        self.assertGreater(value, 3.0)


if __name__ == "__main__":
    unittest.main()

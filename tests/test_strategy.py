from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from stockmarkpred.config import Settings
from stockmarkpred.models import Bar, MarketSnapshot
from stockmarkpred.strategy import PennyMomentumStrategy


def make_bar(index: int) -> Bar:
    base = 1.00 + (index * 0.018)
    spike = 0.02 if index >= 25 else 0.0
    close = base + spike
    low = close - 0.03
    high = close + 0.05
    return Bar(
        time=datetime(2026, 3, 11, 14, 30, tzinfo=UTC) + timedelta(minutes=index),
        open=close - 0.01,
        high=high,
        low=low,
        close=close,
        volume=1200 if index < 25 else 3200,
    )


def make_breakout_bar(index: int) -> Bar:
    if index < 15:
        close = 1.08 + (index * 0.003)
        high = close + (0.015 if index == 12 else 0.01)
        low = close - 0.02
        volume = 1500
    elif index < 45:
        close = 1.108 + (((index % 6) - 3) * 0.002)
        high = close + 0.01
        low = close - 0.012
        volume = 1200
    else:
        close = 1.118 + ((index - 45) * 0.004)
        high = close + 0.012
        low = close - 0.012
        volume = 3600

    return Bar(
        time=datetime(2026, 3, 11, 14, 30, tzinfo=UTC) + timedelta(minutes=index),
        open=close - 0.008,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


class StrategyTests(unittest.TestCase):
    def test_extended_momentum_profile_downgrades_to_watch_with_pullback_entry(self) -> None:
        bars = [make_bar(index) for index in range(50)]
        snapshot = MarketSnapshot(
            symbol="TEST",
            last_price=bars[-1].close,
            bid=bars[-1].close - 0.002,
            ask=bars[-1].close + 0.002,
            minute_bar=bars[-1],
            daily_bar=Bar(
                time=bars[-1].time,
                open=1.10,
                high=1.95,
                low=1.08,
                close=bars[-1].close,
                volume=2400000,
            ),
            prev_daily_bar=Bar(
                time=bars[-1].time - timedelta(days=1),
                open=1.00,
                high=1.20,
                low=0.98,
                close=1.12,
                volume=900000,
            ),
        )
        settings = Settings(api_key="demo", api_secret="demo")
        strategy = PennyMomentumStrategy(settings)

        idea = strategy.evaluate(snapshot, bars)

        self.assertIsNotNone(idea)
        assert idea is not None
        self.assertEqual(idea.action, "WATCH")
        self.assertGreaterEqual(idea.score, settings.watch_threshold)
        self.assertLess(idea.entry_price, idea.current_price)
        self.assertGreater(idea.take_profit, idea.entry_price)
        self.assertLess(idea.stop_loss, idea.entry_price)
        self.assertIn("preferred pullback entry", idea.reasons[0])

    def test_fresh_breakout_can_still_emit_buy_with_trigger_entry(self) -> None:
        bars = [make_breakout_bar(index) for index in range(50)]
        snapshot = MarketSnapshot(
            symbol="BRK",
            last_price=bars[-1].close,
            bid=bars[-1].close - 0.0015,
            ask=bars[-1].close + 0.0015,
            minute_bar=bars[-1],
            daily_bar=Bar(
                time=bars[-1].time,
                open=1.03,
                high=1.18,
                low=1.01,
                close=bars[-1].close,
                volume=1800000,
            ),
            prev_daily_bar=Bar(
                time=bars[-1].time - timedelta(days=1),
                open=0.97,
                high=1.02,
                low=0.95,
                close=1.00,
                volume=600000,
            ),
        )
        settings = Settings(api_key="demo", api_secret="demo")
        strategy = PennyMomentumStrategy(settings)

        idea = strategy.evaluate(snapshot, bars)

        self.assertIsNotNone(idea)
        assert idea is not None
        self.assertEqual(idea.action, "BUY")
        self.assertGreaterEqual(idea.entry_price, idea.opening_range_high)
        self.assertLessEqual(idea.entry_price, idea.current_price)
        self.assertGreater(idea.take_profit, idea.entry_price)
        self.assertLess(idea.stop_loss, idea.entry_price)
        self.assertIn("breakout trigger", idea.reasons[0])


if __name__ == "__main__":
    unittest.main()

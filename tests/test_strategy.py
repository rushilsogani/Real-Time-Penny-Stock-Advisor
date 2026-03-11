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


class StrategyTests(unittest.TestCase):
    def test_momentum_profile_generates_buy_or_watch(self) -> None:
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
        self.assertIn(idea.action, {"BUY", "WATCH"})
        self.assertGreaterEqual(idea.score, settings.watch_threshold)
        self.assertGreater(idea.take_profit, idea.entry_price)
        self.assertLess(idea.stop_loss, idea.entry_price)


if __name__ == "__main__":
    unittest.main()

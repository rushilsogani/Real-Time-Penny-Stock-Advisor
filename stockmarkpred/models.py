from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    trade_count: int = 0
    vwap: float | None = None


@dataclass
class MarketSnapshot:
    symbol: str
    last_price: float
    bid: float | None = None
    ask: float | None = None
    minute_bar: Bar | None = None
    daily_bar: Bar | None = None
    prev_daily_bar: Bar | None = None

    @property
    def day_volume(self) -> int:
        return self.daily_bar.volume if self.daily_bar else 0

    @property
    def gap_pct(self) -> float:
        if not self.daily_bar or not self.prev_daily_bar or self.prev_daily_bar.close <= 0:
            return 0.0
        return (
            (self.daily_bar.close - self.prev_daily_bar.close) / self.prev_daily_bar.close
        ) * 100.0

    @property
    def spread_pct(self) -> float | None:
        if self.bid is None or self.ask is None or self.last_price <= 0:
            return None
        return ((self.ask - self.bid) / self.last_price) * 100.0


@dataclass
class TradeIdea:
    symbol: str
    action: str
    score: int
    confidence: int
    current_price: float
    entry_price: float
    stop_loss: float
    take_profit: float
    gap_pct: float
    relative_volume: float
    dollar_volume: float
    vwap: float
    ema9: float
    ema20: float
    rsi14: float
    macd_histogram: float
    atr14: float
    opening_range_high: float
    opening_range_low: float
    generated_at: datetime
    as_of: datetime
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["generated_at"] = self.generated_at.isoformat()
        payload["as_of"] = self.as_of.isoformat()
        return payload

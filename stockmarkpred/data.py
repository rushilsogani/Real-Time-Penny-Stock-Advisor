from __future__ import annotations

import json
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from stockmarkpred.config import Settings
from stockmarkpred.models import Bar, MarketSnapshot


class DataClientError(RuntimeError):
    """Raised when the market-data client cannot complete a request."""


class AlpacaDataClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.settings.base_url}{path}{query}"
        headers = {
            "APCA-API-KEY-ID": self.settings.api_key,
            "APCA-API-SECRET-KEY": self.settings.api_secret,
            "Accept": "application/json",
            "User-Agent": "StockMarkPred/1.0",
        }
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise DataClientError(f"HTTP {exc.code} from Alpaca at {path}: {body}") from exc
        except URLError as exc:
            raise DataClientError(f"Network error reaching Alpaca at {path}: {exc}") from exc

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)

    @classmethod
    def _parse_bar(cls, raw: dict[str, Any]) -> Bar:
        return Bar(
            time=cls._parse_timestamp(raw["t"]),
            open=float(raw["o"]),
            high=float(raw["h"]),
            low=float(raw["l"]),
            close=float(raw["c"]),
            volume=int(raw.get("v", 0) or 0),
            trade_count=int(raw.get("n", 0) or 0),
            vwap=float(raw["vw"]) if raw.get("vw") is not None else None,
        )

    def get_top_movers(self, limit: int) -> list[str]:
        payload = self._request_json(
            "/v1beta1/screener/stocks/movers",
            {"top": limit},
        )
        gainers = payload.get("gainers", [])
        return [item["symbol"].upper() for item in gainers if item.get("symbol")]

    def get_most_actives(self, limit: int) -> list[str]:
        payload = self._request_json(
            "/v1beta1/screener/stocks/most-actives",
            {"by": "volume", "top": limit},
        )
        most_actives = payload.get("most_actives", [])
        return [item["symbol"].upper() for item in most_actives if item.get("symbol")]

    def get_snapshots(self, symbols: list[str]) -> dict[str, MarketSnapshot]:
        if not symbols:
            return {}
        payload = self._request_json(
            "/v2/stocks/snapshots",
            {"symbols": ",".join(symbols), "feed": self.settings.data_feed},
        )
        snapshots: dict[str, MarketSnapshot] = {}
        for symbol, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            latest_trade = raw.get("latestTrade") or {}
            latest_quote = raw.get("latestQuote") or {}
            minute_bar = raw.get("minuteBar")
            daily_bar = raw.get("dailyBar")
            prev_daily_bar = raw.get("prevDailyBar")
            last_price = latest_trade.get("p")
            if last_price is None and minute_bar:
                last_price = minute_bar.get("c")
            if last_price is None and daily_bar:
                last_price = daily_bar.get("c")
            if last_price is None:
                continue

            snapshots[symbol.upper()] = MarketSnapshot(
                symbol=symbol.upper(),
                last_price=float(last_price),
                bid=float(latest_quote["bp"]) if latest_quote.get("bp") is not None else None,
                ask=float(latest_quote["ap"]) if latest_quote.get("ap") is not None else None,
                minute_bar=self._parse_bar(minute_bar) if minute_bar else None,
                daily_bar=self._parse_bar(daily_bar) if daily_bar else None,
                prev_daily_bar=self._parse_bar(prev_daily_bar) if prev_daily_bar else None,
            )
        return snapshots

    def get_intraday_bars(self, symbol: str, limit: int) -> list[Bar]:
        end = datetime.now(UTC)
        start = end - timedelta(days=2)
        payload = self._request_json(
            f"/v2/stocks/{symbol}/bars",
            {
                "timeframe": "1Min",
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z"),
                "limit": limit,
                "adjustment": "raw",
                "feed": self.settings.data_feed,
                "sort": "asc",
            },
        )
        bars = payload.get("bars", [])
        return [self._parse_bar(bar) for bar in bars]

    def build_universe(self) -> tuple[list[str], dict[str, MarketSnapshot]]:
        ordered_symbols: OrderedDict[str, None] = OrderedDict()
        for symbol in self.get_top_movers(self.settings.candidate_limit):
            ordered_symbols[symbol] = None
        for symbol in self.get_most_actives(self.settings.candidate_limit):
            ordered_symbols[symbol] = None
        for symbol in self.settings.watchlist:
            ordered_symbols[symbol.upper()] = None

        candidate_symbols = list(ordered_symbols.keys())
        snapshots = self.get_snapshots(candidate_symbols)

        filtered: list[str] = []
        for symbol in candidate_symbols:
            snapshot = snapshots.get(symbol)
            if snapshot is None:
                continue
            last_price = snapshot.last_price
            day_volume = max(snapshot.day_volume, snapshot.minute_bar.volume if snapshot.minute_bar else 0)
            dollar_volume = last_price * day_volume
            if not (self.settings.min_price <= last_price <= self.settings.max_price):
                continue
            if day_volume < self.settings.min_day_volume:
                continue
            if dollar_volume < self.settings.min_dollar_volume:
                continue
            filtered.append(symbol)
        return filtered, snapshots

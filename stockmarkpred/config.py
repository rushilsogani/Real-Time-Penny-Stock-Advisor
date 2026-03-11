from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None and raw != "" else default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None and raw != "" else default


def _get_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return []
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    api_key: str
    api_secret: str
    base_url: str = "https://data.alpaca.markets"
    data_feed: str = "iex"
    poll_seconds: int = 30
    candidate_limit: int = 14
    max_ideas: int = 5
    min_price: float = 0.25
    max_price: float = 5.0
    min_day_volume: int = 300000
    min_dollar_volume: float = 750000.0
    min_relative_volume: float = 1.8
    opening_range_minutes: int = 15
    bar_lookback: int = 120
    score_threshold: int = 70
    watch_threshold: int = 55
    risk_reward: float = 2.2
    atr_stop_multiplier: float = 0.35
    min_stop_atr: float = 0.75
    max_stop_atr: float = 1.5
    watchlist: list[str] = field(default_factory=list)
    log_path: Path = field(default_factory=lambda: Path("outputs/signals.jsonl"))
    verbose: bool = True

    @classmethod
    def load(cls, env_path: Path | None = None) -> "Settings":
        if env_path is not None:
            _load_env_file(env_path)

        api_key = os.getenv("APCA_API_KEY_ID", "").strip()
        api_secret = os.getenv("APCA_API_SECRET_KEY", "").strip()
        if not api_key or not api_secret:
            raise ValueError(
                "APCA_API_KEY_ID and APCA_API_SECRET_KEY must be set in the environment or .env."
            )

        return cls(
            api_key=api_key,
            api_secret=api_secret,
            base_url=os.getenv("APCA_BASE_URL", "https://data.alpaca.markets").rstrip("/"),
            data_feed=os.getenv("APCA_DATA_FEED", "iex").strip() or "iex",
            poll_seconds=max(5, _get_int("POLL_SECONDS", 30)),
            candidate_limit=max(5, _get_int("CANDIDATE_LIMIT", 14)),
            max_ideas=max(1, _get_int("MAX_IDEAS", 5)),
            min_price=max(0.01, _get_float("MIN_PRICE", 0.25)),
            max_price=max(0.10, _get_float("MAX_PRICE", 5.0)),
            min_day_volume=max(1000, _get_int("MIN_DAY_VOLUME", 300000)),
            min_dollar_volume=max(10000.0, _get_float("MIN_DOLLAR_VOLUME", 750000.0)),
            min_relative_volume=max(0.5, _get_float("MIN_RELATIVE_VOLUME", 1.8)),
            opening_range_minutes=max(5, _get_int("OPENING_RANGE_MINUTES", 15)),
            bar_lookback=max(40, _get_int("BAR_LOOKBACK", 120)),
            score_threshold=max(1, _get_int("SCORE_THRESHOLD", 70)),
            watch_threshold=max(1, _get_int("WATCH_THRESHOLD", 55)),
            risk_reward=max(1.0, _get_float("RISK_REWARD", 2.2)),
            atr_stop_multiplier=max(0.05, _get_float("ATR_STOP_MULTIPLIER", 0.35)),
            min_stop_atr=max(0.20, _get_float("MIN_STOP_ATR", 0.75)),
            max_stop_atr=max(0.30, _get_float("MAX_STOP_ATR", 1.5)),
            watchlist=_get_list("WATCHLIST"),
            log_path=Path(os.getenv("LOG_PATH", "outputs/signals.jsonl")),
        )

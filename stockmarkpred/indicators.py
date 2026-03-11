from __future__ import annotations

from statistics import mean

from stockmarkpred.models import Bar


def sma(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if period <= 0 or not values:
        return []
    multiplier = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append((value - result[-1]) * multiplier + result[-1])
    return result


def ema(values: list[float], period: int) -> float | None:
    series = ema_series(values, period)
    return series[-1] if series else None


def slope_pct(values: list[float], lookback: int = 5) -> float | None:
    if lookback < 2 or len(values) < lookback:
        return None
    start = values[-lookback]
    end = values[-1]
    if start == 0:
        return None
    return ((end - start) / start) * 100.0


def rsi(values: list[float], period: int = 14) -> float | None:
    if period <= 0 or len(values) < period + 1:
        return None

    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0.0)
        loss = abs(min(change, 0.0))
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period

    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def macd(
    values: list[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> tuple[float | None, float | None, float | None]:
    if len(values) < slow_period:
        return None, None, None

    fast_ema = ema_series(values, fast_period)
    slow_ema = ema_series(values, slow_period)
    macd_line = [fast - slow for fast, slow in zip(fast_ema, slow_ema)]
    signal_line = ema_series(macd_line, signal_period)
    if not signal_line:
        return None, None, None
    histogram = macd_line[-1] - signal_line[-1]
    return macd_line[-1], signal_line[-1], histogram


def atr(bars: list[Bar], period: int = 14) -> float | None:
    if period <= 0 or len(bars) < period + 1:
        return None

    true_ranges: list[float] = []
    previous_close = bars[0].close
    for bar in bars:
        true_range = max(
            bar.high - bar.low,
            abs(bar.high - previous_close),
            abs(bar.low - previous_close),
        )
        true_ranges.append(true_range)
        previous_close = bar.close

    return mean(true_ranges[-period:])


def session_vwap_series(bars: list[Bar]) -> list[float]:
    cumulative_price_volume = 0.0
    cumulative_volume = 0
    values: list[float] = []
    for bar in bars:
        typical_price = (bar.high + bar.low + bar.close) / 3.0
        cumulative_price_volume += typical_price * bar.volume
        cumulative_volume += bar.volume
        if cumulative_volume <= 0:
            values.append(bar.close)
            continue
        values.append(cumulative_price_volume / cumulative_volume)
    return values


def relative_volume(
    volumes: list[int], current_window: int = 5, baseline_window: int = 20
) -> float | None:
    minimum_needed = current_window + baseline_window
    if current_window <= 0 or baseline_window <= 0 or len(volumes) < minimum_needed:
        return None

    current_volume = sum(volumes[-current_window:])
    baseline_slice = volumes[-minimum_needed:-current_window]
    baseline_average = (sum(baseline_slice) / len(baseline_slice)) * current_window
    if baseline_average <= 0:
        return None
    return current_volume / baseline_average

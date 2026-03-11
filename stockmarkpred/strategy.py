from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from stockmarkpred.config import Settings
from stockmarkpred.indicators import atr, ema_series, macd, relative_volume, rsi, session_vwap_series, slope_pct
from stockmarkpred.models import Bar, MarketSnapshot, TradeIdea

EASTERN = ZoneInfo("America/New_York")
BREAKOUT_ENTRY_BUFFER = 0.0015
MAX_ENTRY_EXTENSION_PCT = 0.0125
MAX_ENTRY_EXTENSION_ATR = 0.35


class PennyMomentumStrategy:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _latest_regular_session(self, bars: list[Bar]) -> list[Bar]:
        if not bars:
            return []
        latest_date = bars[-1].time.astimezone(EASTERN).date()
        session_bars = [
            bar
            for bar in bars
            if bar.time.astimezone(EASTERN).date() == latest_date
            and time(9, 30) <= bar.time.astimezone(EASTERN).time() <= time(16, 0)
        ]
        if session_bars:
            return session_bars
        return [bar for bar in bars if bar.time.astimezone(EASTERN).date() == latest_date]

    def _plan_entry(
        self,
        current_price: float,
        opening_range_high: float,
        ema9: float,
        ema20: float,
        latest_vwap: float,
        atr14: float,
    ) -> tuple[float, bool, str]:
        breakout_trigger = max(opening_range_high * (1.0 + BREAKOUT_ENTRY_BUFFER), ema9)
        chase_buffer = min(breakout_trigger * MAX_ENTRY_EXTENSION_PCT, atr14 * MAX_ENTRY_EXTENSION_ATR)
        actionable_ceiling = breakout_trigger + chase_buffer

        pullback_candidates = sorted(
            {
                value
                for value in [breakout_trigger, ema9, ema20, latest_vwap, opening_range_high]
                if value > 0
            },
            reverse=True,
        )
        preferred_pullback = next(
            (value for value in pullback_candidates if value <= current_price),
            breakout_trigger,
        )

        if current_price < breakout_trigger:
            return breakout_trigger, False, f"Trigger above {breakout_trigger:.4f} is still not broken"

        if current_price <= actionable_ceiling:
            extension_pct = ((current_price - breakout_trigger) / breakout_trigger) * 100.0 if breakout_trigger > 0 else 0.0
            return breakout_trigger, True, f"Price is only {extension_pct:.2f}% above the breakout trigger"

        extension_pct = ((current_price - preferred_pullback) / preferred_pullback) * 100.0 if preferred_pullback > 0 else 0.0
        return (
            preferred_pullback,
            False,
            f"Price is extended {extension_pct:.2f}% above the preferred pullback entry",
        )

    def evaluate(self, snapshot: MarketSnapshot, bars: list[Bar]) -> TradeIdea | None:
        session_bars = self._latest_regular_session(bars)
        minimum_bars = max(30, self.settings.opening_range_minutes + 20)
        if len(session_bars) < minimum_bars:
            return None

        closes = [bar.close for bar in session_bars]
        volumes = [bar.volume for bar in session_bars]

        vwap_series = session_vwap_series(session_bars)
        ema9_series = ema_series(closes, 9)
        ema20_series = ema_series(closes, 20)
        if not vwap_series or not ema9_series or not ema20_series:
            return None

        latest_vwap = vwap_series[-1]
        ema9 = ema9_series[-1]
        ema20 = ema20_series[-1]
        rsi14 = rsi(closes, 14)
        macd_line, signal_line, macd_histogram = macd(closes)
        atr14 = atr(session_bars, 14)
        rel_volume = relative_volume(volumes, current_window=5, baseline_window=20)

        if rsi14 is None or macd_line is None or signal_line is None or macd_histogram is None or atr14 is None:
            return None

        last_bar = session_bars[-1]
        current_price = snapshot.last_price or last_bar.close
        day_volume = max(snapshot.day_volume, sum(volumes))
        dollar_volume = current_price * day_volume
        gap_pct = snapshot.gap_pct
        spread_pct = snapshot.spread_pct
        atr_pct = (atr14 / current_price) * 100.0 if current_price > 0 else 0.0

        opening_range_size = min(self.settings.opening_range_minutes, len(session_bars))
        opening_range_bars = session_bars[:opening_range_size]
        opening_range_high = max(bar.high for bar in opening_range_bars)
        opening_range_low = min(bar.low for bar in opening_range_bars)
        recent_swing_low = min(bar.low for bar in session_bars[-5:])
        closing_strength = 0.5
        if last_bar.high > last_bar.low:
            closing_strength = (last_bar.close - last_bar.low) / (last_bar.high - last_bar.low)

        ema9_slope = slope_pct(ema9_series, 5) or 0.0
        ema20_slope = slope_pct(ema20_series, 5) or 0.0
        above_vwap_pct = ((current_price - latest_vwap) / latest_vwap) * 100.0 if latest_vwap > 0 else 0.0

        score = 35
        reasons: list[str] = []

        if gap_pct >= 8.0:
            score += 12
            reasons.append(f"Gap strength is strong at {gap_pct:.1f}%")
        elif gap_pct >= 3.0:
            score += 8
            reasons.append(f"Gap up of {gap_pct:.1f}% keeps momentum on the tape")
        elif gap_pct < -3.0:
            score -= 8
            reasons.append(f"Negative gap of {gap_pct:.1f}% weakens the setup")

        if current_price > latest_vwap:
            if above_vwap_pct <= 5.5:
                score += 18
                reasons.append(f"Price is above session VWAP by {above_vwap_pct:.1f}%")
            else:
                score += 8
                reasons.append(f"Price is above VWAP but extended by {above_vwap_pct:.1f}%")
        else:
            score -= 22
            reasons.append("Price is below session VWAP")

        if ema9 > ema20:
            score += 15
            reasons.append("9 EMA is above 20 EMA")
        else:
            score -= 14
            reasons.append("9 EMA is below 20 EMA")

        if ema9_slope > 0 and ema20_slope > 0:
            score += 6
            reasons.append("Both trend EMAs are rising")
        elif ema9_slope < 0:
            score -= 6
            reasons.append("Fast EMA slope has turned down")

        if 58.0 <= rsi14 <= 78.0:
            score += 10
            reasons.append(f"RSI is in the momentum zone at {rsi14:.1f}")
        elif 50.0 <= rsi14 < 58.0:
            score += 4
            reasons.append(f"RSI is improving at {rsi14:.1f}")
        elif rsi14 > 84.0:
            score -= 7
            reasons.append(f"RSI is stretched at {rsi14:.1f}")
        else:
            score -= 8
            reasons.append(f"RSI is weak at {rsi14:.1f}")

        if macd_histogram > 0:
            score += 10
            reasons.append(f"MACD histogram is positive at {macd_histogram:.4f}")
        else:
            score -= 7
            reasons.append(f"MACD histogram is negative at {macd_histogram:.4f}")

        if rel_volume is not None and rel_volume >= self.settings.min_relative_volume:
            score += 20
            reasons.append(f"Relative volume is elevated at {rel_volume:.2f}x")
        elif rel_volume is not None and rel_volume >= 1.2:
            score += 8
            reasons.append(f"Relative volume is acceptable at {rel_volume:.2f}x")
        else:
            score -= 10
            reasons.append("Relative volume is not strong enough")

        if current_price >= opening_range_high * 1.002:
            score += 12
            reasons.append("Price has cleared the opening-range high")
        elif current_price >= opening_range_high * 0.995:
            score += 5
            reasons.append("Price is testing the opening-range breakout")
        else:
            score -= 4
            reasons.append("Price has not reclaimed the opening-range high")

        if dollar_volume >= self.settings.min_dollar_volume * 3:
            score += 8
            reasons.append(f"Dollar volume is strong at ${dollar_volume:,.0f}")
        elif dollar_volume >= self.settings.min_dollar_volume:
            score += 4
            reasons.append(f"Dollar volume clears the floor at ${dollar_volume:,.0f}")

        if spread_pct is not None:
            if spread_pct <= 0.40:
                score += 8
                reasons.append(f"Spread is tight at {spread_pct:.2f}%")
            elif spread_pct <= 1.00:
                score += 4
                reasons.append(f"Spread is manageable at {spread_pct:.2f}%")
            elif spread_pct > 1.75:
                score -= 12
                reasons.append(f"Spread is too wide at {spread_pct:.2f}%")

        if 2.0 <= atr_pct <= 12.0:
            score += 6
            reasons.append(f"ATR volatility is healthy at {atr_pct:.1f}%")
        elif atr_pct > 18.0:
            score -= 8
            reasons.append(f"ATR volatility is extreme at {atr_pct:.1f}%")

        if closing_strength >= 0.65:
            score += 5
            reasons.append("Latest candle closed near its high")
        elif closing_strength <= 0.35:
            score -= 5
            reasons.append("Latest candle closed weakly")

        score = max(0, min(100, int(round(score))))

        hard_long_filters = (
            current_price > latest_vwap
            and ema9 > ema20
            and (rel_volume or 0.0) >= 1.2
            and dollar_volume >= self.settings.min_dollar_volume
        )
        if score < self.settings.watch_threshold:
            return None

        entry_price, actionable_now, entry_reason = self._plan_entry(
            current_price=current_price,
            opening_range_high=opening_range_high,
            ema9=ema9,
            ema20=ema20,
            latest_vwap=latest_vwap,
            atr14=atr14,
        )

        action = "BUY" if score >= self.settings.score_threshold and hard_long_filters and actionable_now else "WATCH"

        support_candidates = [
            value
            for value in [latest_vwap, ema20, recent_swing_low, opening_range_high]
            if value < entry_price
        ]
        if not support_candidates:
            return None
        support = max(support_candidates)

        stop_buffer = atr14 * self.settings.atr_stop_multiplier
        risk_per_share = entry_price - (support - stop_buffer)
        risk_per_share = max(risk_per_share, atr14 * self.settings.min_stop_atr)
        risk_per_share = min(risk_per_share, atr14 * self.settings.max_stop_atr)

        stop_loss = max(0.01, entry_price - risk_per_share)
        take_profit = entry_price + (risk_per_share * self.settings.risk_reward)

        return TradeIdea(
            symbol=snapshot.symbol,
            action=action,
            score=score,
            confidence=score,
            current_price=round(current_price, 4),
            entry_price=round(entry_price, 4),
            stop_loss=round(stop_loss, 4),
            take_profit=round(take_profit, 4),
            gap_pct=round(gap_pct, 2),
            relative_volume=round(rel_volume or 0.0, 2),
            dollar_volume=round(dollar_volume, 2),
            vwap=round(latest_vwap, 4),
            ema9=round(ema9, 4),
            ema20=round(ema20, 4),
            rsi14=round(rsi14, 2),
            macd_histogram=round(macd_histogram, 5),
            atr14=round(atr14, 4),
            opening_range_high=round(opening_range_high, 4),
            opening_range_low=round(opening_range_low, 4),
            generated_at=datetime.now(UTC),
            as_of=last_bar.time,
            reasons=[entry_reason, *reasons[:5]],
        )

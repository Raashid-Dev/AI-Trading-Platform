# engine/options_signal.py (UPDATED)

from datetime import datetime, time, timedelta
from typing import Optional


class SignalState:
    def __init__(self):
        self.daily_count = 0
        self.last_signal_ts: Optional[datetime] = None
        self.last_direction: Optional[str] = None
        self.last_reset_date = None

    def reset_if_new_day(self, today):
        if self.last_reset_date != today:
            self.daily_count = 0
            self.last_signal_ts = None
            self.last_direction = None
            self.last_reset_date = today

    def record(self, direction, ts):
        self.daily_count += 1
        self.last_signal_ts = ts
        self.last_direction = direction


def get_strike(spot, direction, confidence, interval=50):
    atm = round(spot / interval) * interval

    if confidence >= 0.85:
        if direction == "BULLISH":
            return atm - interval, "ITM"
        else:
            return atm + interval, "ITM"

    return atm, "ATM"


def _no_trade(reason):
    return {
        "signal": "NO_TRADE",
        "strike": None,
        "type": None,
        "confidence": None,
        "reason": reason,
    }


def generate_options_signal(
    direction,
    confidence,
    india_vix,
    nifty_spot,
    current_time,
    expiry_days_left,
    state,
):
    t = current_time.time()
    day = current_time.date()
    state.reset_if_new_day(day)

    # Filters
    if time(9, 15) <= t <= time(9, 30):
        return _no_trade("opening noise window")

    if t >= time(14, 55):
        return _no_trade("too close to close")

    if india_vix > 20:
        return _no_trade("VIX too high")

    if expiry_days_left == 0 and india_vix > 16:
        return _no_trade("expiry + high VIX")

    # Direction
    if direction == "SIDEWAYS":
        return _no_trade("market sideways")

    # 🔥 UPDATED CONFIDENCE
    if confidence < 0.55:
        return _no_trade(f"low confidence ({confidence})")

    # Risk control
    if state.daily_count >= 3:
        return _no_trade("max trades reached")

    if (
        state.last_signal_ts
        and state.last_direction == direction
        and (current_time - state.last_signal_ts) < timedelta(minutes=15)
    ):
        return _no_trade("cooldown active")

    strike, strike_type = get_strike(nifty_spot, direction, confidence)

    signal = "BUY_CALL" if direction == "BULLISH" else "BUY_PUT"

    state.record(direction, current_time)

    return {
        "signal": signal,
        "strike": strike,
        "type": strike_type,
        "confidence": round(confidence, 2),
        "reason": f"{direction} | conf={confidence}",
    }
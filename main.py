import logging
import os
import random
import sys
import time
import json
from collections import deque
from datetime import datetime
import pytz
from typing import Optional, Dict

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO)
log_main = logging.getLogger("trading-loop")

# ===== IMPORTS =====
from engine import run_multi_signal_pipeline, build_state_map, fetch_all, TradeLog
from engine.multi_signal_engine import rank_signals, filter_best_signals
from engine.live_data import mock_fetch_all

# ===== TIMEZONE =====
IST = pytz.timezone("Asia/Kolkata")

# ===== CONFIG =====
LIVE_INTERVAL_SECONDS = 10
HISTORY_MAXLEN = 40   # candles to keep per symbol

# ✅ ABSOLUTE PATH for state file (consistent across server + loop)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIVE_STATE_FILE = os.path.join(BASE_DIR, "live_state.json")

log_main.info("State file: %s", LIVE_STATE_FILE)

# ===== PRICE HISTORY =====
# Accumulates last HISTORY_MAXLEN data points per symbol for charts
_TRACKED_SYMBOLS = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]
price_history: Dict[str, deque] = {sym: deque(maxlen=HISTORY_MAXLEN) for sym in _TRACKED_SYMBOLS}


def _append_history(symbol: str, data: dict, now: datetime) -> None:
    if symbol not in price_history:
        return
    price_history[symbol].append({
        "t":          now.strftime("%H:%M"),
        "price":      round(data["price"], 2),
        "ema9":       round(data["ema9"], 2),
        "ema21":      round(data["ema21"], 2),
        "vwap":       round(data["vwap"], 2),
        "change_pct": round(data["price_change"], 3),
    })


def _serialize_history() -> Dict[str, list]:
    return {sym: list(dq) for sym, dq in price_history.items()}


# ===== SAFE WRITE =====
def write_state_atomic(state: dict) -> None:
    try:
        tmp = LIVE_STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2, default=str)
        os.replace(tmp, LIVE_STATE_FILE)
        log_main.debug("State written  keys=%s", list(state.keys()))
    except Exception as e:
        log_main.error("State write failed: %s", e)


# ===== MOCK MANUAL INPUTS =====
def _mock_manual_inputs() -> dict:
    """
    Vary macro inputs so the scorer produces a full range of signal
    strengths — including ones that clear the confidence filter.
    """
    stance = random.choice(["BULL", "BEAR", "NEUTRAL"])
    if stance == "BULL":
        pcr, fii, oi = round(random.uniform(0.5, 0.79), 2), round(random.uniform(600, 1500)), random.choice([0, 1])
        crude, dxy   = round(random.uniform(-2, 0), 2), round(random.uniform(-1, 0), 2)
    elif stance == "BEAR":
        pcr, fii, oi = round(random.uniform(1.21, 2.0), 2), round(random.uniform(-1500, -600)), random.choice([0, -1])
        crude, dxy   = round(random.uniform(0, 2), 2), round(random.uniform(0, 1), 2)
    else:
        pcr, fii, oi = round(random.uniform(0.8, 1.2), 2), round(random.uniform(-400, 400)), 0
        crude, dxy   = round(random.uniform(-0.5, 0.5), 2), round(random.uniform(-0.5, 0.5), 2)

    return {
        "pcr":              pcr,
        "fii_net_cr":       fii,
        "oi_bias":          oi,
        "crude_change":     crude,
        "dxy_change":       dxy,
        "india_vix":        round(random.uniform(13.0, 18.0), 1),
        "expiry_days_left": random.randint(1, 3),
    }


# ===== MAIN LOOP =====
def live_loop(mock: bool = False) -> None:
    """
    Main trading loop.
    Can be called directly (if __name__ == '__main__') OR
    started as a daemon thread from server.py on startup.
    """
    state_map = build_state_map()
    log       = TradeLog()
    candle    = 0
    mode      = "MOCK" if mock else "LIVE"

    log_main.info("Trading loop starting  mode=%s  state_file=%s", mode, LIVE_STATE_FILE)

    # Write initial state immediately → dashboard shows correct capital from start
    try:
        snapshot = log.export_state()
        snapshot["price_history"] = _serialize_history()
        snapshot["symbol_snapshot"] = {}
        write_state_atomic(snapshot)
        log_main.info("Initial state written  capital=%.0f", snapshot["capital"]["capital"])
    except Exception as e:
        log_main.error("Initial state write failed: %s", e)

    while True:
        candle += 1
        now = datetime.now(IST)
        log_main.info("Candle %d [%s]  time=%s", candle, mode, now.strftime("%H:%M:%S"))

        try:
            # 1. Fetch market data
            data = mock_fetch_all() if mock else fetch_all()
            valid = {sym: d for sym, d in data.items() if d is not None}
            log_main.debug("Fetched  valid=%d/%d", len(valid), len(data))

            # 2. Accumulate price history
            for sym, d in valid.items():
                _append_history(sym, d, now)

            # 3. Build manual inputs
            # Always randomize macro inputs — we don't have a live macro feed yet
            # (PCR, FII flows, India VIX, crude etc. change intraday; randomizing
            #  ensures all signal stances get exercised and confidence thresholds fire)
            manual_inputs = _mock_manual_inputs()

            # 4. Run pipeline
            results = run_multi_signal_pipeline(data, manual_inputs, now, state_map)
            if not results:
                log_main.warning("Pipeline returned empty — skipping candle")
                time.sleep(LIVE_INTERVAL_SECONDS)
                continue

            # 5. Rank + filter
            ranked = rank_signals(results)
            best   = filter_best_signals(ranked, results=results)
            log_main.info("Signals  ranked=%d  best=%d  stance=pcr%.2f/fii%.0f",
                          len(ranked), len(best), manual_inputs["pcr"], manual_inputs["fii_net_cr"])

            # 6. Update trade log
            log.set_latest_signals(best)

            # 7. Build symbol snapshot (current state of all symbols)
            symbol_snapshot = {}
            for sym, d in valid.items():
                r = results.get(sym, {})
                symbol_snapshot[sym] = {
                    "price":          round(d["price"], 2),
                    "change_pct":     round(d["price_change"], 3),
                    "ema9":           round(d["ema9"], 2),
                    "ema21":          round(d["ema21"], 2),
                    "vwap":           round(d["vwap"], 2),
                    "signal":         r.get("signal", "NO_TRADE"),
                    "direction":      r.get("direction", ""),
                    "confidence":     r.get("confidence", 0),
                    "trend_strength": r.get("trend_strength", ""),
                    "score":          r.get("score", 0),
                }

            # 8. Export state + write
            snapshot = log.export_state()
            snapshot["price_history"]   = _serialize_history()
            snapshot["symbol_snapshot"] = symbol_snapshot
            snapshot["manual_inputs"]   = manual_inputs
            write_state_atomic(snapshot)

        except Exception as e:
            log_main.error("Loop error on candle %d: %s", candle, e, exc_info=True)

        time.sleep(LIVE_INTERVAL_SECONDS)


# ===== ENTRY =====
if __name__ == "__main__":
    if "--live" in sys.argv:
        live_loop(mock=False)
    elif "--mock" in sys.argv:
        live_loop(mock=True)
    else:
        print("Usage: python main.py --live | --mock")

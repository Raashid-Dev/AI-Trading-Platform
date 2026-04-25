import logging
import os
import random
import sys
import time
import json
from datetime import datetime
import pytz
from typing import Optional

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

# ✅ CRITICAL FIX: ABSOLUTE PATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIVE_STATE_FILE = os.path.join(BASE_DIR, "live_state.json")

print(f"[INIT] State file path: {LIVE_STATE_FILE}")

# #region agent log
_DBG_PATH = os.path.join(BASE_DIR, ".cursor", "debug-afaa4d.log")
def _dbg(message: str, data: Optional[dict] = None, *, hypothesisId: str = "H0", runId: str = "pre-fix"):
    try:
        payload = {
            "sessionId": "afaa4d",
            "runId": runId,
            "hypothesisId": hypothesisId,
            "location": "main.py",
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open(_DBG_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
# #endregion


# ===== SAFE WRITE FUNCTION =====
def write_state_atomic(state: dict):
    try:
        tmp_file = LIVE_STATE_FILE + ".tmp"

        with open(tmp_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

        os.replace(tmp_file, LIVE_STATE_FILE)

        print(f"[STATE WRITE] Success at {datetime.now()}")
        _dbg("state_write_success", {"path": LIVE_STATE_FILE, "keys": list(state.keys())}, hypothesisId="H4")

    except Exception as e:
        print(f"[STATE ERROR] {e}")
        _dbg("state_write_error", {"path": LIVE_STATE_FILE, "error": repr(e)}, hypothesisId="H4")


def _mock_manual_inputs() -> dict:
    """
    Randomised macro inputs for mock mode so the scorer produces
    a wide range of signal strengths — including ones that pass
    the confidence / score filters.

    Cycles through bullish / bearish / neutral stances to ensure
    real signals appear within a few candles.
    """
    # Pick a random market stance
    stance = random.choice(["BULL", "BEAR", "NEUTRAL"])

    if stance == "BULL":
        pcr        = round(random.uniform(0.5, 0.79), 2)   # < 0.8 → +3
        fii_net_cr = round(random.uniform(500, 1500), 0)   # > 500 → +3
        oi_bias    = random.choice([0, 1])                 # 0 or +3
        crude      = round(random.uniform(-2, 0), 2)       # crude down → macro +1
        dxy        = round(random.uniform(-1, 0), 2)
    elif stance == "BEAR":
        pcr        = round(random.uniform(1.21, 2.0), 2)   # > 1.2 → -3
        fii_net_cr = round(random.uniform(-1500, -500), 0) # < -500 → -3
        oi_bias    = random.choice([0, -1])                # 0 or -3
        crude      = round(random.uniform(0, 2), 2)
        dxy        = round(random.uniform(0, 1), 2)
    else:  # NEUTRAL
        pcr        = round(random.uniform(0.8, 1.2), 2)
        fii_net_cr = round(random.uniform(-400, 400), 0)
        oi_bias    = 0
        crude      = round(random.uniform(-0.5, 0.5), 2)
        dxy        = round(random.uniform(-0.5, 0.5), 2)

    return {
        "pcr":              pcr,
        "fii_net_cr":       fii_net_cr,
        "oi_bias":          oi_bias,
        "crude_change":     crude,
        "dxy_change":       dxy,
        "india_vix":        round(random.uniform(13.0, 18.0), 1),
        "expiry_days_left": random.randint(1, 3),
    }


# ===== MAIN LOOP =====
def live_loop(mock: bool = False):
    _dbg("live_loop_enter", {"argv": sys.argv, "cwd": os.getcwd(), "base_dir": BASE_DIR, "state_file": LIVE_STATE_FILE, "mock": mock}, hypothesisId="H1")
    state_map = build_state_map()
    log = TradeLog()

    candle = 0
    mode_label = "MOCK" if mock else "LIVE"
    print(f"\n🚀 TRADING LOOP STARTED [{mode_label}]\n")

    # Write initial state immediately so dashboard shows correct capital on startup
    try:
        write_state_atomic(log.export_state())
        print("[INIT] Initial state written — capital ready.")
    except Exception as e:
        print(f"[INIT] Could not write initial state: {e}")

    while True:
        candle += 1
        now = datetime.now(IST)

        try:
            print(f"\n===== Candle {candle} [{mode_label}] =====")
            _dbg("candle_begin", {"candle": candle, "now": now.isoformat(), "mock": mock}, hypothesisId="H0")

            # 1. Fetch data — mock uses synthetic data; live uses yfinance
            if mock:
                data = mock_fetch_all()
            else:
                data = fetch_all()
            _dbg("fetch_all_done", {"candle": candle, "symbols": list(data.keys()), "n_nonnull": sum(1 for v in data.values() if v is not None)}, hypothesisId="H2")

            # 2. Build manual inputs
            manual_inputs = _mock_manual_inputs() if mock else {
                "pcr": 1.0,
                "fii_net_cr": 0.0,
                "oi_bias": 0,
                "crude_change": 0.0,
                "dxy_change": 0.0,
                "india_vix": 15.0,
                "expiry_days_left": 1,
            }
            print(f"[INPUTS] stance implied by pcr={manual_inputs['pcr']}  fii={manual_inputs['fii_net_cr']}")

            results = run_multi_signal_pipeline(data, manual_inputs, now, state_map)
            _dbg("pipeline_done", {"candle": candle, "result_keys": list(results.keys())[:20]}, hypothesisId="H3")

            if not results:
                print("No results from pipeline — sleeping.")
                time.sleep(LIVE_INTERVAL_SECONDS)
                continue

            # 3. Rank + filter
            ranked = rank_signals(results)
            best   = filter_best_signals(ranked, results=results)
            print(f"[SIGNALS] ranked={len(ranked)}  best={len(best)}")
            _dbg("filter_done", {"candle": candle, "ranked": len(ranked), "best": len(best)}, hypothesisId="H0")

            # 4. Store + export state
            log.set_latest_signals(best)
            snapshot = log.export_state()
            print(f"[STATE] capital={snapshot.get('capital', {}).get('capital')}  signals={len(snapshot.get('signals', []))}")
            write_state_atomic(snapshot)

        except Exception as e:
            log_main.error(f"Loop error: {e}", exc_info=True)
            _dbg("loop_exception", {"candle": candle, "error": repr(e)}, hypothesisId="H3")

        time.sleep(LIVE_INTERVAL_SECONDS)


# ===== ENTRY =====
if __name__ == "__main__":
    _dbg("main_entry", {"argv": sys.argv}, hypothesisId="H1")
    if "--live" in sys.argv:
        live_loop(mock=False)
    elif "--mock" in sys.argv:
        live_loop(mock=True)
    else:
        print("Run with: python main.py --live  (or --mock)")
        _dbg("main_exit_no_mode_flag", {"argv": sys.argv}, hypothesisId="H1")

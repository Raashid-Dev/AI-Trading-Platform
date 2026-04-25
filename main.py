import logging
import os
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


# ===== MAIN LOOP =====
def live_loop(mock: bool = False):
    _dbg("live_loop_enter", {"argv": sys.argv, "cwd": os.getcwd(), "base_dir": BASE_DIR, "state_file": LIVE_STATE_FILE, "mock": mock}, hypothesisId="H1")
    state_map = build_state_map()
    log = TradeLog()

    candle = 0
    mode_label = "MOCK" if mock else "LIVE"
    print(f"\n🚀 TRADING LOOP STARTED [{mode_label}]\n")

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

            # 2. Run pipeline
            # Default manual inputs (until wired to real sources / UI inputs)
            manual_inputs = {
                "pcr": 1.0,
                "fii_net_cr": 0.0,
                "oi_bias": 0,
                "crude_change": 0.0,
                "dxy_change": 0.0,
                "india_vix": 15.0,
                "expiry_days_left": 1,
            }
            results = run_multi_signal_pipeline(
                data,
                manual_inputs,
                now,
                state_map
            )
            _dbg("pipeline_done", {"candle": candle, "result_keys": list(results.keys())[:20]}, hypothesisId="H3")

            if not results:
                print("No results...")
                time.sleep(LIVE_INTERVAL_SECONDS)
                continue

            # 3. Rank + filter
            ranked = rank_signals(results)
            best = filter_best_signals(ranked, results=results)
            _dbg("filter_done", {"candle": candle, "ranked": len(ranked), "best": len(best)}, hypothesisId="H0")

            # 4. Store in log
            log.set_latest_signals(best)

            # 5. Export state (THIS IS WHAT UI READS)
            snapshot = log.export_state()

            print("[DEBUG] Snapshot keys:", snapshot.keys())

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
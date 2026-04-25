import logging
import os
import sys
import time
import json
from datetime import datetime
import pytz

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO)
log_main = logging.getLogger("trading-loop")

# ===== IMPORTS =====
from engine import run_multi_signal_pipeline, build_state_map, fetch_all, TradeLog
from engine.multi_signal_engine import rank_signals, filter_best_signals

# ===== TIMEZONE =====
IST = pytz.timezone("Asia/Kolkata")

# ===== CONFIG =====
LIVE_INTERVAL_SECONDS = 10

# ✅ CRITICAL FIX: ABSOLUTE PATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIVE_STATE_FILE = os.path.join(BASE_DIR, "live_state.json")

print(f"[INIT] State file path: {LIVE_STATE_FILE}")

# ===== SAFE WRITE FUNCTION =====
def write_state_atomic(state: dict):
    try:
        tmp_file = LIVE_STATE_FILE + ".tmp"

        with open(tmp_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

        os.replace(tmp_file, LIVE_STATE_FILE)

        print(f"[STATE WRITE] Success at {datetime.now()}")

    except Exception as e:
        print(f"[STATE ERROR] {e}")


# ===== MAIN LOOP =====
def live_loop():
    state_map = build_state_map()
    log = TradeLog()

    candle = 0

    print("\n🚀 LIVE LOOP STARTED\n")

    while True:
        candle += 1
        now = datetime.now(IST)

        try:
            print(f"\n===== Candle {candle} =====")

            # 1. Fetch data
            data = fetch_all()

            # 2. Run pipeline
            results = run_multi_signal_pipeline(
                data,
                {},  # manual inputs optional
                now,
                state_map
            )

            if not results:
                print("No results...")
                time.sleep(LIVE_INTERVAL_SECONDS)
                continue

            # 3. Rank + filter
            ranked = rank_signals(results)
            best = filter_best_signals(ranked, results=results)

            # 4. Store in log
            log.set_latest_signals(best)

            # 5. Export state (THIS IS WHAT UI READS)
            snapshot = log.export_state()

            print("[DEBUG] Snapshot keys:", snapshot.keys())

            write_state_atomic(snapshot)

        except Exception as e:
            log_main.error(f"Loop error: {e}", exc_info=True)

        time.sleep(LIVE_INTERVAL_SECONDS)


# ===== ENTRY =====
if __name__ == "__main__":
    if "--live" in sys.argv:
        live_loop()
    else:
        print("Run with: python main.py --live")
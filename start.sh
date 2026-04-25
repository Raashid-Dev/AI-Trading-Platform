#!/usr/bin/env bash
# start.sh — single-container entrypoint for Render.
#
# Launches the trading loop in the background, then starts the FastAPI server
# in the foreground.  Both processes share the same filesystem so
# live_state.json is visible to both.
#
# Environment variables:
#   TRADING_MODE   "live" (real yfinance data) or "mock" (simulated)
#                  defaults to "mock" — safer for first deploy
#   PORT           set automatically by Render
#   LIVE_STATE_FILE path to state file (default: live_state.json)

set -e

TRADING_MODE=${TRADING_MODE:-mock}
PORT=${PORT:-8000}

echo "========================================"
echo " AI Trading Platform"
echo " Mode  : $TRADING_MODE"
echo " Port  : $PORT"
echo "========================================"

# Start the trading loop as a background process
echo "[start.sh] Starting trading loop ($TRADING_MODE)..."
python main.py --${TRADING_MODE} &
LOOP_PID=$!
echo "[start.sh] Trading loop PID: $LOOP_PID"

# Start the FastAPI server in the foreground (Render monitors this process)
echo "[start.sh] Starting FastAPI server on port $PORT..."
exec uvicorn server:app --host 0.0.0.0 --port "$PORT"

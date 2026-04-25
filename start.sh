#!/usr/bin/env bash
# start.sh — Render entrypoint.
#
# The trading loop now runs as a daemon thread INSIDE the FastAPI process
# (started from server.py on_event("startup")).
# This gives us a single process, unified logs, and no silent background crashes.
#
# Environment variables:
#   TRADING_MODE   "live" | "mock"  (default: mock)
#   PORT           set automatically by Render

set -e

TRADING_MODE=${TRADING_MODE:-mock}
PORT=${PORT:-8000}

echo "========================================"
echo " AI Trading Platform"
echo " Mode  : $TRADING_MODE"
echo " Port  : $PORT"
echo "========================================"

PY="${PYTHON_BIN:-python}"

echo "[start.sh] Starting FastAPI server + trading loop on port $PORT..."
exec "$PY" -m uvicorn server:app --host 0.0.0.0 --port "$PORT"

# server.py
# FastAPI backend — HTTP endpoints + WebSocket broadcast.
#
# Local dev:
#   uvicorn server:app --host 0.0.0.0 --port 8000 --reload
#
# Production (Render / Railway):
#   uvicorn server:app --host 0.0.0.0 --port $PORT
#
# Environment variables:
#   ALLOWED_ORIGINS   comma-separated list, e.g. "https://my-dashboard.vercel.app"
#                     defaults to "*" (dev-only — tighten for prod)
#   LIVE_STATE_FILE   path to JSON state file (default: live_state.json)

import os
import json
import asyncio
import logging
import time
import threading
from typing import Dict, Any
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s  %(message)s",
)
log = logging.getLogger("server")

# ─────────────────────────────────────────────
# ENV CONFIG
# ─────────────────────────────────────────────
LIVE_STATE_FILE = os.getenv("LIVE_STATE_FILE", "live_state.json")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ─────────────────────────────────────────────
# FASTAPI INIT
# ─────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────
_clients = set()
_last_valid_state: Dict[str, Any] = {}
_last_update_time = None

# ─────────────────────────────────────────────
# SAFE FILE READ
# ─────────────────────────────────────────────
def _load_state_safe():
    global _last_valid_state

    try:
        if os.path.exists(LIVE_STATE_FILE):
            with open(LIVE_STATE_FILE, "r") as f:
                data = json.load(f)
                _last_valid_state = data
                return data
    except Exception as e:
        log.warning(f"State read failed, using last valid: {e}")

    return _last_valid_state

# ─────────────────────────────────────────────
# WEBSOCKET BROADCAST
# ─────────────────────────────────────────────
async def _broadcast(data: dict):
    global _last_update_time
    _last_update_time = time.time()

    dead = []
    for ws in _clients:
        try:
            await ws.send_text(json.dumps(data))
        except:
            dead.append(ws)

    for d in dead:
        _clients.discard(d)

# ─────────────────────────────────────────────
# HEARTBEAT
# ─────────────────────────────────────────────
async def _heartbeat_task():
    while True:
        await asyncio.sleep(15)
        await _broadcast({"type": "heartbeat"})

# ─────────────────────────────────────────────
# FILE WATCHER
# ─────────────────────────────────────────────
async def _file_watcher():
    last_mtime = 0

    while True:
        await asyncio.sleep(2)

        if not os.path.exists(LIVE_STATE_FILE):
            continue

        mtime = os.path.getmtime(LIVE_STATE_FILE)

        if mtime != last_mtime:
            last_mtime = mtime
            data = _load_state_safe()
            await _broadcast(data)

# ─────────────────────────────────────────────
# RATE LIMIT (10 req/sec)
# ─────────────────────────────────────────────
_rate_store = defaultdict(list)

def rate_limit(request: Request):
    ip = request.client.host
    now = time.time()

    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < 1]

    if len(_rate_store[ip]) >= 10:
        raise HTTPException(status_code=429, detail="Too many requests")

    _rate_store[ip].append(now)

_RL = Depends(rate_limit)

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "state_file": "present" if os.path.exists(LIVE_STATE_FILE) else "missing",
        "connections": len(_clients),
        "last_update": _last_update_time,
        "mode": "websocket" if _clients else "polling",
    }

@app.get("/state", dependencies=[_RL])
def get_state():
    return _load_state_safe()

@app.get("/signals", dependencies=[_RL])
def get_signals():
    return _load_state_safe().get("signals", [])

@app.get("/trades", dependencies=[_RL])
def get_trades():
    data = _load_state_safe()
    return {
        "open": data.get("open_trades", []),
        "closed": data.get("closed_trades", []),
    }

@app.get("/capital", dependencies=[_RL])
def get_capital():
    return _load_state_safe().get("capital", {})

@app.get("/summary", dependencies=[_RL])
def get_summary():
    data = _load_state_safe()
    return {
        "capital": data.get("capital", {}),
        "performance": data.get("performance", {}),
        "signals": len(data.get("signals", [])),
        "open": len(data.get("open_trades", [])),
        "closed": len(data.get("closed_trades", [])),
    }

# ─────────────────────────────────────────────
# WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)

    try:
        while True:
            await asyncio.wait_for(ws.receive_text(), timeout=20)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        _clients.discard(ws)

# ─────────────────────────────────────────────
# 🚀 TRADING LOOP RUNNER
# ─────────────────────────────────────────────
def _start_trading_loop():
    try:
        import main
        log.info("🚀 Starting trading loop...")
        main.live_loop()
    except Exception as e:
        log.error(f"❌ Trading loop crashed: {e}", exc_info=True)

# ─────────────────────────────────────────────
# 🔥 MANUAL START ENDPOINT (RENDER FREE FIX)
# ─────────────────────────────────────────────
@app.get("/start")
def start_loop():
    threading.Thread(target=_start_trading_loop, daemon=True).start()
    return {"status": "started"}

# ─────────────────────────────────────────────
# STARTUP TASKS
# ─────────────────────────────────────────────
@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(_file_watcher())
    asyncio.create_task(_heartbeat_task())

    log.info("Server started (watcher + heartbeat ready)")
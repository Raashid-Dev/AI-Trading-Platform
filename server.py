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
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# #region agent log
_DBG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cursor", "debug-afaa4d.log")
def _dbg(message: str, data: Optional[dict] = None, *, hypothesisId: str = "H0", runId: str = "pre-fix"):
    try:
        payload = {
            "sessionId": "afaa4d",
            "runId": runId,
            "hypothesisId": hypothesisId,
            "location": "server.py",
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open(_DBG_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
# #endregion

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
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIVE_STATE_FILE = os.getenv("LIVE_STATE_FILE", "live_state.json")
# If LIVE_STATE_FILE is relative, resolve next to this file.
# This avoids cwd-dependent mismatches between the loop and API server.
if not os.path.isabs(LIVE_STATE_FILE):
    LIVE_STATE_FILE = os.path.join(_BASE_DIR, LIVE_STATE_FILE)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
_dbg("server_boot", {"live_state_file": LIVE_STATE_FILE, "allowed_origins": ALLOWED_ORIGINS, "cwd": os.getcwd()}, hypothesisId="H5")

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
_loop_started = False
_loop_lock = threading.Lock()

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
                _dbg("state_read_ok", {"path": LIVE_STATE_FILE, "keys": list(data.keys())}, hypothesisId="H5")
                return data
    except Exception as e:
        log.warning(f"State read failed, using last valid: {e}")
        _dbg("state_read_error", {"path": LIVE_STATE_FILE, "error": repr(e)}, hypothesisId="H5")

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
            _dbg("watch_missing_state_file", {"path": LIVE_STATE_FILE}, hypothesisId="H5")
            continue

        mtime = os.path.getmtime(LIVE_STATE_FILE)

        if mtime != last_mtime:
            last_mtime = mtime
            data = _load_state_safe()
            await _broadcast(data)
            _dbg("watch_broadcast", {"path": LIVE_STATE_FILE, "mtime": mtime, "n_clients": len(_clients)}, hypothesisId="H5")

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
            # Client may not send messages; keep socket open.
            # Heartbeats are sent server->client by _heartbeat_task().
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        _clients.discard(ws)

# ─────────────────────────────────────────────
# 🚀 TRADING LOOP RUNNER
# ─────────────────────────────────────────────
def _start_trading_loop():
    try:
        _dbg("start_trading_loop_thread_enter", {}, hypothesisId="H6")
        import main
        log.info("🚀 Starting trading loop...")
        main.live_loop()
    except Exception as e:
        log.error(f"❌ Trading loop crashed: {e}", exc_info=True)
        _dbg("start_trading_loop_thread_exception", {"error": repr(e)}, hypothesisId="H6")

# ─────────────────────────────────────────────
# 🔥 MANUAL START ENDPOINT (RENDER FREE FIX)
# ─────────────────────────────────────────────
@app.get("/start")
def start_loop():
    global _loop_started
    with _loop_lock:
        if _loop_started:
            _dbg("start_loop_ignored_already_running", {}, hypothesisId="H6")
            return {"status": "already_running"}
        _loop_started = True
        _dbg("start_loop_thread_spawn", {}, hypothesisId="H6")
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
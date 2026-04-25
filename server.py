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

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger("trading-server")

# ── Config from environment ────────────────────────────────
LIVE_STATE_FILE = os.getenv("LIVE_STATE_FILE", "live_state.json")

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: List[str] = (
    ["*"] if _raw_origins.strip() == "*"
    else [o.strip() for o in _raw_origins.split(",") if o.strip()]
)

# ── Rate limiter config (PART 5) ──────────────────────────
_RATE_LIMIT_MAX = 10          # max requests
_RATE_LIMIT_WIN = 1.0         # per second
_rate_store: Dict[str, List[float]] = defaultdict(list)

# ── Last-valid state cache (PART 2) ───────────────────────
_last_valid_state: Dict[str, Any] = {}

# ── Broadcast timestamp (PART 10) ─────────────────────────
_last_broadcast_time: Optional[float] = None


# ── App ────────────────────────────────────────────────────
app = FastAPI(
    title="AI Trading Engine",
    description="Live signal engine with WebSocket broadcast.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

log.info("CORS origins: %s", ALLOWED_ORIGINS)


# ── ENV validation (PART 8) ───────────────────────────────
@app.on_event("startup")
async def validate_env() -> None:
    warnings: List[str] = []

    if ALLOWED_ORIGINS == ["*"]:
        warnings.append(
            "ALLOWED_ORIGINS is '*' — OK for dev, but set it to your Vercel URL in production."
        )
    if LIVE_STATE_FILE == "live_state.json":
        warnings.append(
            "LIVE_STATE_FILE not explicitly set — using default 'live_state.json' in CWD."
        )

    for w in warnings:
        log.warning("ENV: %s", w)

    log.info(
        "Startup OK — state_file=%s  origins=%s",
        LIVE_STATE_FILE, ALLOWED_ORIGINS,
    )


# ── Rate limiter (PART 5) ─────────────────────────────────
def _rate_limit_check(ip: str) -> bool:
    now = time.monotonic()
    # Prune timestamps outside the window
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < _RATE_LIMIT_WIN]
    if len(_rate_store[ip]) >= _RATE_LIMIT_MAX:
        return False
    _rate_store[ip].append(now)
    return True


async def rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    if not _rate_limit_check(ip):
        log.warning("Rate limit exceeded  ip=%s  path=%s", ip, request.url.path)
        raise HTTPException(status_code=429, detail="Rate limit exceeded — max 10 req/s per IP")


_RL = Depends(rate_limit)   # reusable shorthand


# ── WebSocket connection manager (PART 1) ─────────────────
class ConnectionManager:
    """Thread-safe registry of active WebSocket clients."""

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        log.info("WS connect  remote=%s  total=%d", _ws_addr(ws), len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        log.info("WS disconnect  remote=%s  total=%d", _ws_addr(ws), len(self._clients))

    async def broadcast(self, payload: str) -> None:
        """Send text to every connected client; silently drop dead ones."""
        global _last_broadcast_time
        if not self._clients:
            return

        async with self._lock:
            targets = list(self._clients)

        dead: List[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception as exc:
                log.debug("WS send failed — will prune  remote=%s  err=%s", _ws_addr(ws), exc)
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
            log.info("Pruned %d dead WS clients  remaining=%d", len(dead), len(self._clients))

        _last_broadcast_time = time.time()

    async def ping_all(self) -> None:
        """Lightweight ping to flush dead connections."""
        if self._clients:
            await self.broadcast(json.dumps({"type": "ping"}))

    @property
    def count(self) -> int:
        return len(self._clients)


manager = ConnectionManager()


def _ws_addr(ws: WebSocket) -> str:
    try:
        return f"{ws.client.host}:{ws.client.port}"
    except Exception:
        return "unknown"


# ── State helpers ──────────────────────────────────────────

def _load_state() -> Dict[str, Any]:
    """Read live_state.json; raise HTTPException on failure."""
    if not os.path.exists(LIVE_STATE_FILE):
        raise HTTPException(
            status_code=503,
            detail="State file not yet written — trading loop hasn't started.",
        )
    try:
        with open(LIVE_STATE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"State file corrupt: {exc}")


def _load_state_safe() -> Dict[str, Any]:
    """
    PART 2 — never raises.
    Returns last known-good state when file is missing or corrupt.
    """
    global _last_valid_state

    if not os.path.exists(LIVE_STATE_FILE):
        return _last_valid_state   # empty {} on first boot

    try:
        with open(LIVE_STATE_FILE, "r") as f:
            data = json.load(f)
        _last_valid_state = data   # update fallback cache
        return data
    except Exception as exc:
        log.warning("State file unreadable — returning last valid state  err=%s", exc)
        return _last_valid_state


# ── Public helper used by main.py ─────────────────────────
async def broadcast_state(state: Dict[str, Any]) -> None:
    """Called by the trading loop after every candle write."""
    if manager.count == 0:
        return
    try:
        payload = json.dumps(state, default=str)
        await manager.broadcast(payload)
    except Exception as exc:
        log.warning("broadcast_state error: %s", exc)


# ── Background tasks ──────────────────────────────────────

async def _heartbeat_task() -> None:
    """PART 1 — pings all WS clients every 15 s to detect dead connections."""
    while True:
        await asyncio.sleep(15)
        if manager.count > 0:
            await manager.ping_all()
            log.debug("Heartbeat sent  clients=%d", manager.count)


async def _file_watcher() -> None:
    """
    Polls live_state.json every 1 s.
    Broadcasts to WS clients when mtime or size changes.
    """
    last_mtime: float = 0.0
    last_size:  int   = 0

    while True:
        await asyncio.sleep(1)
        try:
            if not os.path.exists(LIVE_STATE_FILE):
                continue
            stat = os.stat(LIVE_STATE_FILE)
            if stat.st_mtime == last_mtime and stat.st_size == last_size:
                continue
            last_mtime = stat.st_mtime
            last_size  = stat.st_size

            state = _load_state_safe()
            if state:
                await manager.broadcast(json.dumps(state, default=str))
                log.debug("Broadcast triggered  size=%d bytes", last_size)
        except Exception as exc:
            log.warning("file_watcher error: %s", exc)


@app.on_event("startup")
async def start_background_tasks() -> None:
    asyncio.create_task(_file_watcher())
    asyncio.create_task(_heartbeat_task())
    log.info("Background tasks started — file_watcher + heartbeat@15s")


# ── WebSocket endpoint (PART 1) ────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """
    WebSocket streaming endpoint.
    • On connect  → immediately sends the current state snapshot.
    • Updates     → pushed automatically by _file_watcher.
    • Heartbeat   → ping every 15 s via _heartbeat_task.
    • Dead clients → auto-pruned on next broadcast.
    """
    await manager.connect(ws)
    try:
        initial = _load_state_safe()
        if initial:
            await ws.send_text(json.dumps(initial, default=str))
            log.info("WS initial state pushed  remote=%s", _ws_addr(ws))
        else:
            await ws.send_text(
                json.dumps({"status": "waiting", "message": "Trading loop not started yet"})
            )

        # Keep session alive — recv() blocks until the client disconnects
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=20)
            except asyncio.TimeoutError:
                pass   # normal — heartbeat handles pings separately

    except WebSocketDisconnect:
        log.info("WS clean disconnect  remote=%s", _ws_addr(ws))
    except Exception as exc:
        log.warning("WS unexpected error  remote=%s  err=%s", _ws_addr(ws), exc)
    finally:
        await manager.disconnect(ws)


# ── HTTP endpoints ─────────────────────────────────────────

@app.get("/health")
def health(request: Request) -> Dict[str, Any]:
    """
    PART 10 — enhanced health check.
    Returns: status, connections, last_update (UTC ISO-8601), mode.
    """
    state_present = os.path.exists(LIVE_STATE_FILE)
    last_ts: Optional[str] = None
    if _last_broadcast_time is not None:
        last_ts = datetime.fromtimestamp(_last_broadcast_time, tz=timezone.utc).isoformat()

    mode = "websocket" if manager.count > 0 else "polling"

    return {
        "status":          "ok",
        "state_file":      "present" if state_present else "missing",
        "connections":     manager.count,
        "last_update":     last_ts,
        "mode":            mode,
        "allowed_origins": ALLOWED_ORIGINS,
    }


@app.get("/state", dependencies=[_RL])
def get_state(request: Request) -> JSONResponse:
    log.info("GET /state  ip=%s", request.client.host if request.client else "?")
    return JSONResponse(_load_state())


@app.get("/metrics")
def get_metrics() -> JSONResponse:
    data = _load_state()
    return JSONResponse(data.get("performance", data.get("metrics", {})))


@app.get("/trades")
def get_trades() -> JSONResponse:
    data = _load_state()
    return JSONResponse({
        "open":   data.get("open_trades",   []),
        "closed": data.get("closed_trades", []),
    })


@app.get("/capital")
def get_capital() -> JSONResponse:
    data = _load_state()
    return JSONResponse(data.get("capital", {}))


@app.get("/signals", dependencies=[_RL])
def get_signals(request: Request) -> JSONResponse:
    log.info("GET /signals  ip=%s", request.client.host if request.client else "?")
    data = _load_state()
    return JSONResponse(data.get("signals", []))


@app.get("/summary", dependencies=[_RL])
def get_summary(request: Request) -> JSONResponse:
    log.info("GET /summary  ip=%s", request.client.host if request.client else "?")
    data = _load_state()
    perf = data.get("performance", data.get("metrics", {}))
    sigs = data.get("signals", [])

    total_sigs = len(sigs)
    buy_call   = sum(1 for s in sigs if s.get("signal") == "BUY_CALL")
    buy_put    = sum(1 for s in sigs if s.get("signal") == "BUY_PUT")
    confs      = [float(s.get("confidence") or 0.0) for s in sigs]
    avg_conf   = round(sum(confs) / total_sigs, 4) if total_sigs else 0.0

    return JSONResponse({
        "capital": data.get("capital", {}),
        "signal_summary": {
            "total": total_sigs, "buy_call": buy_call,
            "buy_put": buy_put, "avg_confidence": avg_conf,
        },
        "performance": {
            "win_rate":      perf.get("win_rate", 0.0),
            "expectancy":    perf.get("expectancy", 0.0),
            "total_pnl":     perf.get("total_pnl", 0.0),
            "closed_trades": perf.get("closed_trades", 0),
        },
        "open_count":   len(data.get("open_trades",   [])),
        "closed_count": len(data.get("closed_trades", [])),
    })

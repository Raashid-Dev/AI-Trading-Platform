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
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List
from collections import defaultdict
from typing import Optional

import requests as _requests

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

    # ── Start trading loop as a daemon thread ─────────────────
    # Running inside the server process guarantees logs are visible
    # and eliminates the "silent bash background process" failure mode.
    import threading
    try:
        from main import live_loop
        mock = os.getenv("TRADING_MODE", "mock").lower() != "live"
        t = threading.Thread(target=live_loop, args=(mock,), daemon=True, name="trading-loop")
        t.start()
        log.info("Trading loop thread started  mock=%s  pid=%s", mock, os.getpid())
    except Exception as exc:
        log.error("Failed to start trading loop thread: %s", exc)

    log.info("Server started (watcher + heartbeat ready)")


# ── News ─────────────────────────────────────────────────────
import re as _re

_news_cache: Dict[str, Any] = {"items": [], "fetched_at": None}
_NEWS_TTL = 300   # 5 minutes

RSS_FEEDS = [
    ("Economic Times", "https://economictimes.indiatimes.com/markets/stocks/rss.cms"),
    ("ET Markets",     "https://economictimes.indiatimes.com/markets/rss.cms"),
    ("Live Mint",      "https://www.livemint.com/rss/markets"),
]

def _rss_news() -> List[Dict]:
    """Fetch and normalise articles from RSS feeds."""
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"}
    for source, url in RSS_FEEDS:
        try:
            r = _requests.get(url, headers=headers, timeout=8)
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:8]:
                title   = (item.findtext("title")       or "").strip()
                link    = (item.findtext("link")         or "").strip()
                pub     = (item.findtext("pubDate")      or "").strip()
                summary = (item.findtext("description")  or "").strip()
                summary = _re.sub(r"<[^>]+>", "", summary)[:300]
                if title:
                    items.append({
                        "title":     title,
                        "link":      link,
                        "published": pub,
                        "summary":   summary,
                        "source":    source,
                        "image":     None,
                    })
        except Exception as exc:
            log.warning("RSS fetch failed  source=%s  err=%s", source, exc)
    return items


def _finnhub_market_news() -> List[Dict]:
    """General market news from Finnhub (if key configured)."""
    try:
        from engine.finnhub_client import get_market_news
        raw = get_market_news("general")
        out = []
        for n in raw:
            if not n.get("headline"):
                continue
            out.append({
                "title":     n["headline"],
                "link":      n.get("url", ""),
                "published": datetime.utcfromtimestamp(n.get("datetime", 0)).isoformat() + "Z",
                "summary":   n.get("summary", "")[:300],
                "source":    n.get("source", "Finnhub"),
                "image":     n.get("image"),
            })
        return out[:20]
    except Exception as e:
        log.warning("Finnhub market news error: %s", e)
        return []


def _fetch_all_news() -> List[Dict]:
    """Merge Finnhub + RSS, deduplicate by title prefix."""
    finnhub_items = _finnhub_market_news()
    rss_items     = _rss_news()
    merged        = finnhub_items + rss_items

    seen, out = set(), []
    for item in merged:
        key = item["title"][:60].lower().strip()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out[:40]


@app.get("/news")
def get_news() -> Dict:
    global _news_cache
    now = time.time()
    if _news_cache["fetched_at"] is None or (now - _news_cache["fetched_at"]) > _NEWS_TTL:
        items = _fetch_all_news()
        if items:
            _news_cache = {"items": items, "fetched_at": now}
        elif not _news_cache["items"]:
            _news_cache["fetched_at"] = now
    ts = _news_cache.get("fetched_at")
    return {
        "items":      _news_cache["items"],
        "fetched_at": datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else None,
    }


@app.get("/news/company/{symbol}")
def get_company_news(symbol: str) -> Dict:
    """Company-specific news from Finnhub for a given symbol (e.g. TCS)."""
    try:
        from engine.finnhub_client import get_company_news as _cn
        raw = _cn(symbol.upper())
        items = []
        for n in raw:
            if not n.get("headline"):
                continue
            items.append({
                "title":     n["headline"],
                "link":      n.get("url", ""),
                "published": datetime.utcfromtimestamp(n.get("datetime", 0)).isoformat() + "Z",
                "summary":   n.get("summary", "")[:300],
                "source":    n.get("source", "Finnhub"),
                "image":     n.get("image"),
            })
        return {"items": items, "symbol": symbol.upper()}
    except Exception as e:
        log.warning("Company news error %s: %s", symbol, e)
        return {"items": [], "symbol": symbol.upper(), "error": str(e)}


# ── Fundamentals ─────────────────────────────────────────────
# Static quarterly revenue (FY25 actuals as baseline)
_STATIC_REVENUE = {
    "RELIANCE":  [{"q":"Q1 FY25","rev":231971,"net":15138},{"q":"Q2 FY25","rev":235481,"net":16563},{"q":"Q3 FY25","rev":243042,"net":18540},{"q":"Q4 FY25","rev":264678,"net":19407}],
    "TCS":       [{"q":"Q1 FY25","rev":62613,"net":12040},{"q":"Q2 FY25","rev":63973,"net":11909},{"q":"Q3 FY25","rev":63973,"net":12380},{"q":"Q4 FY25","rev":63437,"net":12224}],
    "INFY":      [{"q":"Q1 FY25","rev":38994,"net":6368},{"q":"Q2 FY25","rev":40986,"net":6506},{"q":"Q3 FY25","rev":41764,"net":6806},{"q":"Q4 FY25","rev":40925,"net":7033}],
    "HDFCBANK":  [{"q":"Q1 FY25","rev":68431,"net":16175},{"q":"Q2 FY25","rev":71455,"net":16821},{"q":"Q3 FY25","rev":73957,"net":17654},{"q":"Q4 FY25","rev":75390,"net":17617}],
    "ICICIBANK": [{"q":"Q1 FY25","rev":38765,"net":10708},{"q":"Q2 FY25","rev":40499,"net":11792},{"q":"Q3 FY25","rev":41510,"net":11792},{"q":"Q4 FY25","rev":43170,"net":12630}],
}

_STATIC_META = {
    "RELIANCE":  {"fullName":"Reliance Industries Ltd","sector":"Conglomerate","pe":26.8,"pbv":2.4,"divYield":0.3,"marketCap":"17.4L Cr","description":"India's largest company by market cap, spanning O2C, telecom (Jio), and retail."},
    "TCS":       {"fullName":"Tata Consultancy Services","sector":"IT Services","pe":23.1,"pbv":11.8,"divYield":1.8,"marketCap":"8.7L Cr","description":"India's largest IT services company; consistent dividend payer with global presence."},
    "INFY":      {"fullName":"Infosys Limited","sector":"IT Services","pe":21.5,"pbv":7.4,"divYield":2.1,"marketCap":"6.5L Cr","description":"Second largest Indian IT firm; strong in cloud, digital and enterprise AI services."},
    "HDFCBANK":  {"fullName":"HDFC Bank Limited","sector":"Private Banking","pe":17.3,"pbv":2.8,"divYield":1.2,"marketCap":"12.1L Cr","description":"India's largest private sector bank by assets."},
    "ICICIBANK": {"fullName":"ICICI Bank Limited","sector":"Private Banking","pe":16.8,"pbv":3.1,"divYield":0.8,"marketCap":"8.6L Cr","description":"Fast-growing private bank with strong retail, SME, and digital banking presence."},
    "NIFTY":     {"fullName":"NIFTY 50 Index","sector":"Broad Market","pe":22.4,"pbv":3.8,"divYield":1.2,"description":"Benchmark index of 50 large-cap NSE-listed companies across 13 sectors."},
    "BANKNIFTY": {"fullName":"Bank Nifty Index","sector":"Banking","pe":14.2,"pbv":2.3,"divYield":1.8,"description":"Index of the most liquid and large-cap banking stocks listed on NSE."},
}


@app.get("/fundamentals/{symbol}")
def get_fundamentals(symbol: str) -> Dict:
    """
    Live fundamentals for a symbol.
    Returns: Finnhub live metrics (PE, 52w, yield, etc.) merged with static baseline.
    Falls back to static data gracefully if Finnhub is unavailable.
    """
    sym = symbol.upper()
    meta = _STATIC_META.get(sym, {})

    # Try Finnhub for live metrics
    live_metrics = {}
    live_revenue  = []
    live_earnings = []
    finnhub_ok    = False

    try:
        from engine import finnhub_client as fh
        if fh.is_available():
            metrics  = fh.get_metrics_clean(sym)
            earnings = fh.get_earnings(sym)
            q_rev    = fh.get_quarterly_revenue(sym)

            if metrics:
                live_metrics = metrics
                finnhub_ok   = True
            if earnings:
                live_earnings = earnings
            if q_rev:
                live_revenue = q_rev
    except Exception as e:
        log.warning("Finnhub fundamentals error for %s: %s", sym, e)

    # Merge: Finnhub values override static where available
    def _first(*vals):
        for v in vals:
            if v is not None:
                return v
        return None

    return {
        "symbol":     sym,
        "source":     "finnhub+static" if finnhub_ok else "static",
        "finnhub_ok": finnhub_ok,
        "meta": {
            "fullName":   meta.get("fullName", sym),
            "sector":     meta.get("sector"),
            "description":meta.get("description"),
            "marketCap":  meta.get("marketCap"),
        },
        "metrics": {
            "pe":       _first(live_metrics.get("pe"),       meta.get("pe")),
            "pbv":      _first(live_metrics.get("pbv"),      meta.get("pbv")),
            "divYield": _first(live_metrics.get("divYield"), meta.get("divYield")),
            "52wHigh":  live_metrics.get("52wHigh"),
            "52wLow":   live_metrics.get("52wLow"),
            "eps":      live_metrics.get("eps"),
            "beta":     live_metrics.get("beta"),
            "roe":      live_metrics.get("roe"),
            "netMargin":live_metrics.get("netMargin"),
            "revenueGrowth": live_metrics.get("revenueGrowth"),
        },
        "revenue":  live_revenue  or _STATIC_REVENUE.get(sym, []),
        "earnings": live_earnings,
    }


# ── Chart OHLCV endpoint ──────────────────────────────────────
_CHART_TICKERS = {
    "NIFTY":     "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "RELIANCE":  "RELIANCE.NS",
    "TCS":       "TCS.NS",
    "INFY":      "INFY.NS",
    "HDFCBANK":  "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
}
_CHART_CACHE: Dict[str, Any] = {}
_CHART_TTL = {
    "1m": 30, "5m": 60, "15m": 120, "30m": 180,
    "60m": 600, "1d": 3600, "1wk": 86400,
}
_VALID_INTERVALS = {"1m", "5m", "15m", "30m", "60m", "1d", "1wk"}
_VALID_PERIODS   = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y"}


@app.get("/chart/{symbol}")
def get_chart(symbol: str, interval: str = "5m", period: str = "1d"):
    """
    OHLCV candlestick data for lightweight-charts.
    Returns: { candles: [{time, open, high, low, close}], volume, ema9, ema21, vwap, latest }
    """
    sym    = symbol.upper()
    ticker = _CHART_TICKERS.get(sym)
    if not ticker:
        raise HTTPException(404, f"Unknown symbol: {sym}")

    interval = interval if interval in _VALID_INTERVALS else "5m"
    period   = period   if period   in _VALID_PERIODS   else "1d"

    cache_key = f"{sym}:{interval}:{period}"
    now_ts    = time.time()
    cached    = _CHART_CACHE.get(cache_key)
    ttl       = _CHART_TTL.get(interval, 300)

    if cached and (now_ts - cached["ts"]) < ttl:
        return cached["data"]

    try:
        import yfinance as yf
        import pandas as pd

        df = yf.download(ticker, interval=interval, period=period,
                         progress=False, auto_adjust=True)
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)

        if df is None or df.empty:
            raise HTTPException(503, f"No data from yfinance for {sym}")

        close   = df["Close"]
        ema9s   = close.ewm(span=9,  adjust=False).mean()
        ema21s  = close.ewm(span=21, adjust=False).mean()

        # VWAP (cumulative intraday — only for sub-day intervals)
        intraday = interval not in ("1d", "1wk")
        if intraday and "Volume" in df.columns:
            typical  = (df["High"] + df["Low"] + df["Close"]) / 3
            cum_vol  = df["Volume"].cumsum().replace(0, float("nan"))
            cum_tvp  = (typical * df["Volume"]).cumsum()
            vwap_ser = cum_tvp / cum_vol
        else:
            vwap_ser = pd.Series([float("nan")] * len(df), index=df.index)

        candles, volume, ema9_out, ema21_out, vwap_out = [], [], [], [], []

        for idx in df.index:
            row  = df.loc[idx]
            o    = float(row.get("Open",  row["Close"]))
            h    = float(row.get("High",  row["Close"]))
            l    = float(row.get("Low",   row["Close"]))
            c    = float(row["Close"])
            v    = float(row.get("Volume", 0) or 0)

            if pd.isna(c) or c <= 0:
                continue

            # lightweight-charts needs Unix seconds
            if hasattr(idx, "timestamp"):
                ts = int(idx.timestamp())
            else:
                ts = int(pd.Timestamp(idx).timestamp())

            candles.append({"time": ts, "open": round(o, 2), "high": round(h, 2),
                            "low": round(l, 2), "close": round(c, 2)})
            volume.append({
                "time": ts, "value": v,
                "color": "#10b981" if c >= o else "#ef4444",
            })

            e9  = ema9s.loc[idx]
            e21 = ema21s.loc[idx]
            vw  = vwap_ser.loc[idx]

            if not pd.isna(e9):
                ema9_out.append({"time": ts, "value": round(float(e9), 2)})
            if not pd.isna(e21):
                ema21_out.append({"time": ts, "value": round(float(e21), 2)})
            if not pd.isna(vw) and v > 0:
                vwap_out.append({"time": ts, "value": round(float(vw), 2)})

        latest = {**candles[-1], "volume": volume[-1]["value"]} if candles else None

        result = {
            "symbol":   sym,
            "interval": interval,
            "period":   period,
            "candles":  candles,
            "volume":   volume,
            "ema9":     ema9_out,
            "ema21":    ema21_out,
            "vwap":     vwap_out if intraday else [],
            "latest":   latest,
            "candle_count": len(candles),
        }
        _CHART_CACHE[cache_key] = {"data": result, "ts": now_ts}
        return result

    except HTTPException:
        raise
    except Exception as e:
        log.error("Chart error %s %s %s: %s", sym, interval, period, e, exc_info=True)
        raise HTTPException(503, str(e))


# ── Open Interest endpoint (NSE India) ────────────────────────
_OI_CACHE: Dict[str, Any] = {}
_OI_TTL = 180  # 3 minutes


def _calc_max_pain(strikes: dict) -> float:
    min_pain, result = float("inf"), 0
    for test_k in strikes:
        pain = sum(
            d["ce_oi"] * max(test_k - s, 0) + d["pe_oi"] * max(s - test_k, 0)
            for s, d in strikes.items()
        )
        if pain < min_pain:
            min_pain, result = pain, test_k
    return result


@app.get("/oi/{symbol}")
def get_oi(symbol: str):
    """
    NSE option-chain OI for NIFTY or BANKNIFTY.
    Returns: { pcr, total_ce_oi, total_pe_oi, max_pain, underlying, strikes[] }
    """
    sym = symbol.upper()
    if sym not in ("NIFTY", "BANKNIFTY"):
        return {"error": "OI only available for NIFTY and BANKNIFTY", "symbol": sym}

    now_ts = time.time()
    cached = _OI_CACHE.get(sym)
    if cached and (now_ts - cached["ts"]) < _OI_TTL:
        return cached["data"]

    try:
        # Reuse the NSE session from live_data
        from engine.live_data import _get_nse_session
        sess = _get_nse_session()
        resp = sess.get(
            f"https://www.nseindia.com/api/option-chain-indices?symbol={sym}",
            timeout=12,
        )
        resp.raise_for_status()
        payload = resp.json()

        filtered = payload.get("filtered", {})
        records  = payload.get("records", {})
        ul_price = float(filtered.get("underlyingValue", 0))

        # Build strike-level OI
        strike_map: Dict[float, Dict] = {}
        for item in records.get("data", []):
            strike = float(item.get("strikePrice", 0))
            ce_d   = item.get("CE", {}) or {}
            pe_d   = item.get("PE", {}) or {}
            if strike not in strike_map:
                strike_map[strike] = {"strike": strike, "ce_oi": 0, "pe_oi": 0,
                                      "ce_vol": 0, "pe_vol": 0}
            strike_map[strike]["ce_oi"]  += ce_d.get("openInterest", 0)
            strike_map[strike]["ce_vol"] += ce_d.get("totalTradedVolume", 0)
            strike_map[strike]["pe_oi"]  += pe_d.get("openInterest", 0)
            strike_map[strike]["pe_vol"] += pe_d.get("totalTradedVolume", 0)

        total_ce = sum(v["ce_oi"] for v in strike_map.values())
        total_pe = sum(v["pe_oi"] for v in strike_map.values())
        pcr = round(total_pe / total_ce, 3) if total_ce > 0 else 0.0
        max_pain = _calc_max_pain(strike_map)

        # Near-ATM strikes (±8 strikes)
        all_strikes = sorted(strike_map.keys())
        atm_idx     = min(range(len(all_strikes)),
                         key=lambda i: abs(all_strikes[i] - ul_price))
        near        = all_strikes[max(0, atm_idx - 8): atm_idx + 9]
        strikes_out = [strike_map[s] for s in near]

        data = {
            "symbol":      sym,
            "underlying":  ul_price,
            "pcr":         pcr,
            "total_ce_oi": total_ce,
            "total_pe_oi": total_pe,
            "max_pain":    max_pain,
            "strikes":     strikes_out,
        }
        _OI_CACHE[sym] = {"data": data, "ts": now_ts}
        return data

    except Exception as e:
        log.warning("OI fetch error for %s: %s", sym, e)
        return {"error": str(e), "symbol": sym}


# ── Market status endpoint ────────────────────────────────────
@app.get("/market-status")
def market_status():
    from engine.live_data import get_market_status
    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    return {
        "status": get_market_status(),
        "time_ist": now.strftime("%H:%M:%S"),
        "date_ist": now.strftime("%Y-%m-%d"),
        "weekday":  now.strftime("%A"),
    }
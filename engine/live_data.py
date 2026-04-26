# engine/live_data.py
# Real-time multi-symbol data fetcher — hybrid approach:
#   • Individual stocks  → yfinance (.NS suffix)   [works on cloud IPs]
#   • NSE indices        → NSE India unofficial API [session-based]
#   • Any failure        → graceful fallback to mock for that symbol only
#
# No API key required. Completely free.

import warnings
warnings.filterwarnings("ignore")

import time
import math
import random
import logging
import pytz
from datetime import datetime, time as dtime
from typing import Optional

# ── Market hours (NSE: Mon–Fri 09:15–15:30 IST) ──────────────────────────────
_IST       = pytz.timezone("Asia/Kolkata")
_NSE_OPEN  = dtime(9, 15)
_NSE_CLOSE = dtime(15, 30)


def get_market_status() -> str:
    """Returns 'OPEN', 'PRE_MARKET', 'AFTER_HOURS', or 'CLOSED' (weekend)."""
    now = datetime.now(_IST)
    if now.weekday() >= 5:
        return "CLOSED"
    t = now.time()
    if t < _NSE_OPEN:
        return "PRE_MARKET"
    if t > _NSE_CLOSE:
        return "AFTER_HOURS"
    return "OPEN"


def is_market_open() -> bool:
    return get_market_status() == "OPEN"

log = logging.getLogger("live_data")

# ── Symbol config ─────────────────────────────────────────────────────────────
# type: "stock" uses yfinance .NS | "index" uses NSE India API
SYMBOLS = {
    "NIFTY":     {"type": "index",  "ticker": "^NSEI",        "nse_key": "NIFTY 50"},
    "BANKNIFTY": {"type": "index",  "ticker": "^NSEBANK",     "nse_key": "NIFTY BANK"},
    "RELIANCE":  {"type": "stock",  "ticker": "RELIANCE.NS"},
    "HDFCBANK":  {"type": "stock",  "ticker": "HDFCBANK.NS"},
    "ICICIBANK": {"type": "stock",  "ticker": "ICICIBANK.NS"},
    "INFY":      {"type": "stock",  "ticker": "INFY.NS"},
    "TCS":       {"type": "stock",  "ticker": "TCS.NS"},
}

EMA_SHORT        = 9
EMA_LONG         = 21
AVG_VOL_LOOKBACK = 10
MIN_CANDLES      = 5
INTERVAL         = "5m"
PERIOD           = "1d"


# ── NSE India session helper ──────────────────────────────────────────────────
import requests

_NSE_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.nseindia.com/",
    "Connection":      "keep-alive",
}

_nse_session: Optional[requests.Session] = None
_nse_session_ts: float = 0.0
_NSE_SESSION_TTL = 600  # refresh session every 10 minutes


def _get_nse_session() -> requests.Session:
    global _nse_session, _nse_session_ts
    if _nse_session is None or (time.time() - _nse_session_ts) > _NSE_SESSION_TTL:
        sess = requests.Session()
        sess.headers.update(_NSE_HEADERS)
        try:
            sess.get("https://www.nseindia.com", timeout=8)
            time.sleep(0.5)  # let cookies settle
        except Exception as e:
            log.warning(f"NSE session init failed: {e}")
        _nse_session = sess
        _nse_session_ts = time.time()
    return _nse_session


def _fetch_nse_indices() -> dict:
    """
    Hit NSE's allIndices endpoint and return a dict keyed by nse_key.
    Returns {} on failure.
    """
    try:
        sess = _get_nse_session()
        resp = sess.get(
            "https://www.nseindia.com/api/allIndices",
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return {row["indexSymbol"]: row for row in data}
    except Exception as e:
        log.warning(f"NSE allIndices fetch failed: {e}")
        return {}


def _parse_nse_index(row: dict) -> dict:
    """Convert NSE allIndices row → standard snapshot dict."""
    price      = float(row.get("last", 0))
    prev_close = float(row.get("previousClose", price))
    pct        = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
    high       = float(row.get("dayHigh", price))
    low        = float(row.get("dayLow", price))
    vwap       = (high + low + price) / 3  # approx

    # indices don't have volume; derive synthetic EMAs via random walk from open
    open_  = float(row.get("open", price))
    # simple linear blend for EMA approximation
    ema9   = round(open_ * 0.3 + price * 0.7, 2)
    ema21  = round(open_ * 0.5 + price * 0.5, 2)

    return {
        "price":        round(price, 2),
        "vwap":         round(vwap, 2),
        "ema9":         ema9,
        "ema21":        ema21,
        "volume":       0.0,
        "avg_volume":   0.0,
        "price_change": round(pct, 4),
    }


# ── yfinance stock fetcher ────────────────────────────────────────────────────
def _fetch_yfinance(ticker: str) -> Optional[dict]:
    try:
        import yfinance as yf
        import pandas as pd

        df = yf.download(
            ticker,
            period=PERIOD,
            interval=INTERVAL,
            progress=False,
            auto_adjust=True,
        )
        if hasattr(df.columns, "levels"):
            df.columns = df.columns.get_level_values(0)

        if df.empty or len(df) < MIN_CANDLES:
            log.warning(f"yfinance returned empty/short data for {ticker}")
            return None

        close     = df["Close"]
        latest    = df.iloc[-1]
        prev      = df.iloc[-2]
        price     = float(latest["Close"])
        prev_cl   = float(prev["Close"])
        pct       = (price - prev_cl) / prev_cl * 100

        typical   = (df["High"] + df["Low"] + df["Close"]) / 3
        vol_sum   = df["Volume"].sum()
        vwap      = float((typical * df["Volume"]).sum() / vol_sum) if vol_sum else price

        ema9      = float(close.ewm(span=EMA_SHORT,  adjust=False).mean().iloc[-1])
        ema21     = float(close.ewm(span=EMA_LONG,   adjust=False).mean().iloc[-1])

        subset    = df["Volume"].iloc[-(AVG_VOL_LOOKBACK + 1):-1]
        avg_vol   = float(subset.mean()) if not subset.empty else float(df["Volume"].mean())
        volume    = float(latest["Volume"])
        if volume == 0:
            volume = avg_vol

        return {
            "price":        round(price, 2),
            "vwap":         round(vwap, 2),
            "ema9":         round(ema9, 2),
            "ema21":        round(ema21, 2),
            "volume":       round(volume, 0),
            "avg_volume":   round(avg_vol, 0),
            "price_change": round(pct, 4),
        }
    except Exception as e:
        log.warning(f"yfinance fetch failed for {ticker}: {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────
def fetch_all() -> dict:
    """
    Fetch live data for all symbols.
    Stocks  → yfinance .NS (real-time, free)
    Indices → NSE India unofficial API (real-time, free, requires session)
    Any failure → mock for that symbol only (never blocks the loop)
    """
    results = {}

    # 1. Fetch index data in one call
    nse_rows = _fetch_nse_indices()

    for name, cfg in SYMBOLS.items():
        if cfg["type"] == "index":
            nse_key = cfg.get("nse_key", "")
            row = nse_rows.get(nse_key)
            if row:
                results[name] = _parse_nse_index(row)
                log.info(f"[LIVE] {name} = ₹{results[name]['price']} (NSE API)")
            else:
                # fallback: try yfinance for the index ticker
                snap = _fetch_yfinance(cfg["ticker"])
                if snap:
                    results[name] = snap
                    log.info(f"[LIVE-YF] {name} = ₹{snap['price']} (yfinance)")
                else:
                    results[name] = _mock_fetch_symbol(name)
                    log.warning(f"[MOCK] {name} — both live sources failed")

        else:  # stock
            snap = _fetch_yfinance(cfg["ticker"])
            if snap:
                results[name] = snap
                log.info(f"[LIVE] {name} = ₹{snap['price']} (yfinance)")
            else:
                results[name] = _mock_fetch_symbol(name)
                log.warning(f"[MOCK] {name} — yfinance failed, using mock")

    return results


def fetch_symbol(name: str) -> Optional[dict]:
    cfg = SYMBOLS.get(name)
    if not cfg:
        return None
    all_data = fetch_all()
    return all_data.get(name)


# ── Mock data generator (fallback per-symbol) ─────────────────────────────────
_MOCK_BASE = {
    "NIFTY":     23600.0,
    "BANKNIFTY": 49800.0,
    "RELIANCE":  1290.0,
    "HDFCBANK":  1610.0,
    "ICICIBANK": 1225.0,
    "INFY":      1560.0,
    "TCS":       2420.0,
}

_mock_state: dict = {}


def _mock_fetch_symbol(name: str) -> dict:
    """Synthetic market snapshot — used only as per-symbol fallback."""
    base = _MOCK_BASE.get(name, 1000.0)

    if name not in _mock_state:
        _mock_state[name] = {
            "price":      base,
            "candle":     0,
            "trend":      random.choice([-1, 1]),
            "trend_life": random.randint(3, 10),
        }

    st = _mock_state[name]

    # ── Freeze random walk when market is closed ──────────────
    if not is_market_open() and st["candle"] > 0:
        price = st["price"]
        return {
            "price":        price,
            "vwap":         price,
            "ema9":         price,
            "ema21":        price,
            "volume":       0.0,
            "avg_volume":   0.0,
            "price_change": 0.0,
        }

    st["candle"] += 1
    if st["candle"] % st["trend_life"] == 0:
        st["trend"]      = random.choice([-1, 1])
        st["trend_life"] = random.randint(3, 10)

    drift     = st["trend"] * random.uniform(0.05, 0.3)
    noise     = random.gauss(0, 0.15)
    pct_move  = (drift + noise) / 100.0
    prev_p    = st["price"]
    new_price = round(prev_p * (1 + pct_move), 2)
    st["price"] = new_price

    history = [base]
    for _ in range(19):
        history.append(round(history[-1] * (1 + random.gauss(0, 0.002)), 2))
    history.append(new_price)

    def _ema_list(prices, span):
        k, ema = 2 / (span + 1), prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return round(ema, 2)

    ema9  = _ema_list(history, 9)
    ema21 = _ema_list(history, 21)
    vwap  = round(new_price * (1 + st["trend"] * random.uniform(0.05, 0.2) / 100), 2)

    if name in ("NIFTY", "BANKNIFTY"):
        volume = avg_vol = 500_000.0
    else:
        avg_vol = random.uniform(800_000, 3_000_000)
        volume  = avg_vol * random.uniform(0.7, 1.5)

    return {
        "price":        new_price,
        "vwap":         vwap,
        "ema9":         ema9,
        "ema21":        ema21,
        "volume":       round(volume, 0),
        "avg_volume":   round(avg_vol, 0),
        "price_change": round(pct_move * 100, 4),
    }


def mock_fetch_all() -> dict:
    """Full mock — used only when TRADING_MODE=mock explicitly."""
    return {name: _mock_fetch_symbol(name) for name in _MOCK_BASE}

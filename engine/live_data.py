# engine/live_data.py
# Real-time multi-symbol data fetcher
# Source  : Yahoo Finance via yfinance (free, no API key)
# Install : pip install yfinance pandas
#
# Usage:
#   from engine.live_data import fetch_all, fetch_symbol
#   data = fetch_all()           # all symbols
#   nifty = fetch_symbol("^NSEI")

# engine/live_data.py

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
from typing import Optional
import os
import json
import time

SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INFY": "INFY.NS",
    "TCS": "TCS.NS",
}

INTERVAL = "5m"
PERIOD = "1d"
EMA_SHORT = 9
EMA_LONG = 21
AVG_VOL_LOOKBACK = 10
MIN_CANDLES = 5


 # #region agent log
_DBG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cursor", "debug-afaa4d.log")
def _dbg(message: str, data: dict, *, hypothesisId: str = "H2", runId: str = "pre-fix"):
    try:
        payload = {
            "sessionId": "afaa4d",
            "runId": runId,
            "hypothesisId": hypothesisId,
            "location": "engine/live_data.py",
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(_DBG_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
 # #endregion


def _vwap(df):
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vol_sum = df["Volume"].sum()
    if vol_sum == 0:
        return float(df["Close"].iloc[-1])
    return float((typical * df["Volume"]).sum() / vol_sum)


def _ema(series, span):
    return float(series.ewm(span=span, adjust=False).mean().iloc[-1])


def _avg_volume(df):
    subset = df["Volume"].iloc[-(AVG_VOL_LOOKBACK + 1):-1]
    if subset.empty:
        return float(df["Volume"].mean())
    return float(subset.mean())


def fetch_symbol(ticker: str) -> Optional[dict]:
    import yfinance as yf

    t0 = time.time()
    _dbg("yf_download_begin", {"ticker": ticker, "period": PERIOD, "interval": INTERVAL}, hypothesisId="H2")
    df = yf.download(
        ticker,
        period=PERIOD,
        interval=INTERVAL,
        progress=False,
        auto_adjust=True,
    )
    _dbg("yf_download_end", {"ticker": ticker, "elapsed_s": round(time.time() - t0, 3), "rows": int(getattr(df, "shape", (0, 0))[0] or 0)}, hypothesisId="H2")

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    if df.empty or len(df) < MIN_CANDLES:
        return None

    close = df["Close"]
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(latest["Close"])
    prev_close = float(prev["Close"])

    price_change = ((price - prev_close) / prev_close) * 100

    volume = float(latest["Volume"])
    avg_vol = _avg_volume(df)

    # 🔥 FIX FOR INDEX (CRITICAL)
    if ticker in ["^NSEI", "^NSEBANK"]:
        volume = 0
        avg_vol = 0

    if avg_vol == 0:
        avg_vol = 1

    if volume == 0:
        volume = avg_vol

    vwap = _vwap(df)
    ema9 = _ema(close, EMA_SHORT)
    ema21 = _ema(close, EMA_LONG)

    if pd.isna(vwap):
        vwap = price

    return {
        "price": price,
        "vwap": vwap,
        "ema9": ema9,
        "ema21": ema21,
        "volume": volume,
        "avg_volume": avg_vol,
        "price_change": price_change,
    }


def fetch_all():
    results = {}
    for name, ticker in SYMBOLS.items():
        results[name] = fetch_symbol(ticker)
    return results
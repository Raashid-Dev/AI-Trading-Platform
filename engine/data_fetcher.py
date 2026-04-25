# engine/data_fetcher.py
# Live market data fetcher for NIFTY 50

import warnings
warnings.filterwarnings("ignore")

from typing import Optional
import pandas as pd

# ── Constants ─────────────────────────────────────────────────────

NIFTY_TICKER   = "^NSEI"
CANDLE_INTERVAL = "5m"
FETCH_PERIOD    = "1d"
EMA_SHORT       = 9
EMA_LONG        = 21
MIN_CANDLES     = 5


# ── Indicators ────────────────────────────────────────────────────

def _compute_vwap(df) -> float:
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vol_sum = df["Volume"].sum()

    if vol_sum == 0:
        return float(df["Close"].iloc[-1])  # fallback

    return round(float((typical * df["Volume"]).sum() / vol_sum), 2)


def _compute_ema(series, span: int) -> float:
    return round(float(series.ewm(span=span, adjust=False).mean().iloc[-1]), 2)


def _avg_volume(df, lookback: int = 10) -> float:
    vol_series = df["Volume"].iloc[-(lookback + 1):-1]

    if vol_series.empty:
        return float(df["Volume"].mean())

    return round(float(vol_series.mean()), 0)


# ── Main Fetch ────────────────────────────────────────────────────

def fetch_nifty(ticker: str = NIFTY_TICKER) -> dict:
    try:
        import yfinance as yf
    except ImportError:
        return _error("Run: pip install yfinance pandas")

    try:
        df = yf.download(
            ticker,
            period=FETCH_PERIOD,
            interval=CANDLE_INTERVAL,
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        return _error(f"download failed: {e}")

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    if df.empty or len(df) < MIN_CANDLES:
        return _error("Insufficient market data")

    close  = df["Close"]
    latest = df.iloc[-1]
    prev   = df.iloc[-2]

    price        = round(float(latest["Close"]), 2)
    prev_close   = round(float(prev["Close"]), 2)
    price_change = round(((price - prev_close) / prev_close) * 100, 3)

    # --- indicators ---
    vwap       = _compute_vwap(df)
    ema9       = _compute_ema(close, EMA_SHORT)
    ema21      = _compute_ema(close, EMA_LONG)
    volume     = float(latest["Volume"])
    avg_volume = _avg_volume(df)

    # --- safety fixes ---
    if avg_volume == 0:
        avg_volume = 1

    if volume == 0:
        volume = avg_volume

    if pd.isna(vwap):
        vwap = price

    return {
        "price":        price,
        "vwap":         vwap,
        "ema9":         ema9,
        "ema21":        ema21,
        "volume":       volume,
        "avg_volume":   avg_volume,
        "price_change": price_change,
        "high":         round(float(latest["High"]), 2),
        "low":          round(float(latest["Low"]), 2),
        "open":         round(float(latest["Open"]), 2),
        "candles":      len(df),
        "status":       "ok",
        "error":        None,
    }


def _error(msg: str) -> dict:
    return {
        "price": None, "vwap": None, "ema9": None, "ema21": None,
        "volume": None, "avg_volume": None, "price_change": None,
        "high": None, "low": None, "open": None,
        "candles": 0, "status": "error", "error": msg,
    }


# ── Pipeline Bridge ───────────────────────────────────────────────

def fetch_nifty_for_pipeline(
    india_vix: float,
    oi_bias: int,
    pcr: float,
    fii_net_cr: float,
    crude_change: float,
    dxy_change: float,
    expiry_days_left: int,
) -> Optional[dict]:

    data = fetch_nifty()

    if data["status"] == "error":
        print(f"[data_fetcher] ERROR: {data['error']}")
        return None

    return {
        "price":            data["price"],
        "vwap":             data["vwap"],
        "ema9":             data["ema9"],
        "ema21":            data["ema21"],
        "vol":              data["volume"],
        "avg_vol":          data["avg_volume"],
        "price_change":     data["price_change"],
        "nifty_spot":       data["price"],

        "pcr":              pcr,
        "fii_net_cr":       fii_net_cr,
        "oi_bias":          oi_bias,
        "crude_change":     crude_change,
        "dxy_change":       dxy_change,
        "india_vix":        india_vix,
        "expiry_days_left": expiry_days_left,
    }


# ── Test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    data = fetch_nifty()
    print(data)
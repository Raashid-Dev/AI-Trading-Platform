# engine/finnhub_client.py
# Finnhub API wrapper for Indian stock data
# Free tier: 60 API calls/minute, no credit card required
# Supports: NSE quotes, company news, financials, quarterly earnings
#
# Set env var: FINNHUB_API_KEY=your_key_here
# Register free: https://finnhub.io/register

import os
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

log = logging.getLogger("finnhub")

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
BASE_URL    = "https://finnhub.io/api/v1"

# Finnhub uses NSE: prefix for Indian exchange stocks
NSE_SYMBOLS: Dict[str, str] = {
    "TCS":       "NSE:TCS",
    "RELIANCE":  "NSE:RELIANCE",
    "INFY":      "NSE:INFY",
    "HDFCBANK":  "NSE:HDFCBANK",
    "ICICIBANK": "NSE:ICICIBANK",
}

# Indices not available as NSE: quotes on Finnhub — handled by NSE India API
INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY"}

# In-memory cache: { key: {"data": ..., "ts": float} }
_cache: Dict[str, Dict] = {}


def _is_configured() -> bool:
    return bool(FINNHUB_KEY)


def _get(endpoint: str, params: dict) -> Optional[Any]:
    """Raw GET with error handling and rate-limit awareness."""
    if not _is_configured():
        return None
    params = {**params, "token": FINNHUB_KEY}
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
        if resp.status_code == 429:
            log.warning("Finnhub rate limit hit — backing off 5s")
            time.sleep(5)
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning(f"Finnhub {endpoint} error: {e}")
        return None


def _cached(key: str, ttl: int, fetcher) -> Optional[Any]:
    """Return cached result if fresh, otherwise call fetcher and cache."""
    now = time.time()
    entry = _cache.get(key)
    if entry and (now - entry["ts"]) < ttl:
        return entry["data"]
    data = fetcher()
    if data is not None:
        _cache[key] = {"data": data, "ts": now}
    return _cache.get(key, {}).get("data")


# ─────────────────────────────────────────────────────────────────────────────
# Quotes  (30-second cache — use for price cross-check / backup)
# ─────────────────────────────────────────────────────────────────────────────

def get_quote(name: str) -> Optional[Dict]:
    """
    Real-time quote for a stock.
    Returns: { c: current, h: high, l: low, o: open, pc: prev_close, t: timestamp }
    """
    ticker = NSE_SYMBOLS.get(name)
    if not ticker:
        return None
    return _cached(
        f"quote:{name}", 30,
        lambda: _get("/quote", {"symbol": ticker})
    )


def get_all_quotes() -> Dict[str, Dict]:
    """Fetch quotes for all supported stock symbols."""
    out = {}
    for name in NSE_SYMBOLS:
        q = get_quote(name)
        if q and q.get("c", 0) > 0:
            out[name] = q
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Company News  (15-minute cache per symbol)
# ─────────────────────────────────────────────────────────────────────────────

def get_company_news(name: str, days: int = 5) -> List[Dict]:
    """
    Recent news articles for a specific company.
    Returns list of: { headline, summary, url, datetime, source, image }
    """
    ticker = NSE_SYMBOLS.get(name)
    if not ticker:
        return []

    now      = datetime.utcnow()
    from_str = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    to_str   = now.strftime("%Y-%m-%d")

    def _fetch():
        data = _get("/company-news", {"symbol": ticker, "from": from_str, "to": to_str})
        return data if isinstance(data, list) else None

    result = _cached(f"news:{name}:{from_str}", 900, _fetch)
    return result[:20] if result else []  # cap at 20 per symbol


def get_market_news(category: str = "general") -> List[Dict]:
    """
    General market/financial news. category: 'general' | 'forex' | 'crypto' | 'merger'
    """
    def _fetch():
        data = _get("/news", {"category": category})
        return data if isinstance(data, list) else None

    result = _cached(f"mkt_news:{category}", 900, _fetch)
    return result[:30] if result else []


# ─────────────────────────────────────────────────────────────────────────────
# Basic Financials  (1-hour cache — PE, PBV, 52w high/low, yield)
# ─────────────────────────────────────────────────────────────────────────────

def get_basic_financials(name: str) -> Optional[Dict]:
    """
    Key metrics: 52wHigh/Low, PE, PBV, EPS, dividend yield, beta, market cap.
    Returns the raw Finnhub 'metric' object.
    """
    ticker = NSE_SYMBOLS.get(name)
    if not ticker:
        return None
    return _cached(
        f"metrics:{name}", 3600,
        lambda: _get("/stock/metric", {"symbol": ticker, "metric": "all"})
    )


def get_metrics_clean(name: str) -> Dict:
    """
    Returns a cleaned, frontend-ready metrics dict.
    Falls back to empty dict if Finnhub unavailable.
    """
    raw = get_basic_financials(name)
    if not raw:
        return {}
    m = raw.get("metric", {})
    return {
        "52wHigh":      m.get("52WeekHigh"),
        "52wLow":       m.get("52WeekLow"),
        "pe":           m.get("peBasicExclExtraTTM") or m.get("peTTM"),
        "pbv":          m.get("pbQuarterly") or m.get("pbAnnual"),
        "divYield":     m.get("dividendYieldIndicatedAnnual"),
        "eps":          m.get("epsBasicExclExtraItemsTTM"),
        "beta":         m.get("beta"),
        "marketCapMB":  m.get("marketCapitalization"),  # in millions USD
        "roe":          m.get("roeTTM"),
        "roa":          m.get("roaTTM"),
        "debtEquity":   m.get("totalDebt/totalEquityQuarterly"),
        "revenueGrowth": m.get("revenueGrowthQuarterlyYoy"),
        "netMargin":    m.get("netMarginTTM"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Quarterly Financials  (1-hour cache)
# ─────────────────────────────────────────────────────────────────────────────

def get_reported_financials(name: str, freq: str = "quarterly") -> List[Dict]:
    """
    Actual reported financials from Finnhub (income statement level).
    freq: 'quarterly' | 'annual'
    Returns list of periods, most recent first.
    """
    ticker = NSE_SYMBOLS.get(name)
    if not ticker:
        return []

    def _fetch():
        data = _get("/financials/reported", {"symbol": ticker, "freq": freq})
        if not data:
            return None
        return data.get("data", [])

    result = _cached(f"financials:{name}:{freq}", 3600, _fetch)
    return result[:8] if result else []   # last 8 quarters max


def get_quarterly_revenue(name: str) -> List[Dict]:
    """
    Normalised quarterly revenue + net income for charts.
    Returns: [{ q: 'Q1 FY25', rev: float_crores, net: float_crores }, ...]
    """
    raw = get_reported_financials(name)
    if not raw:
        return []

    out = []
    for period in reversed(raw[:8]):   # chronological order
        report   = period.get("report", {})
        ic       = report.get("ic", [])   # income statement line items

        rev = net = None
        for item in ic:
            concept = (item.get("concept") or "").lower()
            value   = item.get("value")
            if value is None:
                continue
            if "revenue" in concept or "sales" in concept:
                if rev is None:
                    rev = value
            if "netincome" in concept or "net income" in concept or "profit" in concept:
                if net is None:
                    net = value

        if rev is None:
            continue

        # Finnhub reports in native currency (INR for NSE).
        # Convert from raw INR to Crores (÷ 10_000_000)
        def to_cr(v):
            if v is None:
                return None
            # Heuristic: if value > 1e9 it's in rupees; < 1e6 it's already in crores
            if abs(v) > 1e9:
                return round(v / 1e7, 0)
            elif abs(v) > 1e6:
                return round(v / 1e5, 0)
            else:
                return round(v, 0)  # already in crores or similar

        year  = str(period.get("year", ""))
        qtr   = period.get("quarter", "")
        label = f"Q{qtr} FY{year[2:]}" if qtr and year else period.get("period", "?")

        out.append({
            "q":   label,
            "rev": to_cr(rev),
            "net": to_cr(net),
        })

    return out[-4:]   # last 4 quarters for the chart


# ─────────────────────────────────────────────────────────────────────────────
# Earnings (EPS actual vs estimate)
# ─────────────────────────────────────────────────────────────────────────────

def get_earnings(name: str) -> List[Dict]:
    """
    Quarterly EPS: actual vs estimate, surprise %.
    Returns: [{ period, actual, estimate, surprise, surprisePct }, ...]
    """
    ticker = NSE_SYMBOLS.get(name)
    if not ticker:
        return []

    def _fetch():
        data = _get("/stock/earnings", {"symbol": ticker, "limit": 4})
        return data if isinstance(data, list) else None

    result = _cached(f"earnings:{name}", 3600, _fetch)
    return result or []


# ─────────────────────────────────────────────────────────────────────────────
# Company Profile
# ─────────────────────────────────────────────────────────────────────────────

def get_company_profile(name: str) -> Optional[Dict]:
    """Name, logo, industry, market cap, outstanding shares, country."""
    ticker = NSE_SYMBOLS.get(name)
    if not ticker:
        return None
    return _cached(
        f"profile:{name}", 86400,   # cache for 24 hours
        lambda: _get("/stock/profile2", {"symbol": ticker})
    )


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

def is_available() -> bool:
    """Quick check — returns True if Finnhub key is configured and reachable."""
    if not _is_configured():
        return False
    result = _get("/quote", {"symbol": "NSE:TCS"})
    return result is not None and result.get("c", 0) > 0

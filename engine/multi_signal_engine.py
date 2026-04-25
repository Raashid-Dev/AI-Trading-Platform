# engine/multi_signal_engine.py
# Multi-symbol signal pipeline
# Runs score_market() + generate_options_signal() for every symbol
# returned by fetch_all().
#
# Usage:
#   from engine.multi_signal_engine import run_multi_signal_pipeline, build_state_map
#   from engine.live_data import fetch_all, SYMBOLS
#
#   state_map = build_state_map()          # once per session
#   data      = fetch_all()                # every 5 min
#   results   = run_multi_signal_pipeline(data, MANUAL_INPUTS, datetime.now(IST), state_map)

# engine/multi_signal_engine.py

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from engine.market_scorer import score_market
from engine.options_signal import SignalState, generate_options_signal


# ─────────────────────────────────────────────────────────────
# STATE MAP
# ─────────────────────────────────────────────────────────────

def build_state_map(symbols: Optional[Dict] = None) -> Dict[str, SignalState]:
    if symbols is None:
        from engine.live_data import SYMBOLS
        symbols = SYMBOLS
    return {name: SignalState() for name in symbols}


# ─────────────────────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────────────────────

def run_multi_signal_pipeline(
    data_dict: Dict[str, Optional[Dict]],
    manual_inputs: Dict,
    current_time: datetime,
    state_map: Dict[str, SignalState],
) -> Dict[str, Dict]:

    results: Dict[str, Dict] = {}

    for symbol, data in data_dict.items():

        if data is None:
            continue

        if symbol not in state_map:
            state_map[symbol] = SignalState()

        state = state_map[symbol]

        market = score_market(
            pcr=manual_inputs["pcr"],
            fii_net_cr=manual_inputs["fii_net_cr"],
            oi_bias=manual_inputs["oi_bias"],
            price=data["price"],
            vwap=data["vwap"],
            ema9=data["ema9"],
            ema21=data["ema21"],
            vol=data["volume"],
            avg_vol=data["avg_volume"],
            price_change=data["price_change"],
            crude_change=manual_inputs["crude_change"],
            dxy_change=manual_inputs["dxy_change"],
        )

        signal = generate_options_signal(
            direction=market["direction"],
            confidence=market["confidence"],
            india_vix=manual_inputs["india_vix"],
            nifty_spot=data["price"],
            current_time=current_time,
            expiry_days_left=manual_inputs["expiry_days_left"],
            state=state,
        )

        results[symbol] = {
            "direction": market["direction"],
            "confidence": round(market["confidence"], 2),
            "signal": signal["signal"],
            "strike": signal.get("strike"),
            "type": signal.get("type"),
            "score": market["total"],
            "conflict": market["conflict"],
            "reason": signal.get("reason", ""),
            "trend_strength": market.get("trend_strength", "MODERATE"),
        }

    # META (important for VIX logic)
    results["__meta__"] = {
        "india_vix": manual_inputs.get("india_vix")
    }

    return results


# ─────────────────────────────────────────────────────────────
# REGIME LOGIC
# ─────────────────────────────────────────────────────────────

def get_market_regime(results: Dict) -> str:
    nifty = results.get("NIFTY")
    if not nifty:
        return "MIXED"

    if nifty.get("trend_strength") == "WEAK":
        return "RANGE"

    if nifty.get("direction") == "SIDEWAYS":
        return "RANGE"

    if nifty.get("trend_strength") in ("STRONG_BULL", "STRONG_BEAR"):
        return "TREND"

    return "MIXED"


def get_vix_regime(india_vix: Optional[float]) -> str:
    if india_vix is None:
        return "NORMAL"
    if india_vix < 13:
        return "LOW_VOL"
    if india_vix <= 18:
        return "NORMAL"
    return "HIGH_VOL"


# ─────────────────────────────────────────────────────────────
# RANKING
# ─────────────────────────────────────────────────────────────

def rank_signals(results: Dict) -> List[Tuple[str, Dict]]:
    active = [
        (sym, r)
        for sym, r in results.items()
        if not sym.startswith("__") and r["signal"] != "NO_TRADE"
    ]

    for _, r in active:
        r["rank_score"] = round(r["confidence"] * abs(r["score"]), 3)

    return sorted(active, key=lambda x: x[1]["rank_score"], reverse=True)


# ─────────────────────────────────────────────────────────────
# FILTERING (FINAL LOGIC)
# ─────────────────────────────────────────────────────────────

def filter_best_signals(
    ranked: List[Tuple[str, Dict]],
    max_signals: int = 2,
    results: Optional[Dict] = None,
    adaptive_config: Optional[Dict] = None,
) -> List[Tuple[str, Dict]]:

    regime = get_market_regime(results) if results else "MIXED"

    if regime == "RANGE":
        return []

    # ── Base confidence floor (regime + VIX, unchanged) ───────
    min_conf = 0.70 if regime == "MIXED" else 0.60

    meta = (results or {}).get("__meta__", {})
    vix_tier = get_vix_regime(meta.get("india_vix"))

    if vix_tier == "LOW_VOL":
        min_conf = max(min_conf, 0.70)

    elif vix_tier == "HIGH_VOL":
        min_conf = 0.55
        max_signals = 1

    # ── Adaptive override: raise floor, never lower it ────────
    adaptive_min_conf  = (adaptive_config or {}).get("min_confidence", 0.0)
    allow_weak_trend   = (adaptive_config or {}).get("allow_weak_trend", True)
    min_conf           = max(min_conf, adaptive_min_conf)

    filtered = [
        (sym, r)
        for sym, r in ranked
        if r["confidence"] >= min_conf
        and not r["conflict"]
        # static WEAK guard + adaptive override
        and (allow_weak_trend or r.get("trend_strength") != "WEAK")
        and r.get("trend_strength") != "WEAK"
        and abs(r["score"]) >= 8
        and r["confidence"] >= (
            0.55 if r.get("trend_strength") in ("STRONG_BULL", "STRONG_BEAR") else 0.65
        )
    ]

    best = filtered[:max_signals]

    # attach regime info for dashboard
    for _, r in best:
        r["regime"]   = regime
        r["vix_tier"] = vix_tier

    return best


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────

def print_live_dashboard(signals: List[Tuple[str, Dict]]):

    print("\n====================================")
    print("          LIVE SIGNALS")
    print("====================================")

    if not signals:
        print("No actionable signals this candle.")
        print("====================================")
        return

    first = signals[0][1]
    print(f"Regime : {first.get('regime')}")
    print(f"VIX    : {first.get('vix_tier')}")
    print("------------------------------------")

    for i, (sym, r) in enumerate(signals, 1):
        print(f"{i}. {sym}")
        print(f"   Direction : {r['direction']}")
        print(f"   Confidence: {r['confidence']}")
        print(f"   Score     : {r['score']}")
        print(f"   Signal    : {r['signal']} {r['strike']} {r['type']}")
        print()

    print("====================================")
import logging
import os
import sys
import time
import json
import random
from datetime import datetime, timedelta
import pytz

# ── Structured logging (PART 4) ───────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log_main = logging.getLogger("trading-loop")

from engine import score_market, SignalState, generate_options_signal, TradeLog
from engine import run_multi_signal_pipeline, build_state_map, fetch_all
from engine.multi_signal_engine import rank_signals, filter_best_signals, print_live_dashboard
from engine.performance_tracker import evaluate_trade

IST = pytz.timezone("Asia/Kolkata")

MOCK_INTERVAL_SECONDS  = 5
LIVE_INTERVAL_SECONDS  = 300   # 5 minutes
MAX_TRADES_PER_SESSION = 5
INITIAL_CAPITAL        = 100_000
RISK_PER_TRADE         = 0.02   # 2 % of current capital per trade
MAX_EXPOSURE           = 3.0    # max sum of risk_multipliers across open trades
SECTOR_COOLDOWN_CANDLES = 2     # candles to block a sector after weak exit

SECTOR_MAP = {
    "NIFTY":     "INDEX",
    "BANKNIFTY": "BANK",
    "HDFCBANK":  "BANK",
    "ICICIBANK": "BANK",
    "INFY":      "IT",
    "TCS":       "IT",
    "RELIANCE":  "ENERGY",
}
# ── ADAPTIVE CONFIG (updated every 10 candles from optimizer) ──
adaptive_config = {
    "min_confidence": 0.60,   # raised automatically if low-conf trades underperform
    "allow_weak_trend": True, # set to False when WEAK trend loses consistently
}

LIVE_STATE_FILE = os.getenv("LIVE_STATE_FILE", "live_state.json")

MOCK_START_PRICE = 22350.0
EXPIRY_DAYS_LEFT = 3

DIVIDER = "─" * 52

# ── MANUAL INPUTS (update once per session) ────────────────────
MANUAL_INPUTS = {
    "pcr":              0.85,
    "fii_net_cr":       620.0,
    "oi_bias":          1,
    "crude_change":    -0.3,
    "dxy_change":      -0.1,
    "india_vix":        13.4,
    "expiry_days_left": EXPIRY_DAYS_LEFT,
}


# ── CORE PIPELINE ─────────────────────────────────────

def run_signal_pipeline(
    pcr, fii_net_cr, oi_bias,
    price, vwap, ema9, ema21,
    vol, avg_vol, price_change,
    crude_change, dxy_change,
    india_vix, nifty_spot,
    current_time, expiry_days_left, state
):
    market = score_market(
        pcr=pcr,
        fii_net_cr=fii_net_cr,
        oi_bias=oi_bias,
        price=price,
        vwap=vwap,
        ema9=ema9,
        ema21=ema21,
        vol=vol,
        avg_vol=avg_vol,
        price_change=price_change,
        crude_change=crude_change,
        dxy_change=dxy_change,
    )

    signal = generate_options_signal(
        direction=market["direction"],
        confidence=market["confidence"],
        india_vix=india_vix,
        nifty_spot=nifty_spot,
        current_time=current_time,
        expiry_days_left=expiry_days_left,
        state=state,
    )

    signal["market"] = market
    return signal


# ── HELPERS ─────────────────────────────────────

def _direction_tag(d):
    return {
        "BULLISH": "↑ BULLISH",
        "BEARISH": "↓ BEARISH",
        "SIDEWAYS": "→ SIDEWAYS"
    }.get(d, d)


def print_market(m):
    filled = int(m["confidence"] * 10)
    conf_bar = "█" * filled + "░" * (10 - filled)
    print(f"  Market   : {_direction_tag(m['direction'])} [{conf_bar}] {m['confidence']:.2f}")
    print(f"  Score    : {m['total']:+d}/20   Conflict: {m['conflict']}")


def print_signal(r):
    if r["signal"] == "NO_TRADE":
        print(f"  Signal   : NO_TRADE — {r['reason']}")
    else:
        print(
            f"  Signal   : {r['signal']} "
            f"strike={r['strike']} type={r['type']} conf={r['confidence']:.2f}"
        )


def print_outcome(trade):
    tags = {
        "WIN": "✓ WIN",
        "LOSS": "✗ LOSS",
        "NEUTRAL": "~ NEUTRAL",
        None: "pending..."
    }
    print(
        f"  Outcome  : 3c={tags[trade.get('outcome_3')]} "
        f"10c={tags[trade.get('outcome_10')]}"
    )


# ── CORE CANDLE PROCESSING ─────────────────────────────────────

def _process_candle(candle_num, now, inputs, state, log, price_history, open_trades, source):

    price = inputs["price"]
    price_history.append(price)

    print(f"\n{DIVIDER}")
    print(f"Candle #{candle_num} {now.strftime('%H:%M:%S IST')} [{source}]")
    print(DIVIDER)

    print(f"Nifty : {round(price, 2)}  VIX: {round(inputs['india_vix'], 2)}")

    result = run_signal_pipeline(**inputs, current_time=now, state=state)

    print_market(result["market"])
    print_signal(result)

    # ── ENTRY CONFIRMATION LOGIC (FINAL) ──

    if not hasattr(state, "pending_signal"):
        state.pending_signal = None

    if result["signal"] != "NO_TRADE":

        if state.pending_signal is None:
            # Store first signal → wait for confirmation
            state.pending_signal = (result, price, candle_num)

        else:
            prev_result, prev_price, prev_candle = state.pending_signal

            if (
                result["market"]["direction"] == prev_result["market"]["direction"]
                and result["market"]["confidence"] >= 0.55
            ):
                trade = log.add(prev_result, entry_price=prev_price)
                open_trades.append((trade, prev_candle))

            # Reset after second candle
            state.pending_signal = None

    else:
        # Reset if signal disappears
        state.pending_signal = None

    # ── TRADE EVALUATION ──

    still_open = []

    for trade, idx in open_trades:
        future_prices = price_history[idx:]
        evaluate_trade(trade, future_prices)

        print_outcome(trade)

        if trade["status"] != "EVALUATED":
            still_open.append((trade, idx))

    return still_open


# ── LIVE LOOP ─────────────────────────────────────

# --- NEW HELPER FUNCTION ---
def get_risk_multiplier(confidence: float) -> float:
    if confidence >= 0.75:
        return 1.5
    elif confidence >= 0.65:
        return 1.0
    else:
        return 0.7


def print_capital_status(cs: dict) -> None:
    """cs = log.get_capital_state()"""
    print(f"\n  ===== CAPITAL =====")
    print(f"  Balance  : ₹{cs['capital']:>12,.2f}")
    print(f"  Peak     : ₹{cs['max_capital']:>12,.2f}")
    print(f"  Drawdown : {cs['drawdown_pct']:>+.2f}%")
    print(f"  ===================\n")


def live_loop():
    """
    Multi-symbol live trading loop.
    Fetches real data every 5 minutes via yfinance,
    runs the full multi-signal pipeline, ranks and filters
    the best signals, then records trades for top picks.
    """
    state_map     = build_state_map()
    log           = TradeLog()
    last_traded   = {}   # sym → last signal placed ("BUY_CALL" / "BUY_PUT")
    last_price    = {}   # sym → closing price from the previous candle
    early_exit_cd = {}   # sym → candles remaining in early-exit cooldown
    sector_cd     = {}   # sector → candles remaining in sector cooldown
    candle        = 0
    # Capital is owned exclusively by log.capital — no local copy

    print(f"\n{'=' * 52}")
    print(f"{'LIVE MULTI-SIGNAL LOOP':^52}")
    print(f"{'=' * 52}")
    print(f"  Symbols  : {', '.join(state_map.keys())}")
    print(f"  Interval : {LIVE_INTERVAL_SECONDS}s")
    print(f"  Capital  : ₹{log.capital:,.0f}")
    print(f"  India VIX: {MANUAL_INPUTS['india_vix']}")
    print(f"{'=' * 52}\n")

    try:
        while True:
            candle += 1
            now = datetime.now(IST)

            try:   # PART 6 — per-candle safety guard
                # Decrement early-exit cooldowns at the start of each candle
                early_exit_cd = {s: n - 1 for s, n in early_exit_cd.items() if n > 1}
                # --- SECTOR COOLDOWN DECREMENT ---
                sector_cd     = {s: n - 1 for s, n in sector_cd.items() if n > 1}

                print(f"\n{DIVIDER}")
                print(f"Candle #{candle}  {now.strftime('%H:%M:%S IST')}")
                print(DIVIDER)

                # ── 1. Fetch live data ─────────────────────────────────
                print("  Fetching data...", end="", flush=True)
                data = fetch_all()
                fetched = sum(1 for v in data.values() if v is not None)
                print(f" {fetched}/{len(data)} symbols OK")

                # ── 2. Run multi-signal pipeline ───────────────────────
                results = run_multi_signal_pipeline(
                    data, MANUAL_INPUTS, now, state_map
                )

                if not results:
                    print("  No results — market may be closed or all fetches failed.")
                    time.sleep(LIVE_INTERVAL_SECONDS)
                    continue

                # ── 3. Rank + filter ───────────────────────────────────
                ranked = rank_signals(results)
                best   = filter_best_signals(ranked, results=results,
                                             adaptive_config=adaptive_config)

                # ── 4. Store signals in log + print dashboard ──────────
                log.set_latest_signals(best)
                print_live_dashboard(best)

                # ── 5. Record trades for filtered signals ──────────────
                for sym, r in best:
                    if data.get(sym) is None:
                        continue
                    if log.total_trades() >= MAX_TRADES_PER_SESSION:
                        print(f"  [SKIP] {sym} — session cap ({MAX_TRADES_PER_SESSION}) reached")
                        continue
                    if last_traded.get(sym) == r["signal"]:
                        print(f"  [SKIP] {sym} — duplicate {r['signal']}, waiting for direction change")
                        continue
                    if early_exit_cd.get(sym, 0) > 0:
                        print(f"  [SKIP] {sym} — early-exit cooldown ({early_exit_cd[sym]} candles left)")
                        continue
                    # --- FIXED EXPOSURE GUARD ---
                    new_trade_risk   = get_risk_multiplier(r.get("confidence", 0))
                    current_exposure = sum(
                        t.get("allocated_size", t.get("risk_multiplier", 1.0))
                        for t in log.open_trades
                    )
                    if current_exposure + new_trade_risk > MAX_EXPOSURE:
                        print(f"  [SKIP] {sym} — exposure limit "
                              f"({current_exposure:.1f} + {new_trade_risk} > {MAX_EXPOSURE}x)")
                        continue

                    # --- SECTOR COOLDOWN GUARD ---
                    new_sector = SECTOR_MAP.get(sym)
                    if new_sector is not None and new_sector in sector_cd:
                        print(f"  [SKIP] {sym} — sector cooldown "
                              f"({new_sector}, {sector_cd[new_sector]} candles left)")
                        continue

                    # --- FIXED SECTOR FILTER ---
                    new_sector = SECTOR_MAP.get(sym)
                    new_dir    = r["signal"]
                    if new_sector and any(
                        SECTOR_MAP.get(t.get("symbol")) is not None
                        and SECTOR_MAP.get(t.get("symbol")) == new_sector
                        and t.get("signal_type") == new_dir
                        for t in log.open_trades
                    ):
                        print(f"  [SKIP] {sym} — sector conflict "
                              f"({new_sector} already has {new_dir})")
                        continue

                    current_price = data[sym]["price"]
                    prev_price    = last_price.get(sym)

                    # Momentum filter — only enter on confirming price move
                    if prev_price is not None:
                        if r["signal"] == "BUY_CALL" and current_price <= prev_price:
                            print(f"  [SKIP] {sym} — BUY_CALL needs price > prev "
                                  f"({current_price:.2f} <= {prev_price:.2f})")
                            continue
                        if r["signal"] == "BUY_PUT" and current_price >= prev_price:
                            print(f"  [SKIP] {sym} — BUY_PUT needs price < prev "
                                  f"({current_price:.2f} >= {prev_price:.2f})")
                            continue

                    trade = log.add(r, entry_price=current_price, symbol=sym)

                    # ── Capital management (uses log.capital — single source) ──
                    sl_dist = abs(current_price - trade["stop_loss"])
                    if sl_dist > 0:
                        risk_amount = log.capital * RISK_PER_TRADE
                        qty         = round(risk_amount / sl_dist, 4)
                    else:
                        qty = 1.0
                    trade["qty"]          = qty
                    trade["capital_used"] = round(qty * current_price, 2)

                    last_traded[sym] = r["signal"]
                    # PART 4 — structured trade entry log
                    log_main.info(
                        "TRADE_ENTRY  symbol=%s  signal=%s  strike=%s  "
                        "entry=%.2f  conf=%.2f  qty=%.4f  capital_used=%.0f",
                        sym, r["signal"], r.get("strike", "?"),
                        current_price, r.get("confidence", 0), qty, trade["capital_used"],
                    )
                    print(f"  [TRADE] {sym}  {r['signal']}  "
                          f"strike={r['strike']}  entry={current_price:.2f}  "
                          f"qty={qty:.2f}  capital_used=₹{trade['capital_used']:,.0f}")

                # ── 5a. Update price history for next candle ───────────
                for sym, d in data.items():
                    if d is not None:
                        last_price[sym] = d["price"]

                # ── 6. Evaluate open trades ────────────────────────────
                if log.open_trades:
                    price_snapshot = {
                        s: data[s]["price"]
                        for s in data if data[s] is not None
                    }
                    for trade in list(log.open_trades):
                        sym_key = trade.get("symbol", "NIFTY")
                        if sym_key in price_snapshot:
                            sym_result     = results.get(sym_key, {})
                            evaluate_trade(
                                trade,
                                [price_snapshot[sym_key]],
                                new_direction  = sym_result.get("direction"),
                                trend_strength = sym_result.get("trend_strength"),
                            )
                            if trade["status"] == "CLOSED":
                                log.record_close(trade)   # updates log.capital (compound)
                                pnl_pct      = trade.get("total_pnl") or trade.get("pnl_percent") or 0.0
                                capital_used = trade.get("capital_used", 0.0)
                                dollar_pnl   = round((pnl_pct / 100) * capital_used, 2)
                                reason       = trade.get("exit_reason", "?")
                                # PART 4 — structured trade exit log
                                log_main.info(
                                    "TRADE_EXIT  symbol=%s  reason=%s  pnl_pct=%+.3f  "
                                    "dollar_pnl=%+.0f  capital=%.0f",
                                    sym_key, reason, pnl_pct, dollar_pnl, log.capital,
                                )
                                print(f"  [CLOSED] {sym_key}  "
                                      f"exit={reason}  "
                                      f"pnl={pnl_pct:+.3f}%  ₹{dollar_pnl:+,.0f}")
                                if reason in ("NO_MOMENTUM", "TREND_WEAK"):
                                    early_exit_cd[sym_key] = 2
                                    print(f"  [COOLDOWN] {sym_key} blocked for 2 candles ({reason})")
                                    # --- SET SECTOR COOLDOWN ---
                                    _sector = SECTOR_MAP.get(sym_key)
                                    if _sector is not None:
                                        sector_cd[_sector] = SECTOR_COOLDOWN_CANDLES
                                        print(f"  [COOLDOWN] sector {_sector} blocked for "
                                              f"{SECTOR_COOLDOWN_CANDLES} candles ({reason})")

                # ── 7. Candle summary ──────────────────────────────────
                print(log.candle_summary())
                print_capital_status(log.get_capital_state())

                # ── 8. Performance dashboard (every 5 candles) ─────────
                if candle % 5 == 0:
                    print(log.get_dashboard_metrics())
                    print(log.get_exit_analysis_block())

                    d = log.diagnostics()
                    print(f"\n  ===== STRATEGY =====")
                    print(f"  Expectancy    : {d['expectancy']:+.3f}%")
                    pf = d['profit_factor']
                    print(f"  Profit Factor : {pf:.3f}" if pf != float('inf') else "  Profit Factor : ∞")
                    print(f"  Win Streak    : {d['max_win_streak']}")
                    print(f"  Loss Streak   : {d['max_loss_streak']}")
                    print(f"  ====================\n")

                # ── 9. Atomic JSON export (PART 3) ────────────────────
                try:
                    snapshot = log.export_state()
                    _tmp = LIVE_STATE_FILE + ".tmp"
                    with open(_tmp, "w") as _f:
                        json.dump(snapshot, _f, indent=2, default=str)
                    os.replace(_tmp, LIVE_STATE_FILE)   # atomic rename — no partial reads
                except Exception as _e:
                    log_main.warning("State export failed: %s", _e)

                # ── 10. Adaptive config update (every 10 candles) ──────
                if candle % 10 == 0:
                    opt = log.optimize()
                    # Only act when optimizer has enough data (non-default return)
                    if opt.get("confidence_threshold") and opt["confidence_threshold"] != 0.65:
                        adaptive_config["min_confidence"] = opt["confidence_threshold"]
                    elif opt.get("confidence_threshold"):
                        # apply even the default suggestion if it differs from current
                        new_floor = opt["confidence_threshold"]
                        if new_floor != adaptive_config["min_confidence"]:
                            adaptive_config["min_confidence"] = new_floor

                    if opt.get("worst_trend") == "WEAK":
                        adaptive_config["allow_weak_trend"] = False

                    # Print adaptive config state
                    weak_label = "ON" if adaptive_config["allow_weak_trend"] else "OFF"
                    print(f"\n  ===== ADAPTIVE =====")
                    print(f"  Min Conf   : {adaptive_config['min_confidence']:.2f}")
                    print(f"  Weak Trend : {weak_label}")
                    print(f"  ====================\n")


            except Exception as _candle_err:
                log_main.error(
                    "Candle #%d failed — continuing loop  err=%s",
                    candle, _candle_err, exc_info=True,
                )
            time.sleep(LIVE_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\n🛑 Live loop stopped")
        _print_final_summary(log)


def _print_final_summary(log: TradeLog) -> None:
    trades = log.all_trades
    if not trades:
        print("\n  No trades recorded this session.")
        return

    print(f"\n{'=' * 52}")
    print(f"{'SESSION SUMMARY':^52}")
    print(f"{'=' * 52}")
    print(f"  Total trades : {len(trades)}")

    closed = log.evaluated_trades
    if closed:
        wins   = sum(1 for t in closed if t.get("exit_reason") == "TARGET")
        losses = sum(1 for t in closed if t.get("exit_reason") == "SL")
        timed  = sum(1 for t in closed if t.get("exit_reason") == "TIME")
        print(f"  Closed       : {len(closed)}")
        print(f"    TARGET exits : {wins}")
        print(f"    SL exits     : {losses}")
        print(f"    TIME exits   : {timed}")
        if len(closed):
            print(f"  Win rate     : {wins/len(closed):.0%}")
    print(f"{'=' * 52}\n")


# ── MOCK LOOP ─────────────────────────────────────

def mock_loop():
    state = SignalState()
    log = TradeLog()

    price = MOCK_START_PRICE
    candle = 0

    sim_time = datetime.now(IST).replace(hour=9, minute=31, second=0)

    price_history = []
    open_trades = []

    try:
        while True:
            candle += 1

            # ── Regime simulation ──
            regime = (candle // 10) % 3

            if regime == 0:
                drift = 20
            elif regime == 1:
                drift = -20
            else:
                drift = 0

            noise = random.uniform(-10, 10)
            price += drift + noise

            vwap = price - random.uniform(-15, 15)
            ema9 = price - random.uniform(-10, 10)
            ema21 = ema9 - random.uniform(-5, 5)

            inputs = {
                "price": price,
                "nifty_spot": price,
                "vwap": vwap,
                "ema9": ema9,
                "ema21": ema21,
                "vol": random.randint(80000, 150000),
                "avg_vol": 90000,
                "price_change": random.uniform(-0.5, 0.5),
                "crude_change": random.uniform(-0.5, 0.5),
                "dxy_change": random.uniform(-0.5, 0.5),
                "pcr": random.uniform(0.7, 1.3),
                "fii_net_cr": random.randint(-800, 800),
                "oi_bias": random.choice([-1, 0, 1]),
                "india_vix": random.uniform(12, 18),
                "expiry_days_left": 3
            }

            open_trades = _process_candle(
                candle,
                sim_time,
                inputs,
                state,
                log,
                price_history,
                open_trades,
                "MOCK"
            )

            sim_time += timedelta(minutes=5)
            time.sleep(MOCK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\n🛑 Mock simulation stopped")


# ── ENTRY ─────────────────────────────────────

if __name__ == "__main__":
    if "--live" in sys.argv:
        live_loop()
    elif "--mock" in sys.argv:
        mock_loop()
    else:
        print("Usage:")
        print("  python main.py --live    # real yfinance data, multi-symbol")
        print("  python main.py --mock    # simulated data, single-symbol")
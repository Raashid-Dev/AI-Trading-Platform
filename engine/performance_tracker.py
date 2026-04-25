# engine/performance_tracker.py
# Signal Performance Tracker — Full Trade Lifecycle
#
# Tracks BUY_CALL / BUY_PUT signals with:
#   - Stop-loss and profit target evaluation
#   - Candle-by-candle exit scanning
#   - Time-based exit after 10 candles
#   - PnL % calculation
#   - Legacy 3c / 10c outcome windows (preserved for compatibility)

# engine/performance_tracker.py

from datetime import datetime
from typing import Optional, Tuple, List, Dict


# ── Constants ─────────────────────────────────────────────

WIN_THRESHOLD_PCT    = 0.2
TRAIL_TRIGGER_PCT    = 0.4   # price must move this % from entry to activate break-even stop
SHORT_TERM_CANDLES = 3
MEDIUM_TERM_CANDLES = 10
MAX_CANDLES = 10

# Confidence tiers
_EXIT_TIERS = [
    (0.75, 0.40, 1.00),
    (0.65, 0.30, 0.60),
    (0.55, 0.25, 0.50),
]

_DEFAULT_SL_PCT = 0.30
_DEFAULT_TARGET_PCT = 0.60


# ── FIXED FUNCTION (PYTHON 3.9 SAFE) ──────────────────────
def _get_exit_params(confidence: Optional[float]) -> Tuple[float, float]:
    if confidence is None:
        return _DEFAULT_SL_PCT, _DEFAULT_TARGET_PCT

    for min_conf, sl, tgt in _EXIT_TIERS:
        if confidence >= min_conf:
            return sl, tgt

    return _DEFAULT_SL_PCT, _DEFAULT_TARGET_PCT


# ── CREATE TRADE ──────────────────────────────────────────
def create_trade(signal: Dict, entry_price: float) -> Dict:
    """
    Build a fully-standardised trade dict.
    position_size is UNIFIED with risk_multiplier — one field drives both
    confidence scaling and partial-exit tracking.
    """
    sig_type   = signal["signal"]
    confidence = signal.get("confidence")
    conf_val   = confidence if confidence is not None else 0.0   # safe numeric

    sl_pct, target_pct = _get_exit_params(confidence)

    if entry_price <= 0:
        entry_price = 1.0   # safety guard — prevents ZeroDivisionError downstream

    if sig_type == "BUY_CALL":
        stop_loss = round(entry_price * (1 - sl_pct / 100), 2)
        target    = round(entry_price * (1 + target_pct / 100), 2)
    else:
        stop_loss = round(entry_price * (1 + sl_pct / 100), 2)
        target    = round(entry_price * (1 - target_pct / 100), 2)

    risk_mult = (
        1.5 if conf_val >= 0.75 else
        0.7 if conf_val <  0.65 else
        1.0
    )

    return {
        # ── identity (standard fields always present) ──────
        "symbol":         "UNKNOWN",           # overwritten by TradeLog.add()
        "signal_type":    sig_type,
        "confidence":     round(conf_val, 4),
        "trend_strength": signal.get("trend_strength") or "MODERATE",
        "timestamp":      datetime.now().isoformat(),

        # ── pricing ───────────────────────────────────────
        "entry_price":  entry_price,
        "strike":       signal.get("strike") or 0,
        "exit_price":   None,

        # ── exit parameters ───────────────────────────────
        "sl_pct":       sl_pct,
        "target_pct":   target_pct,
        "stop_loss":    stop_loss,
        "target":       target,
        "exit_reason":  None,
        "pnl_percent":  None,

        # ── legacy window outcomes (kept for compatibility) ─
        "exit_price_3":  None,
        "exit_price_10": None,
        "outcome_3":     None,
        "outcome_10":    None,

        # ── lifecycle ──────────────────────────────────────
        "status":       "OPEN",
        "candles_held": 0,

        # ── SPLIT sizing model ─────────────────────────────
        # risk_multiplier : read-only label of the confidence tier
        # allocated_size  : initial capital weight — never changes after entry
        # remaining_size  : current exposure — halved on each partial exit
        # position_size   : alias for remaining_size (backward compat)
        #
        # final_pnl  = pnl_percent * remaining_size
        # partial_pnl= pnl_at_trigger * (allocated_size - new_remaining_size)
        "risk_multiplier": risk_mult,
        "allocated_size":  risk_mult,
        "remaining_size":  risk_mult,
        "position_size":   risk_mult,   # ← kept for any legacy reads

        # ── PnL accumulators ──────────────────────────────
        "partial_pnl": 0.0,
        "final_pnl":   0.0,
        "total_pnl":   0.0,

        # ── partial / trailing state ───────────────────────
        "trailing_active":    False,
        "partial_exit":       False,
        "partial_exit_price": None,
    }


# ── PNL ───────────────────────────────────────────────────
def _calc_pnl(signal_type: str, entry: float, exit_price: float) -> float:
    if entry == 0:
        return 0.0
    if signal_type == "BUY_CALL":
        return round(((exit_price - entry) / entry) * 100, 3)
    return round(((entry - exit_price) / entry) * 100, 3)


# ── CLASSIFIER ─────────────────────────────────────────────
def _classify(signal_type: str, entry: float, exit_price: float) -> str:
    pct = ((exit_price - entry) / entry) * 100

    if signal_type == "BUY_CALL":
        if pct > WIN_THRESHOLD_PCT:
            return "WIN"
        if pct < -WIN_THRESHOLD_PCT:
            return "LOSS"
        return "NEUTRAL"

    if signal_type == "BUY_PUT":
        if pct < -WIN_THRESHOLD_PCT:
            return "WIN"
        if pct > WIN_THRESHOLD_PCT:
            return "LOSS"
        return "NEUTRAL"

    return "NEUTRAL"


# ── EXIT LOGIC ─────────────────────────────────────────────
def _close_trade(trade, price, reason):
    trade["exit_price"]  = round(price, 2)
    trade["exit_reason"] = reason
    trade["pnl_percent"] = _calc_pnl(
        trade["signal_type"],
        trade["entry_price"],
        price,
    )
    # final_pnl uses remaining_size (current exposure after any partial exits)
    remaining = trade.get("remaining_size", trade.get("position_size", 1.0))
    trade["final_pnl"] = round((trade["pnl_percent"] or 0.0) * remaining, 3)
    trade["total_pnl"] = round((trade.get("partial_pnl") or 0.0) + trade["final_pnl"], 3)
    trade["status"]    = "CLOSED"


def _scan_exit(trade, future_prices):

    if trade["status"] == "CLOSED":
        return

    sl = trade["stop_loss"]
    tgt = trade["target"]
    sig = trade["signal_type"]

    entry = trade["entry_price"]

    for price in future_prices[:MAX_CANDLES]:

        # ── Trigger zone: trailing stop + partial exit (both at 0.4%) ──
        if not trade["trailing_active"]:
            triggered = (
                (sig == "BUY_CALL" and price >= entry * (1 + TRAIL_TRIGGER_PCT / 100)) or
                (sig == "BUY_PUT"  and price <= entry * (1 - TRAIL_TRIGGER_PCT / 100))
            )
            if triggered:
                # Booked portion = allocated_size - new_remaining_size
                allocated  = trade.get("allocated_size",  trade.get("position_size", 1.0))
                old_remain = trade.get("remaining_size",  allocated)
                new_remain = round(old_remain * 0.5, 4)
                booked     = round(allocated - new_remain, 4)   # portion being closed now

                trade["stop_loss"]          = entry
                trade["trailing_active"]    = True
                trade["partial_exit"]       = True
                trade["partial_exit_price"] = round(price, 2)
                # partial_pnl = pnl_at_trigger * booked_portion
                trade["partial_pnl"]        = round(_calc_pnl(sig, entry, price) * booked, 3)
                trade["remaining_size"]     = new_remain
                trade["position_size"]      = new_remain   # keep alias in sync
                sl = entry

        if sig == "BUY_CALL":
            if price >= tgt:
                _close_trade(trade, price, "TARGET")
                return
            if price <= sl:
                _close_trade(trade, price, "SL")
                return

        else:
            if price <= tgt:
                _close_trade(trade, price, "TARGET")
                return
            if price >= sl:
                _close_trade(trade, price, "SL")
                return

    if len(future_prices) >= MAX_CANDLES:
        _close_trade(trade, future_prices[MAX_CANDLES - 1], "TIME")


# ── EARLY EXIT ─────────────────────────────────────────────
MOMENTUM_CANDLES    = 2      # candles before momentum check fires
MOMENTUM_MOVE_PCT   = 0.2    # minimum favourable move required (%)

def _check_early_exits(
    trade,
    future_prices,
    new_direction: Optional[str] = None,
    trend_strength: Optional[str] = None,
) -> bool:
    """
    Run early-exit checks in priority order BEFORE SL/Target scanning.
    Closes the trade in-place and returns True if an early exit fired.

    Checks (in order):
        1. REVERSAL     — opposite direction signal for the same symbol
        2. TREND_WEAK   — trend_strength degraded to WEAK after entry
        3. NO_MOMENTUM  — price hasn't moved +MOMENTUM_MOVE_PCT% after
                          MOMENTUM_CANDLES candles
    """
    if trade["status"] == "CLOSED":
        return False

    sig   = trade["signal_type"]
    entry = trade["entry_price"]

    # ── 1. Reversal ────────────────────────────────────────
    if new_direction is not None:
        opposite = (
            (sig == "BUY_CALL" and new_direction == "BEARISH") or
            (sig == "BUY_PUT"  and new_direction == "BULLISH")
        )
        if opposite:
            price = future_prices[-1] if future_prices else entry
            _close_trade(trade, price, "REVERSAL")
            return True

    # ── 2. Weak trend ──────────────────────────────────────
    if trend_strength == "WEAK":
        price = future_prices[-1] if future_prices else entry
        _close_trade(trade, price, "TREND_WEAK")
        return True

    # ── 3. No momentum ────────────────────────────────────
    if trade["candles_held"] >= MOMENTUM_CANDLES and future_prices:
        current = future_prices[-1]
        moved   = (
            (sig == "BUY_CALL" and current >= entry * (1 + MOMENTUM_MOVE_PCT / 100)) or
            (sig == "BUY_PUT"  and current <= entry * (1 - MOMENTUM_MOVE_PCT / 100))
        )
        if not moved:
            _close_trade(trade, current, "NO_MOMENTUM")
            return True

    return False


# ── EVALUATION ─────────────────────────────────────────────
def evaluate_trade(trade, future_prices,
                   new_direction: Optional[str] = None,
                   trend_strength: Optional[str] = None):

    trade["candles_held"] += 1

    # Early exits run first — if one fires, skip SL/Target scan
    if not _check_early_exits(trade, future_prices, new_direction, trend_strength):
        _scan_exit(trade, future_prices)

    entry = trade["entry_price"]
    sig = trade["signal_type"]

    if len(future_prices) >= 3 and trade["outcome_3"] is None:
        p = future_prices[2]
        trade["outcome_3"] = _classify(sig, entry, p)

    if len(future_prices) >= 10 and trade["outcome_10"] is None:
        p = future_prices[9]
        trade["outcome_10"] = _classify(sig, entry, p)

    return trade


# ── WIN RATE ───────────────────────────────────────────────
def get_win_rate(trades, window="3"):

    if window == "exit":
        closed = [t for t in trades if t["status"] == "CLOSED"]

        if not closed:
            return {"win_rate": 0}

        wins = sum(1 for t in closed if t["exit_reason"] == "TARGET")
        total = len(closed)

        return {
            "win_rate": round(wins / total, 2),
            "total": total,
        }

    key = f"outcome_{window}"
    evaluated = [t for t in trades if t.get(key)]

    if not evaluated:
        return {"win_rate": 0}

    wins = sum(1 for t in evaluated if t[key] == "WIN")
    total = len(evaluated)

    return {
        "win_rate": round(wins / total, 2),
        "total": total,
    }


# ── TRADE NORMALISER (UI-ready copy, never mutates original) ──
def _normalize_trade(trade: Dict) -> Dict:
    """
    Map internal trade keys to frontend-friendly names.
    All fields guaranteed present; None replaced with safe defaults.
    """
    alloc  = trade.get("allocated_size")  or trade.get("risk_multiplier") or 1.0
    remain = trade.get("remaining_size")  or trade.get("position_size")   or alloc
    return {
        "symbol":         trade.get("symbol")         or "UNKNOWN",
        "signal":         trade.get("signal_type")    or "",
        "confidence":     trade.get("confidence")     or 0.0,
        "trend":          trade.get("trend_strength") or "MODERATE",
        "entry":          trade.get("entry_price")    or 0.0,
        "exit":           trade.get("exit_price")     or 0.0,
        "status":         trade.get("status")         or "OPEN",
        "exit_reason":    trade.get("exit_reason")    or "",
        "pnl":            trade.get("total_pnl")      or 0.0,
        "allocated_size": round(alloc,  4),
        "remaining_size": round(remain, 4),
        "timestamp":      trade.get("timestamp")      or "",
        # extra fields useful for a detail view
        "strike":         trade.get("strike")         or 0,
        "stop_loss":      trade.get("stop_loss")      or 0.0,
        "target":         trade.get("target")         or 0.0,
        "candles_held":   trade.get("candles_held")   or 0,
        "partial_exit":   trade.get("partial_exit")   or False,
        "partial_pnl":    trade.get("partial_pnl")    or 0.0,
        "final_pnl":      trade.get("final_pnl")      or 0.0,
    }


# ── TRADE LOG ──────────────────────────────────────────────
class TradeLog:

    def __init__(self):
        self.trades: List[Dict] = []

        # ── Capital state (single source of truth) ─────────
        self.capital:     float = 100_000.0
        self.max_capital: float = 100_000.0
        self.drawdown:    float = 0.0      # fraction, e.g. -0.05 = -5 %

        # ── Latest filtered signals from the pipeline ──────
        # Stored as List[Dict] with "symbol" merged in (JSON-serialisable)
        self.latest_signals: List[Dict] = []

        # ── Trade list cache (avoid O(n) scans every call) ─
        self._cache_valid:  bool       = False
        self._open_cache:   List[Dict] = []
        self._closed_cache: List[Dict] = []

        # ── Per-candle analytics / diagnostics cache ───────
        self._analytics_cache:    Optional[Dict] = None
        self._diagnostics_cache:  Optional[Dict] = None

    # ── cache helpers ──────────────────────────────────────
    def _invalidate_cache(self) -> None:
        """Call whenever trades change; clears all derived caches."""
        self._cache_valid      = False
        self._analytics_cache  = None
        self._diagnostics_cache = None

    def _rebuild_cache(self) -> None:
        self._open_cache   = [t for t in self.trades if t["status"] == "OPEN"]
        self._closed_cache = [t for t in self.trades if t["status"] == "CLOSED"]
        self._cache_valid  = True

    # ── signal helpers ─────────────────────────────────────
    def set_latest_signals(self, signals: List) -> None:
        """
        Store the filtered signal list from filter_best_signals.
        Expected input: List[Tuple[str, Dict]]  (sym, result_dict)
        Flattened to List[Dict] with "symbol" key merged in.
        """
        self.latest_signals = [
            {"symbol": sym, **{k: (v if v is not None else "") for k, v in r.items()}}
            for sym, r in (signals or [])
        ]

    def get_signal_summary(self) -> Dict:
        """Compact summary of the latest signal batch."""
        sigs  = self.latest_signals
        total = len(sigs)
        buy_call = sum(1 for s in sigs if s.get("signal") == "BUY_CALL")
        buy_put  = sum(1 for s in sigs if s.get("signal") == "BUY_PUT")
        confs    = [float(s.get("confidence") or 0.0) for s in sigs]
        avg_conf = round(sum(confs) / total, 4) if total else 0.0
        return {
            "total":          total,
            "buy_call":       buy_call,
            "buy_put":        buy_put,
            "avg_confidence": avg_conf,
        }

    def add(self, signal: Dict, entry_price: float, symbol: str = "UNKNOWN") -> Dict:
        trade = create_trade(signal, entry_price)
        # Ensure all standard fields are always present
        trade["symbol"]         = symbol
        trade["timestamp"]      = datetime.now().isoformat()
        trade["trend_strength"] = trade.get("trend_strength") or signal.get("trend_strength", "MODERATE")
        self.trades.append(trade)
        self._invalidate_cache()
        return trade

    def record_close(self, trade: Dict) -> None:
        """
        Call exactly once when a trade status becomes CLOSED.
        Updates capital using compound formula and refreshes cache.
        """
        pnl = trade.get("total_pnl") or trade.get("pnl_percent") or 0.0
        self.capital = self.capital * (1 + pnl / 100)
        if self.capital > self.max_capital:
            self.max_capital = self.capital
        # drawdown stored as fraction (negative when below peak)
        self.drawdown = (self.capital - self.max_capital) / self.max_capital if self.max_capital else 0.0
        self._invalidate_cache()

    # ── capital helpers ────────────────────────────────────
    def get_capital_state(self) -> Dict:
        """Single authoritative capital snapshot for main.py and API."""
        return {
            "capital":      round(self.capital, 2),
            "max_capital":  round(self.max_capital, 2),
            "drawdown_pct": round(self.drawdown * 100, 2),
        }

    def equity_metrics(self) -> Dict:
        """Alias kept for backward compatibility."""
        cs = self.get_capital_state()
        return {
            "capital":     cs["capital"],
            "max_capital": cs["max_capital"],
            "drawdown":    cs["drawdown_pct"],
        }

    def diagnostics(self) -> dict:
        if self._diagnostics_cache is not None:
            return self._diagnostics_cache

        closed = self.evaluated_trades
        if not closed:
            return {
                "expectancy":      0.0,
                "profit_factor":   0.0,
                "max_win_streak":  0,
                "max_loss_streak": 0,
            }

        pnl_values = [t.get("total_pnl") or t.get("pnl_percent") or 0.0 for t in closed]
        wins   = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p <= 0]

        avg_win  = sum(wins)   / len(wins)   if wins   else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        win_rate = len(wins) / len(pnl_values)

        expectancy    = round(avg_win * win_rate + avg_loss * (1 - win_rate), 3)
        total_profit  = sum(wins)
        total_loss    = abs(sum(losses))
        profit_factor = round(total_profit / total_loss, 3) if total_loss else float("inf")

        # Streak calculation — single pass
        max_win_streak = max_loss_streak = cur_win = cur_loss = 0
        for p in pnl_values:
            if p > 0:
                cur_win  += 1; cur_loss = 0
            else:
                cur_loss += 1; cur_win  = 0
            max_win_streak  = max(max_win_streak,  cur_win)
            max_loss_streak = max(max_loss_streak, cur_loss)

        result = {
            "expectancy":      expectancy,
            "profit_factor":   profit_factor,
            "max_win_streak":  max_win_streak,
            "max_loss_streak": max_loss_streak,
        }
        self._diagnostics_cache = result
        return result

    def candle_summary(self) -> str:
        """
        One-line status string for printing after every candle.
        Shows open/closed counts, win rate, and cumulative total_pnl.
        """
        open_trades = self.open_trades
        open_c      = len(open_trades)
        closed      = self.evaluated_trades
        closed_c    = len(closed)

        exposure = round(sum(t.get("allocated_size", t.get("risk_multiplier", 1.0)) for t in open_trades), 2)

        if not closed:
            return (f"  Open: {open_c} (exposure: {exposure}x)  Closed: 0  "
                    f"Win Rate: —  Total PnL: 0.00")

        wins      = sum(1 for t in closed if t.get("exit_reason") == "TARGET")
        win_rate  = wins / closed_c
        total_pnl = sum(
            t.get("total_pnl") or t.get("pnl_percent") or 0.0
            for t in closed
        )
        return (f"  Open: {open_c} (exposure: {exposure}x)  Closed: {closed_c}  "
                f"Win Rate: {win_rate:.0%}  Total PnL: {total_pnl:+.3f}")

    def evaluate(self, trade, future_prices):
        return evaluate_trade(trade, future_prices)

    def win_rate(self, window="3"):
        return get_win_rate(self.trades, window)

    def exit_stats(self):
        return get_win_rate(self.trades, "exit")

    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def all_trades(self) -> List[Dict]:
        return self.trades

    @property
    def evaluated_trades(self) -> List[Dict]:
        if not self._cache_valid:
            self._rebuild_cache()
        return self._closed_cache

    @property
    def open_trades(self) -> List[Dict]:
        if not self._cache_valid:
            self._rebuild_cache()
        return self._open_cache

    # ── JSON export (frontend / API) ───────────────────────

    # PART 9 — cap closed trades in-memory and in export to prevent unbounded growth
    MAX_CLOSED_TRADES = 500

    def export_state(self) -> Dict:
        """
        Pure-dict snapshot — no print(), fully JSON-serialisable.
        All None values replaced with safe defaults via _normalize_trade.
        Shape matches the frontend contract:
          { capital, signals, open_trades, closed_trades, performance, diagnostics }
        Closed trades are capped at the last MAX_CLOSED_TRADES entries.
        """
        # PART 9 — trim oldest closed trades to bound memory
        closed = self.evaluated_trades
        if len(closed) > self.MAX_CLOSED_TRADES:
            closed = closed[-self.MAX_CLOSED_TRADES:]
            # Also prune the backing store so it doesn't grow indefinitely
            self.trades = [t for t in self.trades if t["status"] == "OPEN"] + \
                          [t for t in self.trades if t["status"] == "CLOSED"][-self.MAX_CLOSED_TRADES:]
            self._invalidate_cache()

        return {
            "capital":       self.get_capital_state(),
            "signals":       self.latest_signals,
            "open_trades":   [_normalize_trade(t) for t in self.open_trades],
            "closed_trades": [_normalize_trade(t) for t in closed],
            "performance":   self.analytics(),
            "diagnostics":   self.diagnostics(),
        }

    def analytics(self) -> dict:
        """
        Return a summary of closed-trade performance metrics.
        Result is cached per invalidation cycle — recomputed only when
        a trade is added or closed, not on every method call.
        """
        if self._analytics_cache is not None:
            return self._analytics_cache

        closed = self.evaluated_trades
        total  = len(self.trades)

        if not closed:
            return {
                "total_trades": total,
                "closed_trades": 0,
                "win_rate":   0.0,
                "avg_pnl":    0.0,
                "avg_win":    0.0,
                "avg_loss":   0.0,
                "max_drawdown": 0.0,
                "total_pnl":  0.0,
            }

        pnl_values = [t.get("total_pnl") or t.get("pnl_percent") or 0.0 for t in closed]

        wins   = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p <= 0]

        # Cumulative drawdown: largest peak-to-trough drop in running PnL
        peak = running = max_dd = 0.0
        for p in pnl_values:
            running += p
            if running > peak:
                peak = running
            dd = peak - running
            if dd > max_dd:
                max_dd = dd

        # ── Exit reason distribution ──────────────────────────
        EXIT_REASONS = ["TARGET", "SL", "TIME",
                        "NO_MOMENTUM", "REVERSAL", "TREND_WEAK"]

        exit_distribution: Dict = {}
        for reason in EXIT_REASONS:
            bucket     = [t for t in closed if t.get("exit_reason") == reason]
            bucket_pnl = [t.get("total_pnl") or t.get("pnl_percent") or 0.0
                          for t in bucket]
            bucket_wins = [p for p in bucket_pnl if p > 0]
            n = len(bucket)
            exit_distribution[reason] = {
                "count":    n,
                "pct":      round(n / len(closed), 2) if closed else 0.0,
                "win_rate": round(len(bucket_wins) / n, 2) if n else 0.0,
                "avg_pnl":  round(sum(bucket_pnl) / n, 3) if n else 0.0,
            }

        result = {
            "total_trades":  total,
            "closed_trades": len(closed),
            "win_rate":      round(len(wins) / len(closed), 2),
            "avg_pnl":       round(sum(pnl_values) / len(closed), 3),
            "avg_win":       round(sum(wins) / len(wins), 3)     if wins   else 0.0,
            "avg_loss":      round(sum(losses) / len(losses), 3) if losses else 0.0,
            "max_drawdown":  round(max_dd, 3),
            "total_pnl":     round(sum(pnl_values), 3),
            "high_conf_trades":   len([t for t in closed if (t.get("confidence") or 0) >= 0.70]),
            "high_conf_win_rate": round(
                sum(1 for t in closed
                    if (t.get("confidence") or 0) >= 0.70
                    and (t.get("total_pnl") or t.get("pnl_percent") or 0) > 0)
                / max(1, len([t for t in closed if (t.get("confidence") or 0) >= 0.70])),
                2
            ),
            "expectancy": round(
                (len(wins) / len(closed)) * (sum(wins) / len(wins) if wins else 0.0)
                + (len(losses) / len(closed)) * (sum(losses) / len(losses) if losses else 0.0),
                3
            ),
            "exit_distribution": exit_distribution,
        }
        self._analytics_cache = result   # cache until next trade event
        return result

    def get_dashboard_metrics(self) -> str:
        """
        Return a formatted performance block for periodic printing.
        Delegates to analytics() — no duplicate computation.

        Example output:
            ===== PERFORMANCE (12 trades) =====
            Win Rate       :  58%
            Avg Win        :  +0.812%
            Avg Loss       :  -0.344%
            Expectancy     :  +0.328%
            Max Drawdown   :  -1.240%
            Total PnL      :  +4.150%
            High Conf W/R  :  67%  (6 trades)
            ===================================
        """
        m = self.analytics()

        if m["closed_trades"] == 0:
            return (
                "\n===== PERFORMANCE =====\n"
                "  No closed trades yet.\n"
                "=======================\n"
            )

        hdr    = f"===== PERFORMANCE ({m['closed_trades']} closed) ====="
        border = "=" * len(hdr)

        lines = [
            f"\n{hdr}",
            f"  Win Rate       : {m['win_rate']:.0%}",
            f"  Avg Win        : {m['avg_win']:+.3f}%",
            f"  Avg Loss       : {m['avg_loss']:+.3f}%",
            f"  Expectancy     : {m['expectancy']:+.3f}%",
            f"  Max Drawdown   : -{m['max_drawdown']:.3f}%",
            f"  Total PnL      : {m['total_pnl']:+.3f}%",
            f"  High Conf W/R  : {m['high_conf_win_rate']:.0%}"
            f"  ({m['high_conf_trades']} trades ≥ 0.70 conf)",
            border,
        ]
        return "\n".join(lines)

    def get_exit_analysis_block(self) -> str:
        """
        Return a formatted exit-reason breakdown block.

        Example:
            ===== EXIT ANALYSIS (8 closed) =====
            TARGET       :  50% | Win Rate 100% | Avg +0.900%
            SL           :  25% | Win Rate   0% | Avg -0.400%
            NO_MOMENTUM  :  12% | Win Rate  33% | Avg -0.100%
            REVERSAL     :   6% | Win Rate   0% | Avg -0.300%
            TREND_WEAK   :   6% | Win Rate  50% | Avg +0.050%
            TIME         :   0% | Win Rate   —  | Avg    —
            =====================================
        """
        m      = self.analytics()
        closed = m["closed_trades"]

        if closed == 0:
            return "\n===== EXIT ANALYSIS =====\n  No closed trades yet.\n=========================\n"

        dist = m["exit_distribution"]
        hdr  = f"===== EXIT ANALYSIS ({closed} closed) ====="

        lines = [f"\n{hdr}"]
        for reason, d in dist.items():
            if d["count"] == 0:
                lines.append(f"  {reason:<14}:   0% | Win Rate   — | Avg    —")
            else:
                lines.append(
                    f"  {reason:<14}: {d['pct']:>3.0%} "
                    f"| Win Rate {d['win_rate']:>3.0%} "
                    f"| Avg {d['avg_pnl']:+.3f}%"
                )
        lines.append("=" * len(hdr))
        return "\n".join(lines)

    # ── OPTIMIZER ──────────────────────────────────────────────

    def optimize(self) -> dict:
        """
        Analyse closed trades and return a dict of suggested strategy
        parameter adjustments.  Pure read — never modifies any trade.

        Returns
        -------
        {
            "confidence_threshold": float,
            "best_trend":           str,
            "worst_trend":          str,
            "dominant_loss_reason": str,
            "notes":                str,
        }
        """
        closed = self.evaluated_trades

        # ── Guard: nothing to analyse ─────────────────────────
        if not closed:
            return {
                "confidence_threshold": 0.65,
                "best_trend":           "UNKNOWN",
                "worst_trend":          "UNKNOWN",
                "dominant_loss_reason": "UNKNOWN",
                "notes":                "No closed trades yet — run more candles before optimising.",
            }

        def _bucket_stats(trades: List[dict]) -> dict:
            """Win rate + avg PnL for a list of trade dicts."""
            if not trades:
                return {"count": 0, "win_rate": 0.0, "avg_pnl": 0.0}
            pnl_vals  = [t.get("total_pnl") or t.get("pnl_percent") or 0.0 for t in trades]
            wins      = [p for p in pnl_vals if p > 0]
            return {
                "count":    len(trades),
                "win_rate": round(len(wins) / len(trades), 3),
                "avg_pnl":  round(sum(pnl_vals) / len(trades), 3),
            }

        # ── A. Confidence buckets ──────────────────────────────
        high_conf = [t for t in closed if (t.get("confidence") or 0.0) >= 0.70]
        mid_conf  = [t for t in closed
                     if 0.60 <= (t.get("confidence") or 0.0) < 0.70]
        low_conf  = [t for t in closed if (t.get("confidence") or 0.0) < 0.60]

        conf_stats = {
            "high": _bucket_stats(high_conf),
            "mid":  _bucket_stats(mid_conf),
            "low":  _bucket_stats(low_conf),
        }

        # ── B. Trend strength buckets ──────────────────────────
        TREND_GROUPS: Dict[str, List[str]] = {
            "STRONG": ["STRONG_BULL", "STRONG_BEAR"],
            "MODERATE": ["MODERATE"],
            "WEAK":   ["WEAK"],
        }

        trend_stats: Dict[str, dict] = {}
        for group, labels in TREND_GROUPS.items():
            bucket = [t for t in closed
                      if t.get("trend_strength") in labels]
            trend_stats[group] = _bucket_stats(bucket)

        # ── C. Exit reason counts ──────────────────────────────
        EARLY_EXITS = {"REVERSAL", "NO_MOMENTUM", "TREND_WEAK"}
        exit_counts: Dict[str, int] = {}
        for t in closed:
            reason = t.get("exit_reason") or "UNKNOWN"
            exit_counts[reason] = exit_counts.get(reason, 0) + 1

        early_total = sum(exit_counts.get(r, 0) for r in EARLY_EXITS)
        exit_counts["EARLY"] = early_total

        # ── Derive suggestions ─────────────────────────────────
        notes: List[str] = []

        # Confidence threshold
        suggested_conf = 0.65   # default
        low_wr  = conf_stats["low"]["win_rate"]
        high_wr = conf_stats["high"]["win_rate"]

        if conf_stats["low"]["count"] > 0 and low_wr < 0.40:
            suggested_conf = 0.65
            notes.append(
                f"Low-conf win rate is {low_wr:.0%} — raise threshold to ≥ 0.65."
            )
        if conf_stats["high"]["count"] > 0 and high_wr > 0.60:
            suggested_conf = max(suggested_conf, 0.70)
            notes.append(
                f"High-conf win rate is {high_wr:.0%} — bias entries toward ≥ 0.70 confidence."
            )
        if conf_stats["mid"]["count"] > 0 and conf_stats["mid"]["win_rate"] < 0.45:
            suggested_conf = max(suggested_conf, 0.68)
            notes.append("Mid-conf bucket underperforming — consider tightening to 0.68+.")

        # Best / worst trend
        scored_trends = {
            g: s["avg_pnl"] for g, s in trend_stats.items() if s["count"] > 0
        }
        best_trend  = max(scored_trends, key=scored_trends.get) if scored_trends else "UNKNOWN"
        worst_trend = min(scored_trends, key=scored_trends.get) if scored_trends else "UNKNOWN"

        if trend_stats.get("WEAK", {}).get("count", 0) > 0:
            weak_wr = trend_stats["WEAK"]["win_rate"]
            if weak_wr < 0.45:
                notes.append(
                    f"WEAK trend win rate is {weak_wr:.0%} — filter out WEAK entries."
                )

        # Dominant loss reason
        loss_reasons = {
            r: c for r, c in exit_counts.items()
            if r not in ("TARGET",)
        }
        dominant_loss = (
            max(loss_reasons, key=loss_reasons.get)
            if loss_reasons else "NONE"
        )

        if dominant_loss == "SL":
            notes.append("SL exits dominate — tighten entry criteria or wait for stronger confirmation.")
        elif dominant_loss == "TIME":
            notes.append("TIME exits dominate — targets may be too aggressive; consider earlier profit-taking.")
        elif dominant_loss in EARLY_EXITS or dominant_loss == "EARLY":
            notes.append("Early exits dominate — check momentum filter or consider wider SL to avoid noise exits.")

        if not notes:
            notes.append("Strategy performing within normal parameters — no immediate changes recommended.")

        return {
            "confidence_threshold": suggested_conf,
            "best_trend":           best_trend,
            "worst_trend":          worst_trend,
            "dominant_loss_reason": dominant_loss,
            "notes":                "  ".join(notes),
            # ── detailed breakdown (for print_optimization) ────
            "_conf_stats":   conf_stats,
            "_trend_stats":  trend_stats,
            "_exit_counts":  exit_counts,
        }

    def print_optimization(self) -> None:
        """Pretty-print the optimizer output to stdout."""
        o = self.optimize()

        closed = self.evaluated_trades
        total  = len(closed)

        hdr    = "===== OPTIMIZER ====="
        border = "=" * len(hdr)

        print(f"\n{hdr}")

        if total == 0:
            print(f"  {o['notes']}")
            print(border)
            return

        print(f"  Trades Analysed : {total}")
        print(f"  Suggested Conf  : {o['confidence_threshold']:.2f}")
        print(f"  Best Trend      : {o['best_trend']}")
        print(f"  Worst Trend     : {o['worst_trend']}")
        print(f"  Loss Driver     : {o['dominant_loss_reason']}")

        # ── Confidence breakdown ───────────────────────────────
        print(f"\n  -- Confidence Buckets --")
        cs = o["_conf_stats"]
        for label, key in [("High (≥0.70)", "high"), ("Mid  (0.60–0.70)", "mid"), ("Low  (<0.60)", "low")]:
            s = cs[key]
            if s["count"] > 0:
                print(f"    {label:<18}: {s['count']:>3} trades  "
                      f"WR {s['win_rate']:.0%}  Avg PnL {s['avg_pnl']:+.3f}%")
            else:
                print(f"    {label:<18}:   0 trades  —")

        # ── Trend breakdown ────────────────────────────────────
        print(f"\n  -- Trend Strength --")
        ts = o["_trend_stats"]
        for group in ("STRONG", "MODERATE", "WEAK"):
            s = ts.get(group, {"count": 0, "win_rate": 0.0, "avg_pnl": 0.0})
            if s["count"] > 0:
                print(f"    {group:<10}: {s['count']:>3} trades  "
                      f"WR {s['win_rate']:.0%}  Avg PnL {s['avg_pnl']:+.3f}%")
            else:
                print(f"    {group:<10}:   0 trades  —")

        # ── Exit reason counts ─────────────────────────────────
        print(f"\n  -- Exit Breakdown --")
        ec = o["_exit_counts"]
        for reason in ("TARGET", "SL", "TIME", "REVERSAL", "NO_MOMENTUM", "TREND_WEAK"):
            cnt = ec.get(reason, 0)
            bar = "▪" * cnt
            print(f"    {reason:<14}: {cnt:>3}  {bar}")

        # ── Notes ──────────────────────────────────────────────
        print(f"\n  Note : {o['notes']}")
        print(border)
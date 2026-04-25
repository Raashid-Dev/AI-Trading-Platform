# config.py
# Central configuration for AI Trading Platform
# Edit these values to tune the system behaviour.

# ── Market Scorer ─────────────────────────────────────────────────────────────

PCR_BULLISH_THRESHOLD  = 0.8    # PCR below this → bullish (+3)
PCR_BEARISH_THRESHOLD  = 1.2    # PCR above this → bearish (-3)

FII_BUY_THRESHOLD      = 500    # FII net buy  > this (₹Cr) → bullish (+3)
FII_SELL_THRESHOLD     = -500   # FII net sell < this (₹Cr) → bearish (-3)

VOLUME_SPIKE_MULTIPLIER = 1.5   # Vol > avg * this → spike detected

SCORE_BULLISH_THRESHOLD = 6     # Total score >= this → BULLISH
SCORE_BEARISH_THRESHOLD = -6    # Total score <= this → BEARISH
SCORE_MAX               = 20    # Used to normalise confidence

# ── Options Signal Engine ─────────────────────────────────────────────────────

MIN_CONFIDENCE          = 0.55  # Below this → NO_TRADE
ITM_CONFIDENCE_TRIGGER  = 0.85  # At or above → use ITM strike

STRIKE_INTERVAL         = 50    # Nifty strike step (points)

MAX_SIGNALS_PER_DAY     = 3     # Hard daily cap (CALL + PUT combined)
SIGNAL_COOLDOWN_MINUTES = 15    # Min gap between same-direction signals

VIX_HARD_LIMIT          = 20    # VIX above this → no trade at all
VIX_EXPIRY_LIMIT        = 16    # VIX above this on expiry day → no trade

# ── Trading Window (IST) ──────────────────────────────────────────────────────

AVOID_OPEN_START        = (9,  15)   # (hour, minute)
AVOID_OPEN_END          = (9,  30)
AVOID_CLOSE_AFTER       = (14, 55)

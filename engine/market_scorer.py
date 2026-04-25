# engine/market_scorer.py

def score_market(
    pcr,
    fii_net_cr,
    oi_bias,
    price,
    vwap,
    ema9,
    ema21,
    vol,
    avg_vol,
    price_change,
    crude_change,
    dxy_change,
):

    s = {}

    # PCR
    if pcr < 0.8:
        s["pcr"] = 3
    elif pcr > 1.2:
        s["pcr"] = -3
    else:
        s["pcr"] = 0

    # FII
    if fii_net_cr > 500:
        s["fii"] = 3
    elif fii_net_cr < -500:
        s["fii"] = -3
    else:
        s["fii"] = 0

    # OI
    s["oi"] = oi_bias * 3

    # VWAP
    s["vwap"] = 4 if price > vwap else -4

    # EMA
    if price > ema9 > ema21:
        s["ema"] = 4
    elif price < ema9 < ema21:
        s["ema"] = -4
    else:
        s["ema"] = 0

    # Trend strength (EMA separation relative to price)
    diff = abs(ema9 - ema21) / price * 100
    if diff < 0.1:
        trend_strength = "WEAK"
    elif ema9 > ema21 and diff > 0.3:
        trend_strength = "STRONG_BULL"
    elif ema9 < ema21 and diff > 0.3:
        trend_strength = "STRONG_BEAR"
    else:
        trend_strength = "MODERATE"

    # 🔥 FIXED VOLUME LOGIC
    if avg_vol > 0 and vol > 1.5 * avg_vol:
        s["vol"] = 2 if price_change > 0 else -2
    else:
        s["vol"] = 0

    # Macro
    if crude_change < 0 and dxy_change < 0:
        s["macro"] = 1
    elif crude_change > 0 and dxy_change > 0:
        s["macro"] = -1
    else:
        s["macro"] = 0

    # Conflict
    major = [s["pcr"], s["fii"], s["oi"]]
    bull = sum(1 for x in major if x > 0)
    bear = sum(1 for x in major if x < 0)
    conflict = bull >= 1 and bear >= 1

    total = sum(s.values())
    confidence = abs(total) / 20

    if conflict:
        return {
            "direction":      "SIDEWAYS",
            "confidence":     min(confidence, 0.35),
            "conflict":       True,
            "scores":         s,
            "total":          total,
            "trend_strength": trend_strength,
        }

    if total >= 4:
        direction = "BULLISH"
    elif total <= -4:
        direction = "BEARISH"
    else:
        direction = "SIDEWAYS"

    return {
        "direction":      direction,
        "confidence":     confidence,
        "conflict":       False,
        "scores":         s,
        "total":          total,
        "trend_strength": trend_strength,
    }
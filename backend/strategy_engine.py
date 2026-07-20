"""Deterministic S001 signal evaluation with hard gates."""

from shariah_gate import check_symbol


def evaluate_s001(symbol: str, bars: list[dict]) -> dict:
    gate = check_symbol(symbol)
    if gate["status"] != "PASS":
        return {"signal": "REJECT", "reason": gate["reason"], "shariah": gate}
    if len(bars) < 200:
        return {"signal": "NO_SIGNAL", "reason": "insufficient_history", "required_bars": 200, "received_bars": len(bars), "shariah": gate}

    closes = [float(bar["close"]) for bar in bars]
    sma50 = sum(closes[-50:]) / 50
    sma200 = sum(closes[-200:]) / 200
    breakout = closes[-1] >= max(closes[-56:-1])
    if sma50 > sma200 and breakout:
        return {"signal": "BUY", "reason": "trend_and_breakout_confirmed", "sma50": sma50, "sma200": sma200, "shariah": gate}
    return {"signal": "NO_SIGNAL", "reason": "strategy_conditions_not_met", "sma50": sma50, "sma200": sma200, "shariah": gate}

"""US strategy path: Tiingo prices plus Zoya compliance, fail-closed."""

from zoya_compliance import check_us_symbol


def evaluate_us_s001(symbol: str, bars: list[dict], *, compliance_override: dict | None = None) -> dict:
    """Evaluate S001; compliance_override is reserved for explicit tests."""
    compliance = compliance_override if compliance_override is not None else check_us_symbol(symbol)
    if compliance.get("status") != "COMPLIANT":
        return {"signal": "REJECT", "reason": "zoya_gate_failed", "compliance": compliance}
    if len(bars) < 200:
        return {"signal": "NO_SIGNAL", "reason": "insufficient_history", "required_bars": 200, "received_bars": len(bars), "compliance": compliance}

    closes = [float(bar["close"]) for bar in bars]
    sma50 = sum(closes[-50:]) / 50
    sma200 = sum(closes[-200:]) / 200
    breakout = closes[-1] >= max(closes[-56:-1])
    signal = "BUY" if sma50 > sma200 and breakout else "NO_SIGNAL"
    return {"signal": signal, "reason": "trend_and_breakout_confirmed" if signal == "BUY" else "strategy_conditions_not_met", "sma50": sma50, "sma200": sma200, "compliance": compliance}

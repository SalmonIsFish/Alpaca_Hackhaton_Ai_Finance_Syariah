"""Local quant agent for rule-based signal evaluation."""

from datetime import date, timedelta

from tiingo_prices import fetch_eod_prices


def _evaluate_s001_signal(bars: list[dict]) -> dict:
    if len(bars) < 200:
        return {"signal": "NO_SIGNAL", "reason": "insufficient_history", "required_bars": 200, "received_bars": len(bars)}

    closes = [float(bar["close"]) for bar in bars]
    sma50 = sum(closes[-50:]) / 50
    sma200 = sum(closes[-200:]) / 200
    breakout = closes[-1] >= max(closes[-56:-1])
    if sma50 > sma200 and breakout:
        return {"signal": "BUY", "reason": "trend_and_breakout_confirmed", "sma50": sma50, "sma200": sma200}
    return {"signal": "NO_SIGNAL", "reason": "strategy_conditions_not_met", "sma50": sma50, "sma200": sma200}


def evaluate_quant(symbol: str) -> dict:
    end_date = date.today()
    start_date = end_date - timedelta(days=320)
    bars, source = fetch_eod_prices(symbol, start_date.isoformat(), end_date.isoformat(), allow_fallback=True)
    strategy = _evaluate_s001_signal(bars)
    close = float(bars[-1]["close"]) if bars else None
    return {
        "agent": "quant",
        "status": "PASS" if strategy.get("signal") == "BUY" else "NO_SIGNAL",
        "symbol": symbol,
        "signal": strategy.get("signal"),
        "reason": strategy.get("reason"),
        "price": close,
        "bars": len(bars),
        "price_source": source,
        "strategy": strategy,
    }

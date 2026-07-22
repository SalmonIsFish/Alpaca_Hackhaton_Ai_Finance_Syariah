"""Watchlist opportunity scanning built on the coordinator gates."""

from agent_coordinator import evaluate_candidate
from agents.quant_agent import evaluate_quant


DEFAULT_WATCHLIST = [
    "AAPL",
    "AMZN",
    "TSLA",
    "CRM",
    "INTC",
    "AMD",
    "ASML",
    "TSM",
    "SHOP",
    "PANW",
    "ANET",
]


def parse_symbols(symbols: str | None) -> list[str]:
    if not symbols:
        return DEFAULT_WATCHLIST
    parsed = []
    for raw_symbol in symbols.replace("\n", ",").split(","):
        symbol = raw_symbol.strip().upper()
        if symbol and symbol not in parsed:
            parsed.append(symbol)
    return parsed[:30] or DEFAULT_WATCHLIST


def scan_opportunities(symbols: str | None = None, *, alert_threshold_pct: float = 3.0) -> dict:
    items = []
    for symbol in parse_symbols(symbols):
        try:
            quant_override = evaluate_quant(symbol, allow_fallback=False, allow_stale_cache=True)
        except Exception as exc:
            items.append(data_error_item(symbol, exc))
            continue
        evaluation = evaluate_candidate(
            symbol=symbol,
            side="BUY",
            quantity=1,
            price=None,
            position_pct=1.0,
            total_exposure_pct=5.0,
            loss_per_trade_pct=0.2,
            daily_loss_pct=0.3,
            orders_today=0,
            quant_override=quant_override,
        )
        agents = evaluation["agent_summary"]
        shariah = agents["shariah"]
        quant = agents["quant"]
        risk = agents["risk"]
        strategy = quant.get("strategy", {})
        items.append(
            {
                "symbol": symbol,
                "decision": evaluation["decision"],
                "ready_for_approval": evaluation["decision"] == "READY_FOR_APPROVAL",
                "blockers": evaluation["blockers"],
                "price": evaluation["price"],
                "notional": evaluation["notional"],
                "shariah_status": shariah.get("status"),
                "shariah_reason": shariah.get("reason"),
                "shariah_market": shariah.get("market"),
                "quant_signal": quant.get("signal"),
                "quant_reason": quant.get("reason"),
                "risk_status": risk.get("status"),
                "price_source": quant.get("price_source"),
                "data_freshness": quant.get("data_freshness"),
                "cache_cached_at": quant.get("cache_cached_at"),
                "cache_age_hours": quant.get("cache_age_hours"),
                "bars": quant.get("bars"),
                "sma50": strategy.get("sma50"),
                "sma200": strategy.get("sma200"),
                "trend_ok": strategy.get("trend_ok"),
                "breakout_ok": strategy.get("breakout_ok"),
                "breakout_level": strategy.get("breakout_level"),
                "breakout_gap_pct": strategy.get("breakout_gap_pct"),
                "alert_threshold_pct": alert_threshold_pct,
                "alert_status": alert_status(strategy, alert_threshold_pct),
                "trigger_price": strategy.get("breakout_level"),
                "distance_to_trigger": distance_to_trigger(evaluation["price"], strategy.get("breakout_level")),
                "watch_status": classify_watch_status(evaluation, strategy),
            }
        )
    return {
        "count": len(items),
        "ready_count": sum(1 for item in items if item["ready_for_approval"]),
        "alert_count": sum(1 for item in items if item.get("alert_status") == "ALERT"),
        "data_error_count": sum(1 for item in items if item.get("watch_status") == "DATA_ERROR"),
        "items": sorted(items, key=opportunity_rank),
    }


def opportunity_rank(item: dict) -> tuple:
    gap = item.get("breakout_gap_pct")
    sortable_gap = gap if gap is not None else -1_000_000
    return (
        not item["ready_for_approval"],
        item.get("watch_status") == "DATA_ERROR",
        item.get("shariah_status") != "PASS",
        item.get("risk_status") != "PASS",
        item.get("trend_ok") is not True,
        item.get("alert_status") != "ALERT",
        item.get("breakout_ok") is not True,
        -sortable_gap,
        item["symbol"],
    )


def classify_watch_status(evaluation: dict, strategy: dict) -> str:
    if evaluation["decision"] == "READY_FOR_APPROVAL":
        return "READY"
    if "shariah_rejected" in evaluation["blockers"] or "risk_rejected" in evaluation["blockers"]:
        return "BLOCKED"
    if strategy.get("trend_ok") is True and strategy.get("breakout_ok") is not True:
        return "NEAR_BREAKOUT"
    return "NOT_READY"


def data_error_item(symbol: str, exc: Exception) -> dict:
    return {
        "symbol": symbol,
        "decision": "BLOCKED",
        "ready_for_approval": False,
        "blockers": ["market_data_unavailable"],
        "price": None,
        "notional": None,
        "shariah_status": None,
        "shariah_reason": None,
        "shariah_market": None,
        "quant_signal": "NO_SIGNAL",
        "quant_reason": "market_data_unavailable",
        "risk_status": None,
        "price_source": "unavailable",
        "data_freshness": "unavailable",
        "cache_cached_at": None,
        "cache_age_hours": None,
        "bars": 0,
        "sma50": None,
        "sma200": None,
        "trend_ok": None,
        "breakout_ok": None,
        "breakout_level": None,
        "breakout_gap_pct": None,
        "alert_threshold_pct": None,
        "alert_status": "DATA_ERROR",
        "trigger_price": None,
        "distance_to_trigger": None,
        "watch_status": "DATA_ERROR",
        "error_type": type(exc).__name__,
        "error_code": getattr(exc, "error_code", None),
        "error_message": str(exc),
        "http_status": getattr(exc, "status_code", None),
        "retry_after": getattr(exc, "retry_after", None),
    }


def alert_status(strategy: dict, threshold_pct: float) -> str:
    gap = strategy.get("breakout_gap_pct")
    if strategy.get("breakout_ok") is True:
        return "TRIGGERED"
    if strategy.get("trend_ok") is True and gap is not None and gap >= -abs(threshold_pct):
        return "ALERT"
    return "NONE"


def distance_to_trigger(price: float | None, trigger_price: float | None) -> float | None:
    if price is None or trigger_price is None:
        return None
    return round(trigger_price - price, 4)

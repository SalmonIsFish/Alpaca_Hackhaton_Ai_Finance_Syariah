"""Coordinate local deterministic agents before paper-order approval."""

from agents.quant_agent import evaluate_quant
from agents.risk_engine import evaluate_risk
from agents.shariah_agent import evaluate_shariah


def evaluate_candidate(
    *,
    symbol: str,
    side: str,
    quantity: int,
    price: float | None,
    position_pct: float,
    total_exposure_pct: float,
    loss_per_trade_pct: float,
    daily_loss_pct: float,
    orders_today: int,
    shariah_override: dict | None = None,
    quant_override: dict | None = None,
) -> dict:
    normalized_symbol = symbol.strip().upper()
    normalized_side = side.strip().upper()

    shariah = shariah_override if shariah_override is not None else evaluate_shariah(normalized_symbol)
    quant = quant_override if quant_override is not None else evaluate_quant(normalized_symbol)
    selected_price = price if price is not None else quant.get("price")
    risk = evaluate_risk(
        position_pct=position_pct,
        total_exposure_pct=total_exposure_pct,
        loss_per_trade_pct=loss_per_trade_pct,
        daily_loss_pct=daily_loss_pct,
        orders_today=orders_today,
    )

    blockers = []
    if normalized_side != "BUY":
        blockers.append("only_buy_side_supported")
    if shariah["status"] != "PASS":
        blockers.append("shariah_rejected")
    if quant.get("signal") != "BUY":
        blockers.append("quant_no_buy_signal")
    if risk["status"] != "PASS":
        blockers.append("risk_rejected")
    if selected_price is None or selected_price <= 0:
        blockers.append("valid_price_required")

    decision = "READY_FOR_APPROVAL" if not blockers else "BLOCKED"
    notional = round(quantity * selected_price, 2) if selected_price else None
    return {
        "symbol": normalized_symbol,
        "side": normalized_side,
        "quantity": quantity,
        "price": selected_price,
        "notional": notional,
        "decision": decision,
        "blockers": blockers,
        "broker_submission": False,
        "agent_summary": {
            "shariah": shariah,
            "quant": quant,
            "risk": risk,
        },
    }

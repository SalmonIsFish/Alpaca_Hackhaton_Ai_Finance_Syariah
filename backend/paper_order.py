"""Prepare, but do not submit, a Moomoo paper order."""

from config import load_settings
from risk_checks import check_order
from shariah_gate import check_symbol


def prepare_paper_order(*, symbol: str, quantity: int, price: float, position_pct: float, total_exposure_pct: float, loss_per_trade_pct: float, daily_loss_pct: float, orders_today: int) -> dict:
    settings = load_settings()
    if settings.moomoo_mode != "paper":
        return {"status": "REJECT", "reason": "paper_mode_required"}
    shariah = check_symbol(symbol)
    if shariah["status"] != "PASS":
        return {"status": "REJECT", "reason": "shariah_gate_failed", "shariah": shariah}
    risk = check_order(
        position_pct=position_pct,
        total_exposure_pct=total_exposure_pct,
        loss_per_trade_pct=loss_per_trade_pct,
        daily_loss_pct=daily_loss_pct,
        orders_today=orders_today,
        limits={
            "max_position_pct": settings.max_position_pct,
            "max_total_exposure_pct": settings.max_total_exposure_pct,
            "max_loss_per_trade_pct": settings.max_loss_per_trade_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_orders_per_day": settings.max_orders_per_day,
        },
    )
    if risk["status"] != "PASS":
        return {"status": "REJECT", "reason": "risk_gate_failed", "risk": risk}
    return {"status": "READY_FOR_APPROVAL", "execution": "PAPER_ONLY", "broker_submission": False, "symbol": symbol, "quantity": quantity, "price": price, "notional": round(quantity * price, 2), "shariah": shariah, "risk": risk}

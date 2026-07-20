"""Deterministic risk engine for paper-order eligibility."""

from risk_checks import check_order


def evaluate_risk(*, position_pct: float, total_exposure_pct: float, loss_per_trade_pct: float, daily_loss_pct: float, orders_today: int) -> dict:
    result = check_order(
        position_pct=position_pct,
        total_exposure_pct=total_exposure_pct,
        loss_per_trade_pct=loss_per_trade_pct,
        daily_loss_pct=daily_loss_pct,
        orders_today=orders_today,
    )
    return {
        "agent": "risk_engine",
        "status": result.get("status"),
        "reason": "risk_limits_passed" if result.get("status") == "PASS" else "risk_limit_failed",
        "details": result,
    }

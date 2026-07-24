"""Deterministic, non-AI risk checks for paper-order preparation."""

MAX_POSITION_PCT = 5.0
MAX_TOTAL_EXPOSURE_PCT = 25.0
MAX_LOSS_PER_TRADE_PCT = 0.5
MAX_DAILY_LOSS_PCT = 1.0
MAX_ORDERS_PER_DAY = 5


def default_limits() -> dict:
    return {
        "max_position_pct": MAX_POSITION_PCT,
        "max_total_exposure_pct": MAX_TOTAL_EXPOSURE_PCT,
        "max_loss_per_trade_pct": MAX_LOSS_PER_TRADE_PCT,
        "max_daily_loss_pct": MAX_DAILY_LOSS_PCT,
        "max_orders_per_day": MAX_ORDERS_PER_DAY,
    }


def check_order(
    *,
    position_pct: float,
    total_exposure_pct: float,
    loss_per_trade_pct: float,
    daily_loss_pct: float,
    orders_today: int,
    limits: dict | None = None,
) -> dict:
    active_limits = {**default_limits(), **(limits or {})}
    checks = {
        "position_ceiling": position_pct <= active_limits["max_position_pct"],
        "total_exposure": total_exposure_pct <= active_limits["max_total_exposure_pct"],
        "loss_per_trade": loss_per_trade_pct <= active_limits["max_loss_per_trade_pct"],
        "daily_loss": daily_loss_pct <= active_limits["max_daily_loss_pct"],
        "daily_order_cap": orders_today < active_limits["max_orders_per_day"],
    }
    return {"status": "PASS" if all(checks.values()) else "REJECT", "checks": checks, "limits": active_limits}

"""Hard-coded, non-AI risk checks for paper-order preparation."""

MAX_POSITION_PCT = 5.0
MAX_TOTAL_EXPOSURE_PCT = 25.0
MAX_LOSS_PER_TRADE_PCT = 0.5
MAX_DAILY_LOSS_PCT = 1.0
MAX_ORDERS_PER_DAY = 5


def check_order(*, position_pct: float, total_exposure_pct: float, loss_per_trade_pct: float, daily_loss_pct: float, orders_today: int) -> dict:
    checks = {
        "position_ceiling": position_pct <= MAX_POSITION_PCT,
        "total_exposure": total_exposure_pct <= MAX_TOTAL_EXPOSURE_PCT,
        "loss_per_trade": loss_per_trade_pct <= MAX_LOSS_PER_TRADE_PCT,
        "daily_loss": daily_loss_pct <= MAX_DAILY_LOSS_PCT,
        "daily_order_cap": orders_today < MAX_ORDERS_PER_DAY,
    }
    return {"status": "PASS" if all(checks.values()) else "REJECT", "checks": checks}

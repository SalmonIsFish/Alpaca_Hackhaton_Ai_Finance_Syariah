"""Verify deterministic risk checks honor configurable limits."""

from risk_checks import check_order


def main() -> None:
    result = check_order(
        position_pct=6.0,
        total_exposure_pct=20.0,
        loss_per_trade_pct=0.4,
        daily_loss_pct=0.9,
        orders_today=4,
    )
    assert result["status"] == "REJECT"
    assert result["checks"]["position_ceiling"] is False
    assert result["limits"]["max_position_pct"] == 5.0

    custom = check_order(
        position_pct=6.0,
        total_exposure_pct=20.0,
        loss_per_trade_pct=0.4,
        daily_loss_pct=0.9,
        orders_today=4,
        limits={
            "max_position_pct": 7.0,
            "max_total_exposure_pct": 25.0,
            "max_loss_per_trade_pct": 0.5,
            "max_daily_loss_pct": 1.0,
            "max_orders_per_day": 5,
        },
    )
    assert custom["status"] == "PASS"
    assert custom["checks"]["position_ceiling"] is True
    assert custom["limits"]["max_position_pct"] == 7.0

    capped_orders = check_order(
        position_pct=1.0,
        total_exposure_pct=1.0,
        loss_per_trade_pct=0.1,
        daily_loss_pct=0.1,
        orders_today=5,
    )
    assert capped_orders["status"] == "REJECT"
    assert capped_orders["checks"]["daily_order_cap"] is False
    print("PASS: risk checks honor default and custom limits.")


if __name__ == "__main__":
    main()

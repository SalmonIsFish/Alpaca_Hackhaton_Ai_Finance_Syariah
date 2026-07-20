"""Exercise the safety gates without submitting an order."""

from paper_order import prepare_paper_order


result = prepare_paper_order(
    symbol="0001",
    quantity=16,
    price=301.00,
    position_pct=5.0,
    total_exposure_pct=10.0,
    loss_per_trade_pct=0.5,
    daily_loss_pct=0.0,
    orders_today=0,
)
print(result)
print("No broker submission was made.")

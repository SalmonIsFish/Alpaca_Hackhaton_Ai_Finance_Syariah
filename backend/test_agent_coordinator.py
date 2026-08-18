"""Verify agent_coordinator composes the option-structure gate without
disturbing the existing equity-only candidate path."""

from agent_coordinator import evaluate_candidate


SHARIAH_PASS = {"agent": "shariah", "status": "PASS", "reason": "symbol_compliant"}
QUANT_BUY = {"agent": "quant", "signal": "BUY", "price": 100.0}


def main() -> None:
    # Existing equity-only behavior must be unaffected when no option_structure
    # is supplied: no "option_structure" key appears in agent_summary at all.
    equity_only = evaluate_candidate(
        symbol="AAPL",
        side="BUY",
        quantity=1,
        price=None,
        position_pct=1.0,
        total_exposure_pct=1.0,
        loss_per_trade_pct=0.1,
        daily_loss_pct=0.1,
        orders_today=0,
        shariah_override=SHARIAH_PASS,
        quant_override=QUANT_BUY,
    )
    assert "option_structure" not in equity_only["agent_summary"]
    assert equity_only["decision"] == "READY_FOR_APPROVAL"

    # A covered call backed by enough owned shares should not block approval.
    covered_call_ready = evaluate_candidate(
        symbol="AAPL",
        side="BUY",
        quantity=1,
        price=None,
        position_pct=1.0,
        total_exposure_pct=1.0,
        loss_per_trade_pct=0.1,
        daily_loss_pct=0.1,
        orders_today=0,
        shariah_override=SHARIAH_PASS,
        quant_override=QUANT_BUY,
        option_structure={"structure": "covered_call", "shares_held": 100, "contracts": 1},
    )
    assert covered_call_ready["decision"] == "READY_FOR_APPROVAL"
    assert covered_call_ready["agent_summary"]["option_structure"]["status"] == "PASS"
    assert "option_structure_rejected" not in covered_call_ready["blockers"]

    # A naked call must block approval even if shariah/quant/risk all pass.
    naked_call_blocked = evaluate_candidate(
        symbol="AAPL",
        side="BUY",
        quantity=1,
        price=None,
        position_pct=1.0,
        total_exposure_pct=1.0,
        loss_per_trade_pct=0.1,
        daily_loss_pct=0.1,
        orders_today=0,
        shariah_override=SHARIAH_PASS,
        quant_override=QUANT_BUY,
        option_structure={"structure": "naked_call"},
    )
    assert naked_call_blocked["decision"] == "BLOCKED"
    assert "option_structure_rejected" in naked_call_blocked["blockers"]
    assert naked_call_blocked["agent_summary"]["option_structure"]["status"] == "REJECT"

    # A covered call is written by SELLING to open -- the coordinator must not
    # apply the equity-only "BUY side only" restriction to option orders.
    covered_call_sell = evaluate_candidate(
        symbol="AAPL",
        side="SELL",
        quantity=1,
        price=3.50,
        position_pct=1.0,
        total_exposure_pct=1.0,
        loss_per_trade_pct=0.1,
        daily_loss_pct=0.1,
        orders_today=0,
        shariah_override=SHARIAH_PASS,
        quant_override=QUANT_BUY,
        asset_class="option",
        option_structure={"structure": "covered_call", "shares_held": 100, "contracts": 1},
    )
    assert "only_buy_side_supported" not in covered_call_sell["blockers"]
    assert covered_call_sell["decision"] == "READY_FOR_APPROVAL"

    # The restriction still applies to plain equity SELL orders -- this
    # coordinator isn't the reduce-only SELL gate (that's the portfolio risk
    # overlay in local_api.py); it just shouldn't block options on side alone.
    equity_sell_still_blocked = evaluate_candidate(
        symbol="AAPL",
        side="SELL",
        quantity=1,
        price=100.0,
        position_pct=1.0,
        total_exposure_pct=1.0,
        loss_per_trade_pct=0.1,
        daily_loss_pct=0.1,
        orders_today=0,
        shariah_override=SHARIAH_PASS,
        quant_override=QUANT_BUY,
    )
    assert "only_buy_side_supported" in equity_sell_still_blocked["blockers"]

    print("PASS: agent_coordinator composes the option-structure gate additively.")


if __name__ == "__main__":
    main()

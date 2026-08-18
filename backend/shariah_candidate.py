"""The one integration point between broker-specific order construction and
the Shariah/risk/approval gate chain.

Any broker adapter (Alpaca, Moomoo, or a future one) calls
build_shariah_candidate with plain values it already has on hand -- it does
not need to know anything about shariah_gate.py, option_structure_gate.py,
or account_shariah_gate.py internally. This keeps gate logic and gate
ownership in one place (this file and its imports) while broker adapters
stay free of Shariah-specific code, matching the existing split where
moomoo_paper_adapter.py and alpaca_paper_adapter.py perform no compliance
checks of their own.
"""

from agents.shariah_agent import evaluate_shariah


# Maps Alpaca's option_contract.strategy vocabulary to option_structure_gate's
# structure names. Extend this, not the gate itself, when a new Alpaca
# strategy needs to be recognized -- an unmapped strategy intentionally falls
# through to option_structure_gate's own unknown_structure rejection.
ALPACA_STRATEGY_TO_STRUCTURE = {
    "COVERED_CALL": "covered_call",
    "CASH_SECURED_PUT": "cash_secured_put",
    "PROTECTIVE_PUT": "protective_put",
    "COLLAR": "collar",
}


def build_shariah_candidate(
    *,
    symbol: str,
    side: str,
    signal: str,
    quantity: int,
    price: float,
    account_type: str,
    option_contract: dict | None = None,
    shares_held: int = 0,
    cash_collateral: float = 0.0,
    uses_margin: bool = False,
    shariah_override: dict | None = None,
) -> dict:
    shariah = shariah_override if shariah_override is not None else evaluate_shariah(symbol)

    candidate = {
        "symbol": symbol,
        "side": side,
        "signal": signal,
        "quantity": quantity,
        "price": price,
        "compliance": {
            "status": "COMPLIANT" if shariah["status"] == "PASS" else "NON_COMPLIANT",
            "source": shariah.get("provider"),
            "reason": shariah.get("reason"),
        },
        "account_type": account_type,
    }

    if option_contract is not None:
        structure = ALPACA_STRATEGY_TO_STRUCTURE.get(str(option_contract.get("strategy") or "").upper())
        candidate["option_structure"] = {
            "structure": structure or "unknown_structure",
            "shares_held": shares_held,
            "cash_collateral": cash_collateral,
            "strike": option_contract.get("strike"),
            "contracts": quantity,
            "uses_margin": uses_margin,
        }

    return candidate

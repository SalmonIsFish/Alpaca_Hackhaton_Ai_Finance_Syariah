"""Human-readable, citation-backed audit trace for Shariah gate decisions.

Turns the PASS/REJECT + reason codes from shariah_agent and
option_structure_agent into a single log line suitable for the execution
audit trail. Rationale text is sourced from
E:\\Projects Stuff\\Multi_Ai_IslamicFinance\\01-Shariah-Principles and recorded
in hackathon/alpaca-2026/SHARIAH_GATE_NOTES.md — see that doc before changing
any wording here, since these strings are meant to be defensible in a demo,
not just descriptive.
"""

STRUCTURE_RATIONALE = {
    "covered_by_owned_shares": "asset-backed; ownership precedes the sale of a right",
    "cash_secured": "100% cash-collateralized purchase commitment (Arboun/Wa'd); no margin financing",
    "hedges_owned_shares": "defensive hedge on an owned position, not speculative",
    "collar_on_owned_shares": "combined put+call hedge on an owned position",
    "insufficient_underlying_shares": "not enough owned shares to cover the call",
    "insufficient_cash_collateral": "insufficient cash collateral for the put",
    "strike_required": "no strike supplied to size the required collateral",
    "no_underlying_position_to_protect": "no owned position to hedge; would be a naked leg",
    "structure_not_permitted": "naked/speculative structure (gharar/maysir)",
    "margin_financing_not_permitted": "margin-financed leg introduces riba",
    "unknown_structure": "unrecognized structure, fails closed by policy",
}

ACCOUNT_RATIONALE = {
    "cash_account_no_margin_exposure": "no standing riba exposure",
    "margin_account_not_permitted": "margin capability is a standing riba exposure",
    "unknown_account_type": "unrecognized account type, fails closed by policy",
}


def build_shariah_trace(
    *,
    symbol: str,
    shariah: dict,
    option_structure: dict | None = None,
    account_shariah: dict | None = None,
) -> str:
    parts = [f"{symbol}: underlying={shariah.get('status')} ({shariah.get('provider')})"]

    if option_structure is not None:
        structure_name = (option_structure.get("details") or {}).get("structure", "unknown")
        status = option_structure.get("status")
        reason = option_structure.get("reason")
        rationale = STRUCTURE_RATIONALE.get(reason)
        if rationale:
            parts.append(f"structure={structure_name} -> {status} ({rationale})")
        else:
            parts.append(f"structure={structure_name} -> {status} ({reason})")

    if account_shariah is not None:
        account_type = (account_shariah.get("details") or {}).get("account_type", "unknown")
        status = account_shariah.get("status")
        reason = account_shariah.get("reason")
        rationale = ACCOUNT_RATIONALE.get(reason)
        if rationale:
            parts.append(f"account={account_type} -> {status} ({rationale})")
        else:
            parts.append(f"account={account_type} -> {status} ({reason})")

    return ". ".join(parts) + "."


def describe_approval(*, symbol: str, shariah: dict, candidate: dict) -> str:
    """Build the full trace from the same candidate shape
    shariah_candidate.build_shariah_candidate() produces, so callers (e.g.
    local_api.py) never need to know option_structure_gate/account_shariah_gate
    internals -- just pass the candidate and the shariah result through.
    """
    from agents.account_shariah_agent import evaluate_account
    from agents.option_structure_agent import evaluate_option_structure

    option_structure_input = candidate.get("option_structure")
    option_structure_result = (
        evaluate_option_structure(**option_structure_input) if option_structure_input is not None else None
    )
    account_type = candidate.get("account_type")
    account_result = evaluate_account(account_type=account_type) if account_type is not None else None
    if account_result is not None:
        account_result = {**account_result, "details": {"account_type": account_type}}

    return build_shariah_trace(
        symbol=symbol,
        shariah=shariah,
        option_structure=option_structure_result,
        account_shariah=account_result,
    )

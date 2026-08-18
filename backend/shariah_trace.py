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


def build_shariah_trace(*, symbol: str, shariah: dict, option_structure: dict | None = None) -> str:
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

    return ". ".join(parts) + "."

"""Fail-closed Shariah gate for options-structure eligibility.

Deterministic, non-AI, and separate from the underlying-symbol gate in
shariah_gate.py. A trade needs a PASS from both gates before it can reach
the approval queue. See hackathon/alpaca-2026/SHARIAH_GATE_NOTES.md for the
sourced rationale behind each verdict.
"""

SHARES_PER_CONTRACT = 100

# Asset-backed or cash-backed structures the policy currently permits, subject
# to the ownership/collateral condition enforced below.
ALLOWED_STRUCTURES = {"covered_call", "cash_secured_put", "protective_put", "collar"}

# Naked/speculative structures rejected outright regardless of backing.
REJECTED_STRUCTURES = {"naked_call", "naked_put", "straddle", "strangle"}


def check_structure(
    *,
    structure: str,
    shares_held: int = 0,
    cash_collateral: float = 0.0,
    strike: float | None = None,
    contracts: int = 1,
    uses_margin: bool = False,
) -> dict:
    normalized = structure.strip().lower()

    if uses_margin:
        return {"status": "REJECT", "reason": "margin_financing_not_permitted", "structure": normalized}

    if normalized in REJECTED_STRUCTURES:
        return {"status": "REJECT", "reason": "structure_not_permitted", "structure": normalized}

    if normalized not in ALLOWED_STRUCTURES:
        return {"status": "REJECT", "reason": "unknown_structure", "structure": normalized}

    if normalized == "covered_call":
        if shares_held >= contracts * SHARES_PER_CONTRACT:
            return {"status": "PASS", "reason": "covered_by_owned_shares", "structure": normalized}
        return {"status": "REJECT", "reason": "insufficient_underlying_shares", "structure": normalized}

    if normalized == "cash_secured_put":
        if strike is None or strike <= 0:
            return {"status": "REJECT", "reason": "strike_required", "structure": normalized}
        if cash_collateral >= contracts * SHARES_PER_CONTRACT * strike:
            return {"status": "PASS", "reason": "cash_secured", "structure": normalized}
        return {"status": "REJECT", "reason": "insufficient_cash_collateral", "structure": normalized}

    # protective_put and collar share the same ownership requirement: both
    # hedge an already-owned position rather than opening a naked leg.
    if shares_held >= contracts * SHARES_PER_CONTRACT:
        reason = "hedges_owned_shares" if normalized == "protective_put" else "collar_on_owned_shares"
        return {"status": "PASS", "reason": reason, "structure": normalized}
    return {"status": "REJECT", "reason": "no_underlying_position_to_protect", "structure": normalized}

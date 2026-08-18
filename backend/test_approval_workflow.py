"""Verify approval states without contacting Moomoo."""

from approval_workflow import approve_candidate


candidate = {
    "signal": "BUY",
    "compliance": {"status": "COMPLIANT", "source": "LOCAL_TEST_FIXTURE"},
    "symbol": "TEST_ONLY",
    "quantity": 1,
    "price": 100.0,
}

print("Pending:", approve_candidate(candidate, approved_by_user=False))
print("Approved:", approve_candidate(candidate, approved_by_user=True))

# A candidate with a compliant option structure approves normally.
covered_call_candidate = {
    **candidate,
    "option_structure": {"structure": "covered_call", "shares_held": 100, "contracts": 1},
}
covered_call_result = approve_candidate(covered_call_candidate, approved_by_user=True)
assert covered_call_result["status"] == "APPROVED_PAPER_READY"

# A candidate with a non-compliant option structure is rejected even though
# the underlying symbol is compliant and the user approved it.
naked_call_candidate = {
    **candidate,
    "option_structure": {"structure": "naked_call"},
}
naked_call_result = approve_candidate(naked_call_candidate, approved_by_user=True)
assert naked_call_result["status"] == "REJECT"
assert naked_call_result["reason"] == "option_structure_rejected"
assert naked_call_result["option_structure"]["status"] == "REJECT"

# No option_structure key at all is the existing equity-only behavior.
assert "option_structure" not in candidate

# A margin-enabled account is rejected even for a plain compliant equity buy --
# this is the gap flagged in the Alpaca adapter: account_type was computed but
# never actually gated on. Closing it here, not in the adapter, keeps every
# broker adapter subject to the same Shariah account check.
margin_account_candidate = {**candidate, "account_type": "MARGIN"}
margin_account_result = approve_candidate(margin_account_candidate, approved_by_user=True)
assert margin_account_result["status"] == "REJECT"
assert margin_account_result["reason"] == "margin_account_not_permitted"

cash_account_candidate = {**candidate, "account_type": "CASH"}
cash_account_result = approve_candidate(cash_account_candidate, approved_by_user=True)
assert cash_account_result["status"] == "APPROVED_PAPER_READY"

# No account_type key at all is the existing behavior (unaffected).
assert "account_type" not in candidate

print("PASS: approval workflow enforces the option-structure gate additively.")
print("PASS: approval workflow rejects margin-enabled accounts.")
print("TEST ONLY: no Moomoo connection and no order submission.")

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
print("TEST ONLY: no Moomoo connection and no order submission.")

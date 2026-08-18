"""Deterministic account-level Shariah agent for margin/Riba exposure.

This agent is deterministic and fail-closed. It does not use an LLM.
"""

from account_shariah_gate import check_account


def evaluate_account(*, account_type: str) -> dict:
    result = check_account(account_type=account_type)
    return {
        "agent": "account_shariah",
        "status": result.get("status"),
        "reason": result.get("reason"),
        "details": result,
    }

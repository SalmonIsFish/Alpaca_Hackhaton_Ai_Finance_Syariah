"""Local Shariah agent.

This agent is deterministic and fail-closed. It does not use an LLM.
"""

from shariah_gate import check_symbol


def evaluate_shariah(symbol: str) -> dict:
    result = check_symbol(symbol)
    status = "PASS" if result.get("status") == "PASS" else "REJECT"
    return {
        "agent": "shariah",
        "status": status,
        "symbol": symbol,
        "reason": result.get("reason"),
        "details": result,
    }

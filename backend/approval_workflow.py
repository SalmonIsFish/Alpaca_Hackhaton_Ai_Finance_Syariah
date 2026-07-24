"""Approval-required paper workflow; broker submission remains opt-in."""

from config import load_settings


def approve_candidate(candidate: dict, *, approved_by_user: bool) -> dict:
    settings = load_settings()
    if settings.moomoo_mode != "paper":
        return {"status": "REJECT", "reason": "paper_mode_required"}
    side = str(candidate.get("side") or "BUY").upper()
    if side not in {"BUY", "SELL"}:
        return {"status": "REJECT", "reason": "side_must_be_BUY_or_SELL"}
    if side == "BUY" and candidate.get("signal") != "BUY":
        return {"status": "REJECT", "reason": "no_buy_signal"}
    if side == "SELL" and candidate.get("signal") != "SELL":
        return {"status": "REJECT", "reason": "sell_signal_required"}
    if candidate.get("compliance", {}).get("status") != "COMPLIANT":
        return {"status": "REJECT", "reason": "compliance_not_confirmed"}
    if not approved_by_user:
        return {"status": "PENDING_APPROVAL", "broker_submission": False}
    return {"status": "APPROVED_PAPER_READY", "broker_submission": False, "execution_environment": "SIMULATE", "candidate": candidate}

"""Approval-required paper workflow; broker submission remains opt-in."""

from config import load_settings


def approve_candidate(candidate: dict, *, approved_by_user: bool) -> dict:
    settings = load_settings()
    if settings.moomoo_mode != "paper":
        return {"status": "REJECT", "reason": "paper_mode_required"}
    if candidate.get("signal") != "BUY":
        return {"status": "REJECT", "reason": "no_buy_signal"}
    if candidate.get("compliance", {}).get("status") != "COMPLIANT":
        return {"status": "REJECT", "reason": "compliance_not_confirmed"}
    if not approved_by_user:
        return {"status": "PENDING_APPROVAL", "broker_submission": False}
    return {"status": "APPROVED_PAPER_READY", "broker_submission": False, "execution_environment": "SIMULATE", "candidate": candidate}

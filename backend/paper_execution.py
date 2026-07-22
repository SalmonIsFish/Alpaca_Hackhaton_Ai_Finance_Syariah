"""Locked-safe paper execution workflow.

This module validates the queue row and execution gates before delegating to a
configured adapter. Broker submission remains opt-in through configuration.
"""

import sqlite3

from approval_queue import get_approval, record_broker_submission, update_execution_status
from config import load_settings
from moomoo_status import check_moomoo_status
from moomoo_paper_adapter import submit_paper_order
from trading_modes import mode_capabilities


def execute_paper_order(connection: sqlite3.Connection, queue_id: int) -> dict:
    settings = load_settings()
    approval = get_approval(connection, queue_id)
    if approval is None:
        return {"status": "NOT_FOUND", "queue_id": queue_id, "broker_submission": False}

    if approval.get("approval_status") != "APPROVED_PAPER_READY":
        result = update_execution_status(
            connection,
            queue_id,
            status="NOT_APPROVED",
            message="approval_status_must_be_APPROVED_PAPER_READY",
        )
        return {**result, "status": result["execution_status"], "queue_id": queue_id, "broker_submission": False}

    if approval.get("broker_submission"):
        result = update_execution_status(
            connection,
            queue_id,
            status="ALREADY_SUBMITTED",
            message="broker_submission_already_recorded",
        )
        return {**result, "status": result["execution_status"], "queue_id": queue_id, "broker_submission": True}

    capabilities = mode_capabilities(settings.trading_mode)
    if not capabilities["paper_execution_allowed"]:
        result = update_execution_status(
            connection,
            queue_id,
            status="TRADING_MODE_BLOCKED",
            message=f"TRADING_MODE {settings.trading_mode} does not allow paper execution",
        )
        return {
            **result,
            "status": result["execution_status"],
            "queue_id": queue_id,
            "trading_mode": settings.trading_mode,
            "broker_submission": False,
        }

    if not settings.paper_execution_enabled:
        result = update_execution_status(
            connection,
            queue_id,
            status="EXECUTION_LOCKED",
            message="PAPER_EXECUTION_ENABLED is false",
        )
        return {
            **result,
            "status": result["execution_status"],
            "queue_id": queue_id,
            "paper_execution_enabled": False,
            "broker_submission": False,
        }

    if approval.get("shariah_status") != "PASS":
        result = update_execution_status(
            connection,
            queue_id,
            status="SHARIAH_GATE_FAILED",
            message="shariah_status_must_be_PASS",
        )
        return {**result, "status": result["execution_status"], "queue_id": queue_id, "broker_submission": False}

    if approval.get("risk_status") != "PASS":
        result = update_execution_status(
            connection,
            queue_id,
            status="RISK_GATE_FAILED",
            message="risk_status_must_be_PASS",
        )
        return {**result, "status": result["execution_status"], "queue_id": queue_id, "broker_submission": False}

    moomoo = check_moomoo_status()
    if (
        not moomoo.get("paper_account_ready")
        or moomoo.get("environment") != "SIMULATE"
        or moomoo.get("account_status") != "ACTIVE"
    ):
        result = update_execution_status(
            connection,
            queue_id,
            status="MOOMOO_NOT_READY",
            message=moomoo.get("reason") or moomoo.get("status", "moomoo_not_ready"),
        )
        return {**result, "status": result["execution_status"], "queue_id": queue_id, "moomoo": moomoo, "broker_submission": False}

    broker_response = submit_paper_order(approval, moomoo)
    if not broker_response.get("broker_submission"):
        result = update_execution_status(
            connection,
            queue_id,
            status=broker_response.get("status", "ADAPTER_NOT_CONFIGURED"),
            message=broker_response.get("reason", "paper execution adapter did not submit"),
        )
        return {
            **result,
            "status": result["execution_status"],
            "queue_id": queue_id,
            "paper_execution_enabled": True,
            "broker_submission": False,
            "moomoo": moomoo,
            "adapter": broker_response,
        }

    result = record_broker_submission(connection, queue_id, broker_response=broker_response)
    return {
        **result,
        "status": result["execution_status"],
        "queue_id": queue_id,
        "paper_execution_enabled": True,
        "broker_submission": True,
        "moomoo": moomoo,
    }

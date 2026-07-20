"""Locked-safe paper execution workflow.

This module intentionally does not submit Moomoo orders yet. It validates the
queue row and execution lock, then records why execution did or did not proceed.
"""

import sqlite3

from approval_queue import get_approval, update_execution_status
from config import load_settings
from moomoo_status import check_moomoo_status


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
        return {**result, "status": result["execution_status"], "queue_id": queue_id, "broker_submission": False}

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

    moomoo = check_moomoo_status()
    if not moomoo.get("paper_account_ready"):
        result = update_execution_status(
            connection,
            queue_id,
            status="MOOMOO_NOT_READY",
            message=moomoo.get("reason") or moomoo.get("status", "moomoo_not_ready"),
        )
        return {**result, "status": result["execution_status"], "queue_id": queue_id, "moomoo": moomoo, "broker_submission": False}

    result = update_execution_status(
        connection,
        queue_id,
        status="EXECUTION_DRY_RUN_READY",
        message="execution adapter is not enabled to submit orders yet",
    )
    return {
        **result,
        "status": result["execution_status"],
        "queue_id": queue_id,
        "paper_execution_enabled": True,
        "broker_submission": False,
        "moomoo": moomoo,
    }

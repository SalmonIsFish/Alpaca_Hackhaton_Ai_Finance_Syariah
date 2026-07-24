"""Locked-safe paper execution workflow.

This module validates the queue row and execution gates before delegating to a
configured adapter. Broker submission remains opt-in through configuration.
"""

import sqlite3

from approval_queue import get_approval, record_broker_reconciliation, record_broker_submission, update_execution_status
from config import load_settings
from moomoo_status import check_moomoo_status
from moomoo_paper_adapter import reconcile_paper_order, submit_paper_order
from portfolio_store import open_position_quantity
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
        return {
            "id": queue_id,
            "status": "ALREADY_SUBMITTED",
            "queue_id": queue_id,
            "broker_submission": True,
            "execution_status": approval.get("execution_status"),
            "execution_message": approval.get("execution_message") or "broker_submission_already_recorded",
            "executed_at": approval.get("executed_at"),
        }

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

    sell_gate = validate_sell_reduction(connection, approval, moomoo)
    if sell_gate["status"] != "PASS":
        result = update_execution_status(
            connection,
            queue_id,
            status="PORTFOLIO_SELL_GATE_FAILED",
            message=sell_gate["reason"],
        )
        return {
            **result,
            "status": result["execution_status"],
            "queue_id": queue_id,
            "broker_submission": False,
            "moomoo": moomoo,
            "portfolio_gate": sell_gate,
        }

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


def validate_sell_reduction(connection: sqlite3.Connection, approval: dict, moomoo: dict) -> dict:
    side = str(approval.get("side") or "BUY").upper()
    if side != "SELL":
        return {"status": "PASS", "side": side}

    symbol = str(approval.get("symbol") or "").upper()
    quantity = float(approval.get("quantity") or 0)
    account_suffix = moomoo.get("account_suffix")
    available_quantity = open_position_quantity(connection, symbol=symbol, account_suffix=account_suffix)
    if quantity <= 0:
        return {
            "status": "REJECT",
            "reason": "sell_quantity_must_be_positive",
            "symbol": symbol,
            "requested_quantity": quantity,
            "available_quantity": available_quantity,
            "account_suffix": account_suffix,
        }
    if available_quantity <= 0:
        return {
            "status": "REJECT",
            "reason": f"no local {symbol} position is available for account {account_suffix}",
            "symbol": symbol,
            "requested_quantity": quantity,
            "available_quantity": available_quantity,
            "account_suffix": account_suffix,
        }
    if quantity > available_quantity:
        return {
            "status": "REJECT",
            "reason": f"sell quantity {quantity:g} exceeds local {symbol} position {available_quantity:g} for account {account_suffix}",
            "symbol": symbol,
            "requested_quantity": quantity,
            "available_quantity": available_quantity,
            "account_suffix": account_suffix,
        }
    return {
        "status": "PASS",
        "side": side,
        "symbol": symbol,
        "requested_quantity": quantity,
        "available_quantity": available_quantity,
        "account_suffix": account_suffix,
    }


def reconcile_submitted_paper_order(connection: sqlite3.Connection, queue_id: int) -> dict:
    approval = get_approval(connection, queue_id)
    if approval is None:
        return {"status": "NOT_FOUND", "queue_id": queue_id, "broker_submission": False}

    if not approval.get("broker_submission"):
        return {
            "status": "BROKER_NOT_SUBMITTED",
            "queue_id": queue_id,
            "broker_submission": False,
            "reason": "approval row has no broker submission",
        }

    reconciliation = reconcile_paper_order(approval)
    if not reconciliation.get("broker_submission"):
        return {
            "status": reconciliation.get("status", "BROKER_RECONCILE_ERROR"),
            "queue_id": queue_id,
            "broker_submission": False,
            "adapter": reconciliation,
        }

    result = record_broker_reconciliation(connection, queue_id, reconciliation=reconciliation)
    return {
        **result,
        "status": result["execution_status"],
        "queue_id": queue_id,
        "broker_submission": True,
    }

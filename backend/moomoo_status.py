"""Read-only Moomoo OpenD status checks."""

import socket

from config import load_settings


def _port_reachable(host: str, port: int, *, timeout: float = 1.5) -> bool:
    """Cheap pre-check so a closed OpenD port fails in ~1.5s instead of the
    minutes-long retry/backoff the moomoo SDK runs internally when a real
    connection attempt is refused."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_moomoo_status() -> dict:
    settings = load_settings()
    if not _port_reachable(settings.moomoo_host, settings.moomoo_port):
        return {
            "status": "unreachable",
            "host": settings.moomoo_host,
            "port": settings.moomoo_port,
            "mode": settings.moomoo_mode,
            "paper_account_ready": False,
            "paper_execution_enabled": settings.paper_execution_enabled,
            "broker_submission": False,
            "reason": "moomoo_opend_not_listening",
        }
    try:
        from moomoo import OpenSecTradeContext, TrdMarket
    except ModuleNotFoundError:
        return {
            "status": "not_installed",
            "host": settings.moomoo_host,
            "port": settings.moomoo_port,
            "mode": settings.moomoo_mode,
            "paper_account_ready": False,
            "paper_execution_enabled": settings.paper_execution_enabled,
            "broker_submission": False,
            "reason": "moomoo_sdk_missing",
        }
    except Exception as exc:
        return {
            "status": "sdk_unavailable",
            "host": settings.moomoo_host,
            "port": settings.moomoo_port,
            "mode": settings.moomoo_mode,
            "paper_account_ready": False,
            "paper_execution_enabled": settings.paper_execution_enabled,
            "broker_submission": False,
            "reason": type(exc).__name__,
        }

    context = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=settings.moomoo_host, port=settings.moomoo_port)
    try:
        ret, accounts = context.get_acc_list()
        if ret != 0:
            return {
                "status": "unreachable",
                "host": settings.moomoo_host,
                "port": settings.moomoo_port,
                "mode": settings.moomoo_mode,
                "paper_account_ready": False,
                "paper_execution_enabled": settings.paper_execution_enabled,
                "broker_submission": False,
                "reason": f"get_acc_list_failed:{ret}",
            }

        paper = accounts[
            (accounts["trd_env"] == "SIMULATE")
            & (accounts["acc_status"] == "ACTIVE")
        ]
        if paper.empty:
            return {
                "status": "paper_account_missing",
                "host": settings.moomoo_host,
                "port": settings.moomoo_port,
                "mode": settings.moomoo_mode,
                "paper_account_ready": False,
                "paper_execution_enabled": settings.paper_execution_enabled,
                "broker_submission": False,
                "reason": "active_us_simulate_account_not_found",
            }

        account_id = str(paper.iloc[0]["acc_id"])
        return {
            "status": "paper_account_ready",
            "host": settings.moomoo_host,
            "port": settings.moomoo_port,
            "mode": settings.moomoo_mode,
            "paper_account_ready": True,
            "paper_execution_enabled": settings.paper_execution_enabled,
            "broker_submission": False,
            "environment": str(paper.iloc[0]["trd_env"]),
            "account_type": str(paper.iloc[0]["acc_type"]),
            "account_status": str(paper.iloc[0]["acc_status"]),
            "account_suffix": account_id[-4:],
        }
    except Exception as exc:
        return {
            "status": "unreachable",
            "host": settings.moomoo_host,
            "port": settings.moomoo_port,
            "mode": settings.moomoo_mode,
            "paper_account_ready": False,
            "paper_execution_enabled": settings.paper_execution_enabled,
            "broker_submission": False,
            "reason": type(exc).__name__,
        }
    finally:
        context.close()

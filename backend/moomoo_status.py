"""Read-only Moomoo OpenD status checks."""

from config import load_settings


def check_moomoo_status() -> dict:
    settings = load_settings()
    try:
        from moomoo import OpenSecTradeContext
    except ModuleNotFoundError:
        return {
            "status": "not_installed",
            "host": settings.moomoo_host,
            "port": settings.moomoo_port,
            "mode": settings.moomoo_mode,
            "paper_account_ready": False,
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
            "broker_submission": False,
            "reason": type(exc).__name__,
        }

    context = OpenSecTradeContext(host=settings.moomoo_host, port=settings.moomoo_port)
    try:
        ret, accounts = context.get_acc_list()
        if ret != 0:
            return {
                "status": "unreachable",
                "host": settings.moomoo_host,
                "port": settings.moomoo_port,
                "mode": settings.moomoo_mode,
                "paper_account_ready": False,
                "broker_submission": False,
                "reason": f"get_acc_list_failed:{ret}",
            }

        paper = accounts[
            (accounts["trd_env"] == "SIMULATE")
            & (accounts["acc_type"] == "CASH")
            & (accounts["acc_status"] == "ACTIVE")
        ]
        if paper.empty:
            return {
                "status": "paper_account_missing",
                "host": settings.moomoo_host,
                "port": settings.moomoo_port,
                "mode": settings.moomoo_mode,
                "paper_account_ready": False,
                "broker_submission": False,
                "reason": "active_simulate_cash_account_not_found",
            }

        account_id = str(paper.iloc[0]["acc_id"])
        return {
            "status": "paper_account_ready",
            "host": settings.moomoo_host,
            "port": settings.moomoo_port,
            "mode": settings.moomoo_mode,
            "paper_account_ready": True,
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
            "broker_submission": False,
            "reason": type(exc).__name__,
        }
    finally:
        context.close()

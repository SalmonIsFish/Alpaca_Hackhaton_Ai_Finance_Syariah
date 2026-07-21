"""Paper execution adapter boundary for Moomoo submissions."""

from datetime import datetime, timezone

from config import load_settings


SUPPORTED_REAL_MARKETS = {"US"}


def submit_paper_order(approval: dict, moomoo: dict) -> dict:
    settings = load_settings()
    adapter = settings.paper_execution_adapter
    if adapter == "fake":
        return fake_submit_paper_order(approval=approval, moomoo=moomoo)
    if adapter == "moomoo":
        return submit_moomoo_paper_order(approval=approval)
    return {
        "status": "ADAPTER_NOT_CONFIGURED",
        "adapter": adapter,
        "broker_submission": False,
        "reason": "PAPER_EXECUTION_ADAPTER must be fake or moomoo to submit paper orders",
    }


def load_moomoo_sdk():
    from moomoo import (
        RET_OK,
        OpenSecTradeContext,
        OrderType,
        Session,
        TimeInForce,
        TrdEnv,
        TrdMarket,
        TrdSide,
    )

    return {
        "RET_OK": RET_OK,
        "OpenSecTradeContext": OpenSecTradeContext,
        "OrderType": OrderType,
        "Session": Session,
        "TimeInForce": TimeInForce,
        "TrdEnv": TrdEnv,
        "TrdMarket": TrdMarket,
        "TrdSide": TrdSide,
    }


def submit_moomoo_paper_order(*, approval: dict) -> dict:
    settings = load_settings()
    market = (approval.get("shariah_market") or "").upper()
    if market not in SUPPORTED_REAL_MARKETS:
        return {
            "status": "UNSUPPORTED_MARKET",
            "adapter": "moomoo",
            "broker_submission": False,
            "reason": f"paper adapter currently supports {', '.join(sorted(SUPPORTED_REAL_MARKETS))} only",
        }

    code = normalize_order_code(approval)
    side = (approval.get("side") or "BUY").upper()
    quantity = approval.get("quantity")
    price = approval.get("price")
    if code is None:
        return {"status": "INVALID_SYMBOL", "adapter": "moomoo", "broker_submission": False, "reason": "symbol_required"}
    if side not in {"BUY", "SELL"}:
        return {"status": "INVALID_SIDE", "adapter": "moomoo", "broker_submission": False, "reason": "side_must_be_BUY_or_SELL"}
    if not isinstance(quantity, int) or quantity <= 0:
        return {"status": "INVALID_QUANTITY", "adapter": "moomoo", "broker_submission": False, "reason": "positive_integer_quantity_required"}
    if not isinstance(price, (int, float)) or price <= 0:
        return {"status": "INVALID_PRICE", "adapter": "moomoo", "broker_submission": False, "reason": "positive_price_required"}

    try:
        sdk = load_moomoo_sdk()
    except ModuleNotFoundError:
        return {"status": "SDK_NOT_INSTALLED", "adapter": "moomoo", "broker_submission": False, "reason": "moomoo_sdk_missing"}
    except Exception as exc:
        return {"status": "SDK_UNAVAILABLE", "adapter": "moomoo", "broker_submission": False, "reason": type(exc).__name__}

    trd_market = market_to_trd_market(sdk, market)
    context = sdk["OpenSecTradeContext"](filter_trdmarket=trd_market, host=settings.moomoo_host, port=settings.moomoo_port)
    try:
        ret, accounts = context.get_acc_list()
        if ret != sdk["RET_OK"]:
            return {
                "status": "MOOMOO_ACCOUNT_QUERY_FAILED",
                "adapter": "moomoo",
                "broker_submission": False,
                "reason": str(accounts),
            }
        account = find_active_simulate_cash_account(accounts)
        if account is None:
            return {
                "status": "MOOMOO_PAPER_ACCOUNT_MISSING",
                "adapter": "moomoo",
                "broker_submission": False,
                "reason": "active_simulate_cash_account_not_found",
            }

        account_id = int(account["acc_id"])
        ret, order_data = context.place_order(
            price=float(price),
            qty=float(quantity),
            code=code,
            trd_side=side_to_trd_side(sdk, side),
            order_type=sdk["OrderType"].NORMAL,
            trd_env=sdk["TrdEnv"].SIMULATE,
            acc_id=account_id,
            remark=f"Amanah queue {approval['id']}",
            time_in_force=sdk["TimeInForce"].DAY,
            fill_outside_rth=False,
            session=sdk["Session"].NONE,
        )
        if ret != sdk["RET_OK"]:
            return {
                "status": "BROKER_REJECTED",
                "adapter": "moomoo",
                "broker_submission": False,
                "reason": str(order_data),
                "environment": "SIMULATE",
                "account_type": "CASH",
                "account_suffix": str(account_id)[-4:],
            }

        submitted_at = datetime.now(timezone.utc).isoformat()
        order_id = extract_first_value(order_data, "order_id", "orderID")
        return {
            "status": "BROKER_SUBMITTED",
            "adapter": "moomoo",
            "broker_submission": True,
            "broker_order_id": order_id,
            "submitted_at": submitted_at,
            "symbol": approval.get("symbol"),
            "broker_code": code,
            "side": side,
            "quantity": quantity,
            "price": price,
            "environment": "SIMULATE",
            "account_type": "CASH",
            "account_suffix": str(account_id)[-4:],
            "order_status": extract_first_value(order_data, "order_status"),
        }
    except Exception as exc:
        return {"status": "BROKER_ERROR", "adapter": "moomoo", "broker_submission": False, "reason": type(exc).__name__}
    finally:
        context.close()


def fake_submit_paper_order(*, approval: dict, moomoo: dict) -> dict:
    submitted_at = datetime.now(timezone.utc).isoformat()
    return {
        "status": "BROKER_SUBMITTED",
        "adapter": "fake",
        "broker_submission": True,
        "broker_order_id": f"FAKE-PAPER-{approval['id']}",
        "submitted_at": submitted_at,
        "symbol": approval.get("symbol"),
        "side": approval.get("side"),
        "quantity": approval.get("quantity"),
        "price": approval.get("price"),
        "environment": moomoo.get("environment", "SIMULATE"),
        "account_type": moomoo.get("account_type", "CASH"),
        "account_suffix": moomoo.get("account_suffix"),
    }


def normalize_order_code(approval: dict) -> str | None:
    symbol = (approval.get("symbol") or "").strip().upper()
    if not symbol:
        return None
    if "." in symbol:
        return symbol
    market = (approval.get("shariah_market") or "").upper()
    if market == "US":
        return f"US.{symbol}"
    return None


def market_to_trd_market(sdk: dict, market: str):
    if market == "US":
        return sdk["TrdMarket"].US
    return sdk["TrdMarket"].NONE


def side_to_trd_side(sdk: dict, side: str):
    if side == "SELL":
        return sdk["TrdSide"].SELL
    return sdk["TrdSide"].BUY


def rows_from_table(table) -> list[dict]:
    if hasattr(table, "to_dict"):
        return table.to_dict("records")
    if isinstance(table, list):
        return table
    return []


def find_active_simulate_cash_account(accounts) -> dict | None:
    for row in rows_from_table(accounts):
        if row.get("trd_env") == "SIMULATE" and row.get("acc_type") == "CASH" and row.get("acc_status") == "ACTIVE":
            return row
    return None


def extract_first_value(data, *columns: str) -> str | None:
    rows = rows_from_table(data)
    if rows:
        for column in columns:
            value = rows[0].get(column)
            if value not in {None, ""}:
                return str(value)
    if isinstance(data, dict):
        for column in columns:
            value = data.get(column)
            if value not in {None, ""}:
                return str(value)
    return None

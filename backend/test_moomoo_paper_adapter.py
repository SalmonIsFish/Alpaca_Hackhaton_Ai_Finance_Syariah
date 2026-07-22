"""Verify the real Moomoo adapter path without connecting to OpenD."""

import os

import moomoo_paper_adapter


class FakeConstants:
    BUY = "BUY"
    SELL = "SELL"
    NORMAL = "NORMAL"
    NONE = "NONE"
    DAY = "DAY"
    SIMULATE = "SIMULATE"
    US = "US"
    NONE_MARKET = "NONE"


class FakeTradeContext:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
        self.place_order_calls = []
        FakeTradeContext.instances.append(self)

    def get_acc_list(self):
        return 0, [
            {"acc_id": 101, "trd_env": "REAL", "acc_type": "CASH", "acc_status": "ACTIVE"},
            {"acc_id": 987654321, "trd_env": "SIMULATE", "acc_type": "MARGIN", "acc_status": "ACTIVE"},
        ]

    def place_order(self, **kwargs):
        self.place_order_calls.append(kwargs)
        return 0, [{"order_id": "MOOMOO-ORDER-1", "order_status": "SUBMITTING"}]

    def close(self):
        self.closed = True


def fake_sdk():
    return {
        "RET_OK": 0,
        "OpenSecTradeContext": FakeTradeContext,
        "OrderType": FakeConstants,
        "Session": FakeConstants,
        "TimeInForce": FakeConstants,
        "TrdEnv": FakeConstants,
        "TrdMarket": FakeConstants,
        "TrdSide": FakeConstants,
    }


def main() -> None:
    original_env = os.environ.get("PAPER_EXECUTION_ADAPTER")
    original_loader = moomoo_paper_adapter.load_moomoo_sdk
    os.environ["PAPER_EXECUTION_ADAPTER"] = "moomoo"
    moomoo_paper_adapter.load_moomoo_sdk = fake_sdk
    FakeTradeContext.instances.clear()
    try:
        approval = {
            "id": 42,
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 3,
            "price": 195.5,
            "shariah_market": "US",
        }
        result = moomoo_paper_adapter.submit_paper_order(approval, moomoo={})
        assert result["status"] == "BROKER_SUBMITTED"
        assert result["broker_submission"] is True
        assert result["adapter"] == "moomoo"
        assert result["broker_order_id"] == "MOOMOO-ORDER-1"
        assert result["broker_code"] == "US.AAPL"
        assert result["account_suffix"] == "4321"

        account_context = FakeTradeContext.instances[0]
        assert account_context.kwargs["filter_trdmarket"] == "US"
        assert account_context.closed is True

        order_context = FakeTradeContext.instances[1]
        assert order_context.kwargs["filter_trdmarket"] == "US"
        assert order_context.closed is True
        call = order_context.place_order_calls[0]
        assert call["code"] == "US.AAPL"
        assert call["trd_side"] == "BUY"
        assert call["order_type"] == "NORMAL"
        assert call["trd_env"] == "SIMULATE"
        assert call["acc_id"] == 987654321
        assert call["remark"] == "Amanah queue 42"
        assert call["time_in_force"] == "DAY"
        assert call["fill_outside_rth"] is False
        assert call["session"] == "NONE"

        unsupported = moomoo_paper_adapter.submit_paper_order(
            {
                "id": 43,
                "symbol": "0001",
                "side": "BUY",
                "quantity": 1,
                "price": 1.0,
                "shariah_market": "MY",
            },
            moomoo={},
        )
        assert unsupported["status"] == "UNSUPPORTED_MARKET"
        assert unsupported["broker_submission"] is False
    finally:
        moomoo_paper_adapter.load_moomoo_sdk = original_loader
        if original_env is None:
            os.environ.pop("PAPER_EXECUTION_ADAPTER", None)
        else:
            os.environ["PAPER_EXECUTION_ADAPTER"] = original_env

    print("PASS: Moomoo paper adapter maps safe orders to OpenD place_order.")


if __name__ == "__main__":
    main()

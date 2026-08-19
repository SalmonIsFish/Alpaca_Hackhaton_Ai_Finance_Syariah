"""Verify Alpaca News API fetching without contacting Alpaca."""

import os

import alpaca_market_data


NEWS_PAGE = {
    "news": [
        {
            "id": 12345,
            "headline": "Apple unveils new product line",
            "summary": "Apple Inc. announced...",
            "author": "Jane Reporter",
            "source": "benzinga",
            "url": "https://example.com/apple-news",
            "created_at": "2026-08-19T14:00:00Z",
            "updated_at": "2026-08-19T14:05:00Z",
            "symbols": ["AAPL"],
            "images": [{"size": "large", "url": "https://example.com/img.jpg"}],
        }
    ],
    "next_page_token": "PAGE2TOKEN",
}


class FakeData:
    """Replays a canned Alpaca news response and records every request."""

    def __init__(self, response=None, *, fail=False, status_code=500):
        self.calls = []
        self.response = response
        self.fail = fail
        self.status_code = status_code

    def __call__(self, path, params, *, credentials, base_url=None):
        self.calls.append({"path": path, "params": dict(params), "credentials": credentials})
        if self.fail:
            return {"ok": False, "status_code": self.status_code, "data": {"message": "boom"}, "reason": f"http_{self.status_code}"}
        return {"ok": True, "status_code": 200, "data": self.response}


def check_request_built_and_response_passthrough() -> None:
    data = FakeData(NEWS_PAGE)
    alpaca_market_data.alpaca_data_request = data

    result = alpaca_market_data.fetch_news(["aapl", "msft", ""], limit=5)

    assert len(data.calls) == 1, "must be a single request, not the exhaustive pager"
    call = data.calls[0]
    assert call["path"] == "/v1beta1/news"
    assert call["params"]["symbols"] == "AAPL,MSFT", "symbols normalized to uppercase, blanks dropped"
    assert call["params"]["limit"] == 5
    assert call["params"]["sort"] == "desc"
    assert call["credentials"]["key_id"] == "TEST-KEY-ID"

    assert result["next_page_token"] == "PAGE2TOKEN"
    assert len(result["news"]) == 1
    article = result["news"][0]
    assert article["headline"] == "Apple unveils new product line"
    assert article["source"] == "benzinga"
    assert article["symbols"] == ["AAPL"]
    # Passed through as Alpaca returns it, not reshaped.
    assert article["url"] == "https://example.com/apple-news"


def check_limit_is_clamped() -> None:
    data = FakeData(NEWS_PAGE)
    alpaca_market_data.alpaca_data_request = data

    alpaca_market_data.fetch_news(["AAPL"], limit=500)
    assert data.calls[0]["params"]["limit"] == 50, "limit must be capped at Alpaca's max of 50"

    alpaca_market_data.fetch_news(["AAPL"], limit=0)
    assert data.calls[1]["params"]["limit"] == 1, "limit must be floored at 1"


def check_no_symbols_omits_the_param() -> None:
    data = FakeData(NEWS_PAGE)
    alpaca_market_data.alpaca_data_request = data

    alpaca_market_data.fetch_news([], limit=10)
    assert data.calls[0]["params"]["symbols"] is None


def check_missing_credentials_raises() -> None:
    os.environ.pop("ALPACA_API_KEY_ID", None)
    os.environ.pop("ALPACA_SECRET_KEY", None)
    raised = False
    try:
        alpaca_market_data.fetch_news(["AAPL"])
    except alpaca_market_data.AlpacaDataError as exc:
        raised = True
        assert exc.error_code == "missing_credentials", exc.error_code
    assert raised, "fetch_news must fail closed without credentials, not silently return empty"


def check_request_failure_raises() -> None:
    alpaca_market_data.alpaca_data_request = FakeData(fail=True, status_code=503)
    raised = False
    try:
        alpaca_market_data.fetch_news(["AAPL"])
    except alpaca_market_data.AlpacaDataError as exc:
        raised = True
        assert exc.status_code == 503, exc.status_code
    assert raised


def main() -> None:
    saved = {k: os.environ.get(k) for k in ["ALPACA_API_KEY_ID", "ALPACA_SECRET_KEY"]}
    original_request = alpaca_market_data.alpaca_data_request
    os.environ["ALPACA_API_KEY_ID"] = "TEST-KEY-ID"
    os.environ["ALPACA_SECRET_KEY"] = "TEST-SECRET"
    try:
        check_request_built_and_response_passthrough()
        check_limit_is_clamped()
        check_no_symbols_omits_the_param()
        check_request_failure_raises()
        check_missing_credentials_raises()
    finally:
        alpaca_market_data.alpaca_data_request = original_request
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    print("PASS: fetch_news builds the right Alpaca request and fails closed without credentials.")


if __name__ == "__main__":
    main()

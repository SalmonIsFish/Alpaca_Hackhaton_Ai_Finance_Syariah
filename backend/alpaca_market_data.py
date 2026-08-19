"""Read-only Alpaca market-data adapter for bars and Level 1 option chains.

Mirrors ``tiingo_prices.fetch_eod_prices`` exactly — same signature, same bar shape,
same ``(bars, source)`` return — so ``market_data.summarize_history`` can switch
providers without any consumer noticing.

Two Alpaca hosts are involved and neither can trade:

- ``data.alpaca.markets``   bars and option snapshots (market data, read-only by nature)
- ``paper-api.alpaca.markets``  the option *contract* catalogue, which lives on the
  trading host. Only GET endpoints are used here, and the host is the paper one.
"""

from __future__ import annotations

import json
import time
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from alpaca_paper_adapter import ALPACA_PAPER_BASE_URL, alpaca_credentials
from config import load_settings

# The on-disk cache is provider-agnostic (backend/market_data_cache) and its freshness
# metadata already feeds /market-overview, so both providers share it rather than
# duplicating the logic or splitting the staleness reporting.
from tiingo_prices import _fixture_prices as fixture_prices
from tiingo_prices import _read_cache as read_market_cache
from tiingo_prices import _write_cache as write_market_cache


ALPACA_DATA_BASE_URL = "https://data.alpaca.markets"
ALPACA_TRADING_BASE_URL = ALPACA_PAPER_BASE_URL
REQUEST_TIMEOUT_SECONDS = 20
MAX_PAGES = 20
NETWORK_RETRIES = 1
RETRY_PAUSE_SECONDS = 0.5
OPTION_TYPES = {"CALL": "call", "PUT": "put"}


class AlpacaDataError(RuntimeError):
    """Market-data request failure with the same safe fields as TiingoDataError."""

    def __init__(self, error_code: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


def alpaca_data_request(path: str, params: dict, *, credentials: dict, base_url: str | None = None) -> dict:
    """Single seam for every Alpaca data call, so tests never touch the network."""
    root = base_url or ALPACA_DATA_BASE_URL
    query = urlencode({key: value for key, value in params.items() if value not in {None, ""}})
    url = f"{root}{path}?{query}" if query else f"{root}{path}"
    headers = {
        "APCA-API-KEY-ID": credentials["key_id"],
        "APCA-API-SECRET-KEY": credentials["secret_key"],
        "Accept": "application/json",
    }
    try:
        with urlopen(Request(url, headers=headers, method="GET"), timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return {"ok": True, "status_code": response.status, "data": _decode(response.read())}
    except HTTPError as exc:
        return {"ok": False, "status_code": exc.code, "data": _decode(exc.read()), "reason": f"http_{exc.code}"}
    except URLError as exc:
        return {"ok": False, "status_code": 0, "data": {}, "reason": type(exc).__name__}
    except Exception as exc:
        return {"ok": False, "status_code": 0, "data": {}, "reason": type(exc).__name__}


def _decode(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _request_with_retry(path: str, params: dict, *, credentials: dict, base_url: str | None = None) -> dict:
    """Retry once on a transport-level failure; HTTP errors are returned as-is."""
    response = alpaca_data_request(path, params, credentials=credentials, base_url=base_url)
    for _ in range(NETWORK_RETRIES):
        if response.get("ok") or response.get("status_code"):
            break
        time.sleep(RETRY_PAUSE_SECONDS)
        response = alpaca_data_request(path, params, credentials=credentials, base_url=base_url)
    return response


def _paged(path: str, params: dict, *, credentials: dict, key: str, base_url: str | None = None):
    """Walk Alpaca's next_page_token pagination, collecting `key` from each page."""
    collected = []
    token = None
    for _ in range(MAX_PAGES):
        page_params = dict(params)
        if token:
            page_params["page_token"] = token
        response = _request_with_retry(path, page_params, credentials=credentials, base_url=base_url)
        if not response.get("ok"):
            raise AlpacaDataError(
                response.get("reason") or "alpaca_request_failed",
                _message(response),
                status_code=response.get("status_code"),
            )
        payload = response.get("data") or {}
        chunk = payload.get(key)
        if isinstance(chunk, list):
            collected.extend(chunk)
        elif isinstance(chunk, dict):
            collected.append(chunk)
        token = payload.get("next_page_token")
        if not token:
            break
    return collected


def _message(response: dict) -> str:
    data = response.get("data")
    if isinstance(data, dict) and data.get("message"):
        return f"Alpaca data error: {data['message']}"
    return f"Alpaca data request failed ({response.get('reason')})"


# ---------------------------------------------------------------------------
# Daily bars — drop-in for tiingo_prices.fetch_eod_prices
# ---------------------------------------------------------------------------


def fetch_eod_prices(
    symbol: str,
    start_date: str,
    end_date: str,
    *,
    allow_fallback: bool = True,
    allow_stale_cache: bool = False,
) -> tuple[list[dict], str]:
    """Return normalized daily bars and their source (alpaca, cache, or fixture)."""
    normalized_symbol = symbol.strip().upper()
    credentials = alpaca_credentials()
    if credentials is None:
        if allow_stale_cache:
            cached = read_market_cache(normalized_symbol)
            if cached:
                return cached, "alpaca_cache_no_credentials"
        if allow_fallback:
            return fixture_prices(normalized_symbol), "fixture"
        raise AlpacaDataError("missing_credentials", "ALPACA_API_KEY_ID / ALPACA_SECRET_KEY are not configured")

    settings = load_settings()
    params = {
        "timeframe": "1Day",
        "start": start_date,
        "end": end_date,
        "limit": 10000,
        # Split/dividend adjusted, so SMA50/SMA200 comparisons stay meaningful.
        "adjustment": "all",
        "feed": settings.alpaca_data_feed or None,
    }
    source = "alpaca"
    try:
        rows = _paged(f"/v2/stocks/{normalized_symbol}/bars", params, credentials=credentials, key="bars")
    except AlpacaDataError as exc:
        if is_sip_subscription_error(exc) and not settings.alpaca_data_feed:
            # The Basic plan cannot query recent SIP data, so drop to the always-
            # permitted IEX feed rather than falling back to fixtures. IEX closes
            # come from one venue, hence the distinct source label.
            try:
                rows = _paged(
                    f"/v2/stocks/{normalized_symbol}/bars",
                    {**params, "feed": "iex"},
                    credentials=credentials,
                    key="bars",
                )
                source = "alpaca_iex"
            except AlpacaDataError:
                return _bars_fallback(normalized_symbol, allow_fallback, allow_stale_cache)
        else:
            return _bars_fallback(normalized_symbol, allow_fallback, allow_stale_cache)

    bars = normalize_bars(normalized_symbol, rows)
    write_market_cache(normalized_symbol, start_date, end_date, bars)
    return bars, source


def is_sip_subscription_error(exc: AlpacaDataError) -> bool:
    return exc.status_code == 403 and "subscription" in str(exc).lower()


def _bars_fallback(symbol: str, allow_fallback: bool, allow_stale_cache: bool):
    if allow_stale_cache:
        cached = read_market_cache(symbol)
        if cached:
            return cached, "alpaca_cache_after_error"
    if allow_fallback:
        return fixture_prices(symbol), "fixture_after_alpaca_error"
    raise


def normalize_bars(symbol: str, rows: list[dict]) -> list[dict]:
    """Map Alpaca's terse OHLCV keys onto the shape the quant agent already expects."""
    bars = []
    for row in rows:
        timestamp = str(row.get("t") or "")
        if not timestamp:
            continue
        bars.append(
            {
                "symbol": symbol,
                "date": timestamp[:10],
                "open": row.get("o"),
                "high": row.get("h"),
                "low": row.get("l"),
                "close": row.get("c"),
                "volume": row.get("v"),
            }
        )
    return bars


# ---------------------------------------------------------------------------
# Options — contract catalogue and merged chain
# ---------------------------------------------------------------------------


def fetch_option_contracts(
    underlying: str,
    *,
    expiration_gte: str | None = None,
    expiration_lte: str | None = None,
    option_type: str | None = None,
    limit: int = 100,
) -> tuple[list[dict], str]:
    """List tradable option contracts for an underlying (Level 1 strike selection)."""
    root = underlying.strip().upper()
    credentials = alpaca_credentials()
    if credentials is None:
        raise AlpacaDataError("missing_credentials", "ALPACA_API_KEY_ID / ALPACA_SECRET_KEY are not configured")

    params = {
        "underlying_symbols": root,
        "expiration_date_gte": expiration_gte,
        "expiration_date_lte": expiration_lte,
        "type": OPTION_TYPES.get(str(option_type or "").upper()),
        "limit": max(1, min(50, limit)),
    }
    rows = _paged(
        "/v2/options/contracts",
        params,
        credentials=credentials,
        key="option_contracts",
        base_url=ALPACA_TRADING_BASE_URL,
    )
    return [normalize_contract(row) for row in rows], "alpaca"


def normalize_contract(row: dict) -> dict:
    return {
        "symbol": row.get("symbol"),
        "underlying": row.get("underlying_symbol") or row.get("root_symbol"),
        "option_type": str(row.get("type") or "").upper(),
        "strike": _number(row.get("strike_price")),
        "expiration": row.get("expiration_date"),
        "style": row.get("style"),
        "status": row.get("status"),
        "tradable": bool(row.get("tradable")),
        "multiplier": int(_number(row.get("multiplier")) or 100),
        "name": row.get("name"),
    }


def fetch_option_snapshots(underlying: str, *, limit: int = 100) -> tuple[dict, str]:
    """Latest quote/trade/bar per contract, keyed by OCC symbol."""
    root = underlying.strip().upper()
    credentials = alpaca_credentials()
    if credentials is None:
        raise AlpacaDataError("missing_credentials", "ALPACA_API_KEY_ID / ALPACA_SECRET_KEY are not configured")

    pages = _paged(
        f"/v1beta1/options/snapshots/{root}",
        {"limit": limit},
        credentials=credentials,
        key="snapshots",
    )
    snapshots: dict = {}
    for page in pages:
        if isinstance(page, dict):
            snapshots.update(page)
    return snapshots, "alpaca"


def fetch_option_chain(
    underlying: str,
    *,
    expiration_gte: str | None = None,
    expiration_lte: str | None = None,
    option_type: str | None = None,
    limit: int = 100,
) -> tuple[list[dict], str]:
    """Contract catalogue joined to live quotes — what a covered call needs to pick a strike.

    Note: Alpaca's option snapshot response carries quotes, trades and bars but no
    Greeks on this account tier, so delta-based strike selection is not available
    from this call; bid/ask/mid are, which is what writing the contract requires.
    """
    contracts, _ = fetch_option_contracts(
        underlying,
        expiration_gte=expiration_gte,
        expiration_lte=expiration_lte,
        option_type=option_type,
        limit=limit,
    )
    snapshots, _ = fetch_option_snapshots(underlying, limit=limit)

    wanted = str(option_type or "").upper()
    rows = []
    for contract in contracts:
        if wanted and contract["option_type"] != wanted:
            continue
        rows.append({**contract, **quote_fields(snapshots.get(contract["symbol"]))})
    return rows, "alpaca"


def quote_fields(snapshot) -> dict:
    """Flatten one option snapshot into bid/ask/mid/last, tolerating a missing quote."""
    empty = {"bid": None, "ask": None, "mid": None, "last": None, "daily_close": None, "quoted_at": None}
    if not isinstance(snapshot, dict):
        return empty

    quote = snapshot.get("latestQuote") or {}
    trade = snapshot.get("latestTrade") or {}
    daily = snapshot.get("dailyBar") or {}
    bid = _number(quote.get("bp"))
    ask = _number(quote.get("ap"))
    mid = round((bid + ask) / 2, 4) if bid is not None and ask is not None else None
    return {
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "last": _number(trade.get("p")),
        "daily_close": _number(daily.get("c")),
        "quoted_at": quote.get("t"),
    }


def _number(value):
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# News — Alpaca's first-party News API (Benzinga-sourced)
# ---------------------------------------------------------------------------


def fetch_news(symbols: list[str], *, limit: int = 20) -> dict:
    """GET https://data.alpaca.markets/v1beta1/news via alpaca_data_request.

    Same credentials as market data (alpaca_credentials()); a single request,
    not the exhaustive-pagination helper other fetch_* functions here use --
    the caller wants at most `limit` recent articles, not every article Alpaca
    has ever indexed for these symbols. Returns the raw Alpaca response shape:
    {"news": [...], "next_page_token": ...}. Each article carries headline,
    summary, source, url, created_at, symbols, images, passed through as
    Alpaca returns them rather than reshaped, since those are already the
    fields a News tab needs.
    """
    credentials = alpaca_credentials()
    if credentials is None:
        raise AlpacaDataError("missing_credentials", "ALPACA_API_KEY_ID / ALPACA_SECRET_KEY are not configured")

    normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()]
    params = {
        "symbols": ",".join(normalized_symbols) if normalized_symbols else None,
        "limit": max(1, min(50, limit)),
        "sort": "desc",
    }
    response = _request_with_retry("/v1beta1/news", params, credentials=credentials)
    if not response.get("ok"):
        raise AlpacaDataError(
            response.get("reason") or "alpaca_request_failed",
            _message(response),
            status_code=response.get("status_code"),
        )
    payload = response.get("data") or {}
    return {
        "news": payload.get("news") or [],
        "next_page_token": payload.get("next_page_token"),
    }

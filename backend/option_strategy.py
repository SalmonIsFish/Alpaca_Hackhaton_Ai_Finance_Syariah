"""Level 1 option strike/expiry selection for covered calls and cash-secured puts.

This is the decision layer that was missing: ``alpaca_market_data.fetch_option_chain``
already returns contracts joined to live quotes, but nothing chose one. This module
chooses, and — as importantly for a demo — records *why* it chose, in the same spirit
as ``shariah_trace.build_shariah_trace``.

**Selecting is not approving.** The output here is a proposal. It goes into
``POST /paper/preview`` as ``option_contract`` and still has to clear the whole gate
chain (``shariah_gate`` -> ``option_structure_gate`` -> ``account_shariah_gate``) plus
the human confirmation phrase before it can reach the broker. Nothing in this file
gates anything; the coverage and collateral arithmetic here exists to size an order,
and ``option_structure_gate`` re-checks it authoritatively.

The rule, in one paragraph
--------------------------
Take every listed contract for the underlying expiring **1 to 7 days out**, keep only
the ones that are tradable, standard-multiplier, and actually quoted with a live bid
and a tight spread, and from those pick the strike whose out-of-the-money percentage
is closest to a **4% OTM target** inside a **2%-7% band**. Size it from what is
actually owned (shares / 100) or actually settled (cash / strike / 100), and if the
top-ranked strike cannot be sized, walk down the ranking to the first one that can.

Why each of those, since a demo has to defend them:

- **1-7 DTE.** A weekly contract expires inside the judging window, so the trade
  realises its P&L rather than sitting open as an unresolved position at judging time;
  a 30-45 DTE covered call would still be open. The floor is 1 rather than 0 because
  every order in this system waits on a human typing a confirmation phrase, and a
  0-DTE contract can expire while it sits in the approval queue. Pass ``min_dte=0``
  to allow same-day expiries anyway.
- **A %-OTM band, not "nearest the money".** Nearest-the-money maximises premium and
  assignment probability at the same time, which is the opposite of what a covered
  call is for. An OTM band caps assignment probability while keeping the premium
  meaningful, and it makes assignment itself benign: a covered call assigned at 4% OTM
  sells the shares *above* today's price, closing the position at a gain on the
  underlying. Delta would be the more standard way to say this, but Alpaca returns no
  Greeks on this account tier (see ``fetch_option_chain``), so moneyness is the
  honest measure available. A fixed band is also reproducible — the same chain always
  yields the same strike, which a delta surface would not.
- **Live bid, tight spread, minimum premium.** These are sell-to-open orders: a
  contract with no bid cannot be sold at all, and a contract whose spread is a large
  fraction of its own mid hands most of the premium to the market maker. Both are
  execution-quality filters, not Shariah ones.
- **Standard 100-share multiplier only.** A contract adjusted by a split or merger
  carries a non-standard deliverable, and 100 shares would no longer cover one call.
  The coverage arithmetic downstream assumes 100; anything else is rejected rather
  than mis-sized.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from option_structure_gate import SHARES_PER_CONTRACT


# Every knob the selection rule turns, in one place, so a policy change is a data
# change and the rationale text keeps describing what actually happened.
DEFAULT_POLICY = {
    "min_dte": 1,
    "max_dte": 7,
    "target_otm_pct": 4.0,
    "min_otm_pct": 2.0,
    "max_otm_pct": 7.0,
    "min_premium_per_share": 0.05,
    "max_spread_pct_of_mid": 15.0,
}

STRATEGIES = {
    "COVERED_CALL": {"option_type": "CALL", "direction": 1},
    "CASH_SECURED_PUT": {"option_type": "PUT", "direction": -1},
}


def resolve_policy(overrides: dict | None = None) -> dict:
    policy = dict(DEFAULT_POLICY)
    policy.update({key: value for key, value in (overrides or {}).items() if value is not None})
    return policy


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def select_covered_call(
    underlying: str,
    *,
    shares_held: int,
    spot: float,
    chain: list | None = None,
    as_of=None,
    max_contracts: int | None = None,
    policy: dict | None = None,
) -> dict:
    """Pick the call to write against shares already owned.

    ``shares_held`` is the settled long position from ``portfolio_store``, not a
    target. One contract obliges delivery of 100 shares, so 100 owned shares is the
    minimum order size and the position is the hard cap on how many can be written.
    """
    capacity = int(shares_held or 0) // SHARES_PER_CONTRACT
    if capacity < 1:
        return {
            "status": "INSUFFICIENT_SHARES",
            "strategy": "COVERED_CALL",
            "underlying": _root(underlying),
            "reason": (
                f"{int(shares_held or 0)} shares held; writing one covered call requires "
                f"{SHARES_PER_CONTRACT}"
            ),
        }
    return _select(
        "COVERED_CALL",
        underlying,
        spot=spot,
        chain=chain,
        as_of=as_of,
        policy=policy,
        max_contracts=_cap(capacity, max_contracts),
        sizer=lambda strike: capacity,
        collateral={"shares_held": int(shares_held or 0)},
    )


def select_cash_secured_put(
    underlying: str,
    *,
    cash_available: float,
    spot: float,
    chain: list | None = None,
    as_of=None,
    max_contracts: int | None = None,
    policy: dict | None = None,
) -> dict:
    """Pick the put to write against cash already settled.

    ``cash_available`` must be settled cash, never buying power — buying power is a
    margin figure, and a put backed by margin is not cash-secured. Sizing is per
    strike, because a higher strike ties up more cash for the same one contract.
    """
    cash = float(cash_available or 0.0)
    if cash <= 0:
        return {
            "status": "INSUFFICIENT_CASH",
            "strategy": "CASH_SECURED_PUT",
            "underlying": _root(underlying),
            "reason": "no settled cash available to secure a put",
        }
    return _select(
        "CASH_SECURED_PUT",
        underlying,
        spot=spot,
        chain=chain,
        as_of=as_of,
        policy=policy,
        max_contracts=max_contracts,
        sizer=lambda strike: int(cash // (strike * SHARES_PER_CONTRACT)),
        collateral={"cash_available": cash},
    )


# ---------------------------------------------------------------------------
# Selection core
# ---------------------------------------------------------------------------


def _select(
    strategy: str,
    underlying: str,
    *,
    spot,
    chain,
    as_of,
    policy,
    max_contracts,
    sizer,
    collateral: dict,
) -> dict:
    root = _root(underlying)
    settings = resolve_policy(policy)
    option_type = STRATEGIES[strategy]["option_type"]

    spot_price = _number(spot)
    if not root:
        return {"status": "INVALID_INPUT", "strategy": strategy, "underlying": root, "reason": "underlying_required"}
    if spot_price is None or spot_price <= 0:
        return {
            "status": "INVALID_INPUT",
            "strategy": strategy,
            "underlying": root,
            "reason": "a positive spot price is required to measure moneyness",
        }

    today = _as_date(as_of) or date.today()
    window = (today + timedelta(days=settings["min_dte"]), today + timedelta(days=settings["max_dte"]))

    if chain is None:
        chain, source = _load_chain(root, option_type, window)
        if chain is None:
            return {"status": "CHAIN_UNAVAILABLE", "strategy": strategy, "underlying": root, "reason": source}
    else:
        source = "provided"

    ranked, rejected = rank_candidates(
        chain,
        strategy=strategy,
        spot=spot_price,
        today=today,
        policy=settings,
    )

    if not ranked:
        return {
            "status": "NO_CANDIDATE",
            "strategy": strategy,
            "underlying": root,
            "reason": _no_candidate_reason(rejected, settings),
            "spot": spot_price,
            "policy": settings,
            "chain_source": source,
            "considered": len(chain),
            "rejected": rejected,
        }

    # Walk the ranking rather than committing to the top strike: for a cash-secured
    # put the best-ranked strike may tie up more cash than is settled, and the next
    # one down is both cheaper to secure and still inside the band.
    unaffordable = 0
    for candidate in ranked:
        contracts = _cap(max(int(sizer(candidate["strike"])), 0), max_contracts)
        if contracts < 1:
            unaffordable += 1
            continue
        return _selection(
            strategy=strategy,
            root=root,
            candidate=candidate,
            contracts=contracts,
            spot=spot_price,
            settings=settings,
            collateral=collateral,
            source=source,
            considered=len(chain),
            rejected=rejected,
            ranked=ranked,
            skipped_for_size=unaffordable,
        )

    cheapest = min(ranked, key=lambda row: row["strike"])
    required = cheapest["strike"] * SHARES_PER_CONTRACT
    return {
        "status": "INSUFFICIENT_CASH" if strategy == "CASH_SECURED_PUT" else "INSUFFICIENT_SHARES",
        "strategy": strategy,
        "underlying": root,
        "reason": (
            f"{len(ranked)} contracts passed the strike screen but none could be secured; "
            f"the cheapest, strike {cheapest['strike']:.2f}, needs {required:,.2f} in collateral"
        ),
        "spot": spot_price,
        "policy": settings,
        "rejected": rejected,
    }


def _selection(
    *,
    strategy,
    root,
    candidate,
    contracts,
    spot,
    settings,
    collateral,
    source,
    considered,
    rejected,
    ranked,
    skipped_for_size,
) -> dict:
    premium = candidate["premium"]
    credit = round(premium * SHARES_PER_CONTRACT * contracts, 2)
    option_contract = {
        "strategy": strategy,
        "option_type": candidate["option_type"],
        "underlying": root,
        "strike": candidate["strike"],
        "expiration": candidate["expiration"],
        "occ_symbol": candidate["symbol"],
    }
    result = {
        "status": "SELECTED",
        "strategy": strategy,
        "underlying": root,
        "option_contract": option_contract,
        "side": "SELL",
        "contracts": contracts,
        "price": premium,
        "premium_per_share": premium,
        "estimated_credit": credit,
        "spot": spot,
        "otm_pct": candidate["otm_pct"],
        "dte": candidate["dte"],
        "bid": candidate["bid"],
        "ask": candidate["ask"],
        "spread_pct_of_mid": candidate["spread_pct_of_mid"],
        "policy": settings,
        "chain_source": source,
        "considered": considered,
        "rejected": rejected,
        "ranked": len(ranked),
        "skipped_for_size": skipped_for_size,
        **collateral,
    }
    if strategy == "CASH_SECURED_PUT":
        result["cash_required"] = round(candidate["strike"] * SHARES_PER_CONTRACT * contracts, 2)
    else:
        result["shares_committed"] = contracts * SHARES_PER_CONTRACT
    result["rationale"] = build_selection_rationale(result)
    return result


def rank_candidates(chain, *, strategy: str, spot: float, today, policy: dict):
    """Filter a chain to eligible contracts, best first. Pure: no I/O, no clock.

    Returns ``(ranked, rejected)`` where ``rejected`` counts why each discarded
    contract was discarded — that tally is what lets the rationale say "9 outside the
    band, 2 with no bid" instead of just "none matched".
    """
    option_type = STRATEGIES[strategy]["option_type"]
    direction = STRATEGIES[strategy]["direction"]
    rejected: dict = {}
    eligible = []

    for row in chain or []:
        if not isinstance(row, dict):
            _count(rejected, "malformed_row")
            continue
        if str(row.get("option_type") or "").upper() != option_type:
            _count(rejected, "wrong_option_type")
            continue
        if not row.get("tradable") or str(row.get("status") or "active").lower() != "active":
            _count(rejected, "not_tradable")
            continue
        if int(row.get("multiplier") or 0) != SHARES_PER_CONTRACT:
            _count(rejected, "non_standard_multiplier")
            continue

        expiry = _as_date(row.get("expiration"))
        if expiry is None:
            _count(rejected, "unparseable_expiration")
            continue
        dte = (expiry - today).days
        if dte < policy["min_dte"] or dte > policy["max_dte"]:
            _count(rejected, "outside_dte_window")
            continue

        strike = _number(row.get("strike"))
        if strike is None or strike <= 0:
            _count(rejected, "invalid_strike")
            continue

        # Signed so both strategies share one comparison: a call is OTM above spot,
        # a put is OTM below it.
        otm_pct = round(direction * (strike - spot) / spot * 100, 4)
        if otm_pct < policy["min_otm_pct"] or otm_pct > policy["max_otm_pct"]:
            _count(rejected, "outside_otm_band")
            continue

        bid = _number(row.get("bid"))
        ask = _number(row.get("ask"))
        if bid is None or bid <= 0:
            _count(rejected, "no_live_bid")
            continue

        premium = _number(row.get("mid"))
        if premium is None or premium <= 0:
            premium = bid
        if premium < policy["min_premium_per_share"]:
            _count(rejected, "premium_below_floor")
            continue

        spread_pct = None
        if ask is not None and ask > 0:
            if ask < bid:
                _count(rejected, "crossed_quote")
                continue
            spread_pct = round((ask - bid) / premium * 100, 4)
            if spread_pct > policy["max_spread_pct_of_mid"]:
                _count(rejected, "spread_too_wide")
                continue

        eligible.append(
            {
                "symbol": row.get("symbol"),
                "option_type": option_type,
                "strike": strike,
                "expiration": row.get("expiration"),
                "dte": dte,
                "otm_pct": otm_pct,
                "premium": premium,
                "bid": bid,
                "ask": ask,
                "spread_pct_of_mid": spread_pct,
            }
        )

    # Closest to the OTM target wins. Ties break toward the later expiry (more premium
    # for the same assignment risk), then the higher premium, then the symbol, so the
    # same chain always produces the same choice.
    eligible.sort(
        key=lambda row: (
            abs(row["otm_pct"] - policy["target_otm_pct"]),
            -row["dte"],
            -row["premium"],
            str(row["symbol"] or ""),
        )
    )
    return eligible, rejected


# ---------------------------------------------------------------------------
# Narration
# ---------------------------------------------------------------------------

REJECTION_LABELS = {
    "wrong_option_type": "wrong option type",
    "not_tradable": "not tradable",
    "non_standard_multiplier": "non-standard multiplier (adjusted contract)",
    "unparseable_expiration": "unreadable expiration",
    "outside_dte_window": "outside the DTE window",
    "invalid_strike": "invalid strike",
    "outside_otm_band": "outside the OTM band",
    "no_live_bid": "no live bid",
    "crossed_quote": "crossed quote",
    "premium_below_floor": "premium below the floor",
    "spread_too_wide": "spread too wide",
    "malformed_row": "malformed chain row",
}


def build_selection_rationale(result: dict) -> str:
    """One line a human can read out loud and defend."""
    policy = result["policy"]
    contract = result["option_contract"]
    label = "covered call" if result["strategy"] == "COVERED_CALL" else "cash-secured put"
    breakdown = ", ".join(
        f"{count} {REJECTION_LABELS.get(reason, reason)}"
        for reason, count in sorted(result["rejected"].items(), key=lambda item: (-item[1], item[0]))
    )

    parts = [
        f"{result['underlying']} {label}: sell {result['contracts']}x {contract['occ_symbol']}",
        (
            f"strike {contract['strike']:.2f} is {result['otm_pct']:.1f}% OTM against a "
            f"{policy['target_otm_pct']:.1f}% target in a {policy['min_otm_pct']:.0f}-"
            f"{policy['max_otm_pct']:.0f}% band, spot {result['spot']:.2f}"
        ),
        (
            f"expires {contract['expiration']} in {result['dte']} days, inside the "
            f"{policy['min_dte']}-{policy['max_dte']} DTE window so it resolves rather than "
            f"staying open"
        ),
        f"premium {result['premium_per_share']:.2f}/share for {result['estimated_credit']:.2f} credit",
    ]
    if result["strategy"] == "COVERED_CALL":
        parts.append(
            f"covered by {result['shares_committed']} of {result['shares_held']} owned shares"
        )
    else:
        parts.append(
            f"secured by {result['cash_required']:.2f} of {result['cash_available']:.2f} settled cash"
        )
    parts.append(
        f"chosen from {result['considered']} contracts, {result['ranked']} eligible"
        + (f" ({breakdown})" if breakdown else "")
    )
    return "; ".join(parts) + "."


def _no_candidate_reason(rejected: dict, policy: dict) -> str:
    if not rejected:
        return "the option chain was empty"
    dominant, count = max(rejected.items(), key=lambda item: (item[1], item[0]))
    detail = REJECTION_LABELS.get(dominant, dominant)
    if dominant == "outside_otm_band":
        detail += f" ({policy['min_otm_pct']:.0f}-{policy['max_otm_pct']:.0f}%)"
    elif dominant == "outside_dte_window":
        detail += f" ({policy['min_dte']}-{policy['max_dte']} days)"
    return f"no contract passed the screen; most common rejection was {detail} ({count})"


# ---------------------------------------------------------------------------
# Chain access
# ---------------------------------------------------------------------------


def _load_chain(root: str, option_type: str, window):
    """Fetch the chain, returning (None, reason) rather than raising.

    Imported lazily so this module stays usable — and testable — without Alpaca
    credentials configured.
    """
    try:
        from alpaca_market_data import AlpacaDataError, fetch_option_chain
    except Exception as exc:
        return None, f"option_chain_import_failed:{type(exc).__name__}"

    try:
        rows, _ = fetch_option_chain(
            root,
            expiration_gte=window[0].isoformat(),
            expiration_lte=window[1].isoformat(),
            option_type=option_type,
        )
    except AlpacaDataError as exc:
        return None, f"option_chain_unavailable:{exc.error_code}"
    except Exception as exc:
        return None, f"option_chain_unavailable:{type(exc).__name__}"
    return rows, "alpaca"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _root(underlying) -> str:
    return str(underlying or "").strip().upper()


def _cap(value: int, ceiling):
    if ceiling is None:
        return value
    return min(value, max(int(ceiling), 0))


def _count(counter: dict, key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _number(value):
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None

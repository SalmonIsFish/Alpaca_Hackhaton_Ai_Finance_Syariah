"""Provision an Alpaca paper account: cash-equivalent posture, and a synced risk basis.

Two jobs, both idempotent, both dry-run by default and only writing with --apply:

1. Reduce the account to cash-equivalent posture (no margin, no shorting).
2. Sync ``PAPER_ACCOUNT_EQUITY`` in ``backend/.env`` to the account's real equity.

Run it against a fresh account -- as at the hackathon kickoff -- and both land in
one pass.

**Why the second job exists.** Every risk cap is a percentage of
``PAPER_ACCOUNT_EQUITY``, but that figure was a hardcoded default rather than
anything the broker told us. It sat at 10000 against an account holding ~99956,
a 10x mismatch that caps a position at $500 instead of $4998. It fails toward
rejection, so nothing unsafe gets through -- but it surfaces as an order refused
for ``position_limit`` on an account with ample equity, which reads as a gate bug
and is not one. Pointing the app at a new account without resyncing reintroduces
it silently, so the sync lives here, next to the other thing you do to a new
account.

The equity figure drifts as the account trades. That is expected; it is a
sizing basis, not an accounting record. Rerun this to refresh it.

Alpaca does not offer cash accounts -- "No, we do not offer cash accounts. All
accounts are set up as margin accounts."
(https://alpaca.markets/support/alpaca-cash-accounts)

The nearest honest equivalent is max_margin_multiplier="1", documented on the
account object as a "standard limited margin account with 1x buying power": the
broker extends no credit, buying_power collapses to settled cash, and nothing can
accrue interest because nothing can be borrowed. account_shariah_gate is not
touched -- account_type_from_multiplier already maps multiplier <= 1 to CASH, and
that mapping predates this script.

The account half is deliberately ONE-DIRECTIONAL: it can only tighten. It will
never raise max_margin_multiplier or re-enable shorting. Loosening is a
deliberate act that belongs in the Alpaca dashboard, not in a script this
repo can run. The equity half is not directional -- equity legitimately moves
both ways -- but it fails closed the same way: an absent, null, unparseable or
non-positive equity refuses rather than writing 0 or silently skipping, since
both of those leave the overlay mis-sized while the run still looks successful.

It only ever writes the ``backend/.env`` sitting next to this file, on the
machine it is invoked on. Run it on the VPS to sync the VPS; run it locally to
sync locally. Nothing here writes across machines.

See docs/shariah-policy/margin-account-policy.md for the fiqh reasoning and its
documented limitation.
"""

import json
import re
import sys
from pathlib import Path

from alpaca_paper_adapter import (
    ALPACA_PAPER_BASE_URL,
    alpaca_credentials,
    alpaca_request,
    check_alpaca_status,
)
from config import load_settings

TARGET_MULTIPLIER = "1"

# The .env this script keeps in sync is the one sitting next to it, i.e. on the
# machine it is invoked on. Run it on the VPS and the VPS's .env is updated; run
# it locally and the local one is. Nothing here writes across machines, exactly
# as the multiplier patch only ever touches the account its credentials point at.
ENV_PATH = Path(__file__).resolve().parent / ".env"

EQUITY_KEY = "PAPER_ACCOUNT_EQUITY"
# Anchored to the whole name so PAPER_ACCOUNT_EQUITY_NOTE is not mistaken for it.
EQUITY_LINE = re.compile(rf"^{EQUITY_KEY}\s*=.*$", re.MULTILINE)


def current_configuration(credentials: dict) -> dict:
    response = alpaca_request("GET", "/v2/account/configurations", credentials=credentials)
    if not response.get("ok"):
        raise SystemExit(f"could not read account configurations: {response.get('reason')}")
    return response.get("data") or {}


def tighten(config: dict, *, disable_shorting: bool) -> dict:
    """Build the patch, refusing anything that would loosen the account."""
    patch = {}

    # An unreadable multiplier means the account's real margin capability is
    # unknown. Omitting it from the patch would leave a 4x account at 4x while
    # the run still reported success, and account_shariah_gate would then reject
    # every order for a reason nobody is looking at. Fail closed instead.
    raw = config.get("max_margin_multiplier")
    try:
        existing = float(raw)
    except (TypeError, ValueError):
        raise SystemExit(
            f"cannot read max_margin_multiplier (got {raw!r}); refusing to patch an account "
            "whose margin capability is unknown"
        ) from None

    if existing > float(TARGET_MULTIPLIER):
        patch["max_margin_multiplier"] = TARGET_MULTIPLIER
    elif existing < float(TARGET_MULTIPLIER):
        raise SystemExit(
            f"refusing to raise max_margin_multiplier from {existing} to {TARGET_MULTIPLIER}"
        )

    if disable_shorting and not config.get("no_shorting"):
        patch["no_shorting"] = True

    return patch


def equity_from_account(payload) -> float:
    """Read the account's real equity, refusing anything unreadable.

    Same discipline as the multiplier above, and for the same reason b6cd5f7
    exists: a ``float(None or 0)`` here would write 0, sizing every risk cap at
    zero so the overlay rejects everything; and silently skipping the update
    would be worse still, leaving the overlay sized against the OLD equity with
    no visible symptom at all. Both look like a successful run. Refuse instead.

    ``equity``, not ``cash``: the overlay measures exposure against the whole
    book, and cash alone understates it once anything is held.
    """
    raw = (payload or {}).get("equity")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise SystemExit(
            f"cannot read account equity (got {raw!r}); refusing to size the risk "
            "overlay against a figure the broker did not give us"
        ) from None

    if value <= 0:
        raise SystemExit(
            f"account equity came back as {value}; refusing to write a "
            "non-positive equity, which would reject every order"
        )
    return value


def apply_env_equity(text: str, equity: float) -> str:
    """Replace the PAPER_ACCOUNT_EQUITY line, or append it, leaving the rest alone.

    Patch, don't clobber: every other line -- comments, credentials, risk limits
    -- must survive byte for byte. Rewriting the file from parsed settings would
    silently drop anything this script does not know about.
    """
    line = f"{EQUITY_KEY}={equity:.2f}"
    if EQUITY_LINE.search(text):
        return EQUITY_LINE.sub(line, text, count=1)
    separator = "" if text == "" or text.endswith("\n") else "\n"
    return f"{text}{separator}{line}\n"


def env_equity(text: str) -> float | None:
    """The PAPER_ACCOUNT_EQUITY currently written in the file, if it is readable."""
    match = EQUITY_LINE.search(text)
    if match is None:
        return None
    try:
        return float(match.group(0).split("=", 1)[1].strip())
    except (IndexError, ValueError):
        return None


def sync_env_equity(env_path: Path, payload, *, apply_changes: bool) -> dict:
    """Bring PAPER_ACCOUNT_EQUITY in ``env_path`` up to the account's real equity.

    Reads the equity first, so an unreadable one refuses before the file is
    opened for writing rather than after a partial write.
    """
    equity = equity_from_account(payload)

    env_path = Path(env_path)
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    before = env_equity(text)

    report = {"path": str(env_path), "before": before, "after": equity}

    if before is not None and f"{before:.2f}" == f"{equity:.2f}":
        return {**report, "status": "UNCHANGED"}
    if not apply_changes:
        return {**report, "status": "DRY_RUN"}

    env_path.write_text(apply_env_equity(text, equity), encoding="utf-8")
    return {**report, "status": "UPDATED"}


def main() -> None:
    settings = load_settings()
    if settings.alpaca_mode != "paper":
        raise SystemExit("refusing to run outside paper mode")

    disable_shorting = "--no-shorting" in sys.argv
    apply_changes = "--apply" in sys.argv

    credentials = alpaca_credentials()
    if credentials is None:
        raise SystemExit("ALPACA_API_KEY_ID / ALPACA_SECRET_KEY are not configured")

    print(f"base url:  {ALPACA_PAPER_BASE_URL}")
    before_status = check_alpaca_status()
    print(
        f"account:   {before_status.get('account_suffix')}  type={before_status.get('account_type')}"
    )

    config = current_configuration(credentials)
    print(
        f"before:    max_margin_multiplier={config.get('max_margin_multiplier')} no_shorting={config.get('no_shorting')}"
    )

    patch = tighten(config, disable_shorting=disable_shorting)
    if not patch:
        print("nothing to change; the account is already at cash-equivalent posture.")
    else:
        print(f"patch:     {json.dumps(patch)}")

    if patch and apply_changes:
        response = alpaca_request(
            "PATCH", "/v2/account/configurations", credentials=credentials, body=patch
        )
        if not response.get("ok"):
            raise SystemExit(
                f"patch failed ({response.get('status_code')}): {json.dumps(response.get('data'))}"
            )

        after = response.get("data") or {}
        print(
            f"after:     max_margin_multiplier={after.get('max_margin_multiplier')} no_shorting={after.get('no_shorting')}"
        )

        after_status = check_alpaca_status()
        print(
            f"account:   {after_status.get('account_suffix')}  type={after_status.get('account_type')}"
        )
        if after_status.get("account_type") != "CASH":
            print(
                "\nWARNING: account still does not report CASH; account_shariah_gate will keep rejecting."
            )

    # ---------------------------------------------------------------- equity
    # The risk overlay sizes every cap off PAPER_ACCOUNT_EQUITY. Left to drift it
    # silently mis-sizes them -- a hardcoded 10000 against a ~99956 account caps a
    # position at $500 instead of $4998, which surfaces on judging day as a
    # rejection that looks exactly like a gate bug. Sync it here so the kickoff
    # account swap cannot reintroduce the drift.
    account = alpaca_request("GET", "/v2/account", credentials=credentials)
    if not account.get("ok"):
        raise SystemExit(f"could not read the account: {account.get('reason')}")

    equity_report = sync_env_equity(ENV_PATH, account.get("data"), apply_changes=apply_changes)
    before_text = "absent" if equity_report["before"] is None else f"{equity_report['before']:.2f}"
    print(
        f"\nequity:    broker={equity_report['after']:.2f}  "
        f"{EQUITY_KEY}={before_text}  -> {equity_report['status']}"
    )
    print(f"           {equity_report['path']}")

    if not apply_changes:
        print("\ndry run. nothing was written; re-run with --apply.")
        return


if __name__ == "__main__":
    main()

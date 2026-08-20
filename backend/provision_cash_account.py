"""Reduce an Alpaca paper account to cash-equivalent posture (no margin, no shorting).

Alpaca does not offer cash accounts -- "No, we do not offer cash accounts. All
accounts are set up as margin accounts."
(https://alpaca.markets/support/alpaca-cash-accounts)

The nearest honest equivalent is max_margin_multiplier="1", documented on the
account object as a "standard limited margin account with 1x buying power": the
broker extends no credit, buying_power collapses to settled cash, and nothing can
accrue interest because nothing can be borrowed. account_shariah_gate is not
touched -- account_type_from_multiplier already maps multiplier <= 1 to CASH, and
that mapping predates this script.

This tool is deliberately ONE-DIRECTIONAL: it can only tighten the account. It
will never raise max_margin_multiplier or re-enable shorting. Loosening is a
deliberate act that belongs in the Alpaca dashboard, not in a script this
repo can run.

See docs/shariah-policy/margin-account-policy.md for the fiqh reasoning and its
documented limitation.
"""

import json
import sys

from alpaca_paper_adapter import (
    ALPACA_PAPER_BASE_URL,
    alpaca_credentials,
    alpaca_request,
    check_alpaca_status,
)
from config import load_settings

TARGET_MULTIPLIER = "1"


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
        return

    print(f"patch:     {json.dumps(patch)}")
    if not apply_changes:
        print("\ndry run. re-run with --apply to write this to the broker account.")
        return

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


if __name__ == "__main__":
    main()

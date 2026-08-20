"""Verify provision_cash_account.tighten() only ever tightens, and fails closed.

This script is the one tool in the repo that changes a real broker account, and
it gets rerun against a brand-new account at hackathon kickoff. The network is
never touched here -- ``tighten`` is a pure function over the configuration dict
that ``/v2/account/configurations`` returns, so every case below is just that
dict shaped the way a fresh account might present it.

The property under test is one-directionality: given any configuration, the
patch ``tighten`` builds must never grant the account more capability than it
already has, and any configuration it cannot read must be refused rather than
quietly under-applied.
"""

import provision_cash_account


def patch_for(config, *, disable_shorting=True):
    return provision_cash_account.tighten(config, disable_shorting=disable_shorting)


def refused(config, *, disable_shorting=True):
    try:
        patch_for(config, disable_shorting=disable_shorting)
    except SystemExit as exc:
        return str(exc)
    return None


def main() -> None:
    # ------------------------------------------------- a fresh account tightens
    # Alpaca creates every paper account as margin; 4x is what a new one shows.
    assert patch_for({"max_margin_multiplier": "4", "no_shorting": False}) == {
        "max_margin_multiplier": "1",
        "no_shorting": True,
    }
    assert patch_for({"max_margin_multiplier": "2", "no_shorting": False}) == {
        "max_margin_multiplier": "1",
        "no_shorting": True,
    }

    # ------------------------------------------------- a rerun is a no-op
    # Kickoff may involve running this twice. The second run must ask for nothing.
    assert patch_for({"max_margin_multiplier": "1", "no_shorting": True}) == {}

    # --------------------------------------- partial state is completed, not undone
    assert patch_for({"max_margin_multiplier": "1", "no_shorting": False}) == {"no_shorting": True}

    # ------------------------------------------------- it never loosens shorting
    # Without --no-shorting the flag is left alone; it is never set back to False.
    assert patch_for(
        {"max_margin_multiplier": "4", "no_shorting": True}, disable_shorting=False
    ) == {"max_margin_multiplier": "1"}
    assert "no_shorting" not in patch_for(
        {"max_margin_multiplier": "4", "no_shorting": True}, disable_shorting=True
    )

    # ------------------------------------------------- it never raises the multiplier
    message = refused({"max_margin_multiplier": "0.5", "no_shorting": True})
    assert message and "refusing to raise" in message, message

    # ------------------------------------- an unreadable multiplier fails closed
    # This is the case that matters at kickoff. If the field is absent, null, or
    # unparseable, the account's real margin capability is UNKNOWN. Building a
    # patch that silently omits max_margin_multiplier would leave a 4x account at
    # 4x while the run still looks successful -- and account_shariah_gate would
    # then reject every order for a reason nobody is looking at. The repo's rule
    # is to fail closed on anything unknown, so this must refuse.
    for config in (
        {"no_shorting": False},
        {"max_margin_multiplier": None, "no_shorting": False},
        {"max_margin_multiplier": "", "no_shorting": False},
        {"max_margin_multiplier": "abc", "no_shorting": False},
    ):
        message = refused(config)
        assert message is not None, f"unreadable multiplier must refuse, got a patch for {config}"
        assert "max_margin_multiplier" in message, message

    print("PASS: provision_cash_account.tighten only tightens and refuses an unreadable account.")


if __name__ == "__main__":
    main()

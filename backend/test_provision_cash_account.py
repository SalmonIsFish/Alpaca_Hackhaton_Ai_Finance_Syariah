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

The script has a second job: keeping ``PAPER_ACCOUNT_EQUITY`` in ``backend/.env``
synced to the account's real equity, so the risk overlay is never sized against a
stale figure. That half is tested the same way -- ``equity_from_account`` is a pure
function over the ``/v2/account`` payload, and ``apply_env_equity`` is a pure
function over the text of a ``.env`` file. Only ``sync_env_equity`` touches disk,
and it is tested against a temporary file, never the real ``backend/.env``.

Why it matters: the overlay ran against a hardcoded 10000 while the account held
~99956 -- a 10x mismatch that caps a position at $500 instead of $4998. It fails
toward rejection, so nothing unsafe slips through, but it would surface on judging
day as a confusing rejection that looks exactly like a gate bug.
"""

import tempfile
from pathlib import Path

import provision_cash_account


def patch_for(config, *, disable_shorting=True):
    return provision_cash_account.tighten(config, disable_shorting=disable_shorting)


def refused(config, *, disable_shorting=True):
    try:
        patch_for(config, disable_shorting=disable_shorting)
    except SystemExit as exc:
        return str(exc)
    return None


def refused_equity(payload):
    try:
        provision_cash_account.equity_from_account(payload)
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

    # =====================================================================
    # PAPER_ACCOUNT_EQUITY sync
    # =====================================================================

    # ------------------------------------------------ equity is read as a number
    assert provision_cash_account.equity_from_account({"equity": "99955.94"}) == 99955.94
    assert provision_cash_account.equity_from_account({"equity": 100000}) == 100000.0

    # ---------------------------------------- an unreadable equity fails closed
    # Same rationale as the multiplier above, and the same bug shape as b6cd5f7's
    # float(None or 0): writing 0 would size every risk cap at zero and reject
    # everything, and silently skipping would leave the overlay on the OLD equity
    # with no visible symptom at all -- the worse of the two, because it looks
    # like a successful run. Refuse loudly instead.
    for payload in ({}, {"equity": None}, {"equity": ""}, {"equity": "abc"}, None):
        message = refused_equity(payload)
        assert message is not None, f"unreadable equity must refuse, got a value for {payload}"
        assert "equity" in message, message

    # A non-positive equity is not a readable account either.
    for payload in ({"equity": "0"}, {"equity": "-5"}):
        assert refused_equity(payload) is not None, f"{payload} must refuse"

    # ------------------------------------ the .env patch replaces, never clobbers
    original = (
        "# Amanah Trader\n"
        "ALPACA_API_KEY_ID=redacted\n"
        "PAPER_ACCOUNT_EQUITY=10000\n"
        "MAX_POSITION_PCT=5.0\n"
    )
    patched = provision_cash_account.apply_env_equity(original, 99955.94)
    assert "PAPER_ACCOUNT_EQUITY=99955.94" in patched, patched
    assert "PAPER_ACCOUNT_EQUITY=10000" not in patched, patched
    # Every other line survives untouched -- the "patch, don't clobber" discipline
    # the margin-multiplier fix already established.
    for line in ("# Amanah Trader", "ALPACA_API_KEY_ID=redacted", "MAX_POSITION_PCT=5.0"):
        assert line in patched, f"{line!r} was lost by the patch:\n{patched}"
    assert len(patched.splitlines()) == len(original.splitlines()), patched

    # ------------------------------------------- absent means append, not ignore
    without = "ALPACA_API_KEY_ID=redacted\nMAX_POSITION_PCT=5.0\n"
    appended = provision_cash_account.apply_env_equity(without, 12345.67)
    assert "PAPER_ACCOUNT_EQUITY=12345.67" in appended, appended
    assert "ALPACA_API_KEY_ID=redacted" in appended, appended
    assert "MAX_POSITION_PCT=5.0" in appended, appended

    # A similarly-named variable must not be mistaken for the real one.
    lookalike = "PAPER_ACCOUNT_EQUITY_NOTE=do not touch\n"
    result = provision_cash_account.apply_env_equity(lookalike, 500.0)
    assert "PAPER_ACCOUNT_EQUITY_NOTE=do not touch" in result, result
    assert "PAPER_ACCOUNT_EQUITY=500.00" in result, result

    # ================================================== sync_env_equity, on disk
    with tempfile.TemporaryDirectory() as tmp:
        env_path = Path(tmp) / ".env"

        # ------------------------------------------------ a fresh run writes it
        env_path.write_text(original, encoding="utf-8")
        report = provision_cash_account.sync_env_equity(
            env_path, {"equity": "99955.94"}, apply_changes=True
        )
        assert report["status"] == "UPDATED", report
        assert report["before"] == 10000.0, report
        assert report["after"] == 99955.94, report
        written = env_path.read_text(encoding="utf-8")
        assert "PAPER_ACCOUNT_EQUITY=99955.94" in written, written
        # ...and the write went through apply_env_equity rather than rewriting the
        # file. Asserting only that the new value is present passes just as well
        # when the whole file has been replaced by that single line -- a mutation
        # check caught exactly that blind spot here, so the surviving lines are
        # asserted on disk and not only in the pure-function test above.
        for line in ("# Amanah Trader", "ALPACA_API_KEY_ID=redacted", "MAX_POSITION_PCT=5.0"):
            assert line in written, f"{line!r} was lost when syncing to disk:\n{written}"
        assert len(written.splitlines()) == len(original.splitlines()), written

        # ------------------------------------------- a rerun at the same equity
        # Kickoff may involve running this twice, exactly as for the multiplier.
        # The file must end up correct, and must not accumulate lines.
        after_first = env_path.read_text(encoding="utf-8")
        rerun = provision_cash_account.sync_env_equity(
            env_path, {"equity": "99955.94"}, apply_changes=True
        )
        assert rerun["status"] == "UNCHANGED", rerun
        assert env_path.read_text(encoding="utf-8") == after_first, "rerun altered the file"

        # ---------------------------------------------- a dry run writes nothing
        before_dry = env_path.read_text(encoding="utf-8")
        dry = provision_cash_account.sync_env_equity(
            env_path, {"equity": "12345.67"}, apply_changes=False
        )
        assert dry["status"] == "DRY_RUN", dry
        assert dry["after"] == 12345.67, dry
        assert env_path.read_text(encoding="utf-8") == before_dry, "dry run wrote to the file"

        # -------------------------------- an unreadable equity leaves .env alone
        # The refusal must happen BEFORE any write, not after a partial one.
        before_bad = env_path.read_text(encoding="utf-8")
        for payload in ({}, {"equity": None}, {"equity": "abc"}):
            try:
                provision_cash_account.sync_env_equity(env_path, payload, apply_changes=True)
            except SystemExit:
                pass
            else:
                raise AssertionError(f"unreadable equity must refuse, got a write for {payload}")
            assert env_path.read_text(encoding="utf-8") == before_bad, (
                f"the .env file was modified despite an unreadable equity: {payload}"
            )

    print("PASS: provision_cash_account.tighten only tightens and refuses an unreadable account.")
    print(
        "PASS: PAPER_ACCOUNT_EQUITY syncs to real equity, patches without clobbering, fails closed."
    )


if __name__ == "__main__":
    main()

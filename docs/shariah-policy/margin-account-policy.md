# Policy record — trading through an Alpaca paper account

Status: **decision pending scholar review.** Recorded 2026-08-19.
Raised by: `NEXT_STEPS.md` → "Blocker to resolve before any live demo".

This file exists because `account_shariah_gate` blocked every order against the
configured broker account, and the only available remedy is a change to the *account*,
not the code. `NEXT_STEPS.md` required that such a change be documented and
scholar-reviewable rather than silently applied. This is that document.

## The finding

`account_shariah_gate.check_account` rejects `MARGIN` outright, for every order type
including plain equity, on the stated rationale:

> carrying margin capability at all is a standing Riba exposure regardless of whether a
> given order draws on it

Verified against live paper account `0TCX` on 2026-08-19:

| field | value |
|---|---|
| `multiplier` | `"4"` |
| `buying_power` | `400000` |
| `cash` | `100000` |
| `shorting_enabled` | `true` |

The gate was correct. The account really did carry 4× leverage. Evidence of the
rejection, captured through the real FastAPI app against the real broker and real SEC
EDGAR filings before any change was made, is in
`docs/live-trade-evidence/before-CVX.json`: preview `READY_FOR_APPROVAL` (CVX @ 203.92,
Shariah PASS, debt 13.3% / cash 2.2%), approval `REJECT — margin_account_not_permitted`.

## Alpaca offers no cash account

From Alpaca's own support documentation:

> "No, we do not offer cash accounts. All accounts are set up as margin accounts."
> — <https://alpaca.markets/support/alpaca-cash-accounts>

So the preferred remedy in `NEXT_STEPS.md` — "provision an Alpaca paper account
configured as CASH" — is not available. Not "not found yet"; genuinely not offered.
Creating additional paper accounts does not help, as all of them are margin accounts.

## The remedy applied

`PATCH /v2/account/configurations` with `max_margin_multiplier: "1"`, and
`no_shorting: true`. Alpaca documents multiplier 1 as a *"standard limited margin
account with 1x buying power"*. After the change the broker extends no credit,
`buying_power` equals settled `cash`, and no share borrowing is possible.

`account_shariah_gate` was **not modified**. Neither was
`alpaca_paper_adapter.account_type_from_multiplier`, which already mapped
`multiplier <= 1` to `CASH` and predates this problem. The account changed to satisfy
the gate; the gate did not change to accept the account. Applied via
`backend/provision_cash_account.py`, which is deliberately one-directional — it can
only tighten the account, and refuses to raise the multiplier or re-enable shorting.

## The argument for accepting this

The gate names a specific harm: *margin capability* as a standing Riba exposure. At 1×
that capability is absent. No credit line is extended, so no interest can accrue on
one. There is no `Riba al-Nasiyah` here because there is no debt and no deferral — see
`Riba.md`. Disabling shorting additionally removes the sale of borrowed shares, which
is a separate objection (selling what one does not own) and not one the Riba gate was
written to catch.

## The argument against, and the honest limitation

Two objections a reviewer should weigh, neither of which this document claims to settle:

1. **The account remains contractually a margin account.** Alpaca's customer agreement
   permits margin; the 1× cap is a revocable configuration, not a structural property of
   the account. Under the strict reading — that entering the margin agreement is itself
   the impermissible act, irrespective of use — this remedy does not cure the defect,
   and the conclusion is that Alpaca cannot be used for this system at all, by anyone.
   That conclusion is coherent and should not be dismissed for being inconvenient.

2. **The cap is revocable, so the guarantee is only as good as the check.** This is
   partly mitigated by construction: `local_api.broker_account_context` re-reads
   `multiplier` from the live account on *every* approval, so if the cap were raised
   again the gate would immediately resume rejecting. The system does not cache the
   account type or take it on trust. What it cannot do is prevent the change.

The correct claim to make about this account is therefore **"no margin capability is
extended to it"** — not "this is a cash account". The system should not assert the
latter, and this repository's marketing, demo narration, and submission material should
not either.

## Deliberately not relied upon

That this is a paper account. No real money, no real credit, no real interest — the
argument is available and it is not wrong. It is excluded because `CLAUDE.md` treats
paper as a faithful rehearsal of live, and an exemption that rests on "it is only paper"
would justify waiving every other gate on the same grounds.

## Open for review

- Is a 1×-capped margin account acceptable, or is the margin agreement itself
  disqualifying?
- If disqualifying: is there a broker offering true cash accounts with an API of
  comparable coverage, and is that a change this project should make?
- Should `account_shariah_gate` additionally reject `shorting_enabled: true`? The
  account object exposes it, the gate currently ignores it, and short selling is a
  distinct prohibition from Riba. This would be a *strengthening* of the gate, so it is
  safe to add, but it is a scope decision rather than a bug fix.

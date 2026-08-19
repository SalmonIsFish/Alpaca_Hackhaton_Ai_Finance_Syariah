# Alpaca Paper Trading Account Types — Research Findings

**Research Date:** 2026-08-19  
**Status:** BLOCKING ISSUE IDENTIFIED  
**Urgency:** Terminal 2 cannot proceed without understanding this

## Summary

**Alpaca does not offer dedicated cash-only accounts.** All accounts — including paper trading accounts — are opened as margin accounts by default. There is no configuration option to provision a cash-only paper account.

## Detailed Findings

### Account Structure
- **Default account type:** All accounts are opened as **margin accounts**
- **No cash account option:** Alpaca explicitly does not support cash-only accounts as a separate product offering
- **Account with <$2,000 equity:** Treated as a "limited margin account" (restricted to 1x buying power), but still technically a margin account

### Paper Trading Context
- Paper-only accounts (globally available, email sign-up only) default to the same margin structure
- Live brokerage accounts can use paper trading alongside real trading, also in margin structure
- No mechanism exists to specify "cash only" when provisioning either account type

### Regulatory / Policy Context
- The margin structure reflects SEC Regulation T (Reg T), which is Alpaca's standard account framework
- A $2,000 equity threshold determines whether an account has access to higher leverage (Reg T 4x intraday buying power)
- Limited margin accounts (< $2,000) receive restricted 1x buying power but remain margin accounts

## Impact on Amanah Trader

**The blocker:** `account_shariah_gate` in `backend/account_shariah_gate.py` rejects all margin accounts outright as a matter of Shariah compliance, with the comment/check for `margin_account_not_permitted`. The current test account is a margin account, so every order fails the gate, whether equity or option.

**Options forward:**
1. **Policy decision path** (recommended): Define how Amanah should treat a mandatory-margin environment when Shariah compliance forbids margin financing. This is not a code bypass — it's a scholar-reviewable policy decision about what "no margin" means when the broker doesn't offer an alternative.

   Possible framings:
   - A margin-structured account used exclusively at 1x buying power (no leverage drawn) can be treated as functionally equivalent to cash
   - Paper trading margin accounts carry no interest charges (unlike live margin), so Riba risk is theoretical rather than actual
   - The gate should distinguish between account *structure* (how Alpaca labels it) and account *usage* (what leverage is actually drawn)

2. **Workaround path (not recommended):** Modify the test account setup to manually limit buying power to 1x equivalents via API constraints, and update the gate to check actual available buying power rather than account type. Still requires policy clarity on what "Shariah compliance under mandatory margin" means.

3. **Documentation path:** Accept that this is a known limitation of the hackathon's paper-trading-only scope, document it prominently, and ensure the Shariah Advisory logic is sound for the case where margin is *available but not used*.

## Recommendation for Terminal 2

Before proceeding, clarify with the project stakeholders (fiqh advisors, if available) whether a margin-structured account used at 1x buying power counts as Shariah-compliant or requires a policy override. Once that decision is made, `account_shariah_gate` can be updated to reflect it.

The current test account is the reality; Alpaca's fresh hackathon account (created when the event starts) will also be margin-structured.

## Sources
- [Alpaca Support: Can I have a cash account with Alpaca?](https://alpaca.markets/support/alpaca-cash-accounts)
- [Alpaca Support: What types of accounts does Alpaca offer?](https://alpaca.markets/support/types-accounts-alpaca-offers)
- [Alpaca Docs: Margin and Short Selling](https://docs.alpaca.markets/us/docs/margin-and-short-selling)
- [Alpaca Docs: Trading Account](https://docs.alpaca.markets/us/docs/account-plans)
- [Alpaca Docs: Paper Trading](https://docs.alpaca.markets/us/docs/paper-trading)

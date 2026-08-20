# Demo Video Script — DRAFT

**Status:** Draft narration for user to edit for voice and delivery style  
**Length:** 3–5 minutes  
**Evidence base:** Real Alpaca paper account (0TCX), verified trades from docs/live-trade-evidence/  
**Purpose:** Show the gate chain in action, demonstrating both approval and rejection in a real trade flow

---

## Video Shot-by-Shot Outline (Time Budget)

| Time | Shot | Visual | Narration Notes |
|---|---|---|---|
| 0:00–0:30 | Title/Intro | Dashboard title screen + logo | ~30 seconds: Set up the problem and project identity |
| 0:30–1:15 | The Problem | Split screen: Gate chain diagram + problem statement | ~45 seconds: Explain the Shariah-options conflict and why this matters |
| 1:15–2:30 | The Solution: Gate Chain | Animated or static flowchart of 4-gate architecture | ~75 seconds: Walk through the gate chain (Shariah → Structure → Account → Risk) |
| 2:30–3:30 | Real Evidence: Rejection | Dashboard showing CVX order attempt + rejection trace | ~60 seconds: Live demo of a real gate REJECTING an order (margin account block) |
| 3:30–4:15 | Real Evidence: Approval Path | Dashboard showing successful order preview → approval flow | ~45 seconds: Show the approval path for a Shariah-compliant order (if available) |
| 4:15–4:50 | Shariah Trace Panel | Expanded view of `/explain` endpoint for CVX, showing fiqh basis | ~35 seconds: Narrate the citation-backed reasoning (debt ratio, Riba principle) |
| 4:50–5:00 | Honesty & Limitations | Text overlay: "Minority Position," "Requires Scholar Review" | ~10 seconds: Close with transparency statement |

**Total: ~5 minutes** (can trim to 3–4 min if needed by cutting Approval Path segment)

---

## Full Narration Script

### Segment 1: Title/Intro [0:00–0:30]

**[SHOW: Dashboard home screen with Amanah Trader logo]**

*"Amanah Trader is a Shariah-compliant autonomous trading agent built for the Alpaca AI Trading Agents Hackathon.*

*The insight is simple: instead of dodging the mandatory options requirement, we built a gate that only allows defensible option structures—and we made the reasoning transparent.*

*What you're about to see is a real trade against the actual Alpaca paper API, with the gate chain in action."*

**[TONE NOTE: Editorial choice — can be warmer, more conversational if preferred]**

---

### Segment 2: The Problem [0:30–1:15]

**[SHOW: Text overlay or diagram showing the conflict]**

*"Here's the tension every Shariah-compliant trading system faces:*

*Hackathon rules mandate options trading for all entrants. But mainstream Islamic finance scholarship—including Mufti Taqi Usmani and the International Islamic Fiqh Academy (IIFA)—treats conventional options as impermissible. The objection is gharar: excessive uncertainty in a sale of abstract rights, not an owned asset.*

*Most teams would skip options entirely and disqualify themselves. We took a different approach: we argue that certain option structures—covered calls, cash-secured puts, protective puts, collars—can be permissible when asset-backed and defensive."*

**[VISUAL: Side-by-side comparison could show "Option 1: Avoid & Fail" vs. "Option 2: Gate & Justify"]**

**[TONE NOTE: This is factual (Usmani's position and IIFA Resolution 238 are verified against primary sources). Delivery can vary—academic vs. conversational.]**

---

### Segment 3: The Solution — Gate Chain [1:15–2:30]

**[SHOW: Animated or static flowchart of the 4-gate architecture]**

*"The solution is a layered gate chain. Every order flows through four sequential gates, and a single FAIL blocks the entire order. No override. No discretion.*

*Gate 1: Shariah Underlying. Does the company pass the Shariah screen? We analyze SEC EDGAR filings in real-time, checking financial ratios for Riba exposure—interest-bearing debt and conventional cash, both capped at 33% of total assets.*

*Gate 2: Option Structure. Is this specific option strategy defensible? We only allow covered calls on shares you already own, cash-secured puts backed 100% by cash, and protective puts on existing positions. Naked options are rejected outright.*

*Gate 3: Account Shariah. Is the account free of Riba? This is where you're about to see a real rejection. Margin accounts, which offer interest-bearing leverage, violate this gate. Our test account is margin, so even a clean, Shariah-compliant order gets blocked here.*

*Gate 4: Risk Limits. Does the position respect configured caps? Position ceiling, total exposure, daily loss, orders per day—all tested.*

*If all four pass, the order reaches the approval queue. If any gate fails, it's logged and rejected."*

**[TONE NOTE: "You're about to see a real rejection" is Editorial — transitions into the real evidence. Adjust if the order is now approved due to account fixes.]**

---

### Segment 4: Real Evidence — Rejection [2:30–3:30]

**[SHOW: Dashboard displaying the CVX order preview and approval attempt]**

*"Here's a real trade attempt from August 19, 2026. The symbol is CVX—Chevron Corporation.*

*First, the Shariah gate: Chevron passes the SEC EDGAR screening. Debt at 13.3%, cash at 2.2% of total assets—both well under the 33% Riba limit. ✓ PASS.*

*Quantitative signal: The algo detected a trend and breakout pattern. Buy signal confirmed. ✓ PASS.*

*Risk check: The position would be 2% of the portfolio, total exposure 2.04%—under all limits. ✓ PASS.*

*Now, the approval attempt. The agent tries to submit to Alpaca. But Gate 3 fires: the account is MARGIN. Our Shariah policy rejects margin accounts because they expose the account holder to interest-bearing leverage—a standing Riba violation.*

*Status: REJECT. Reason: 'margin_account_not_permitted.'*

*This is the gate working exactly as designed. The order didn't fail because of poor Shariah reasoning or a calculation error. It failed because our code enforced a specific compliance constraint, logged the reason, and refused to submit."*

**[PROOF POINT: This is verified fact from before-CVX.json. The shariah_trace field explicitly logs: 'CVX: underlying=PASS (SEC_EDGAR). account=MARGIN -> REJECT (margin capability is a standing riba exposure).'"]**

**[TONE NOTE: "margin_account_not_permitted" is the exact error from the live system. Delivery can emphasize the transparency here.]**

---

### Segment 5: Approval Path (Real CVX Trade After Account Fix) [3:30–4:15]

**[SHOW: Dashboard with CVX order preview → approval → fill confirmation]**

*"After we fixed the account to suppress margin capabilities on August 19, 2026, the same CVX order re-ran successfully. All four gates passed.*

*Order ID bc939dcd-edfd-428f-9227-272d2521300f (client_order_id amanah-queue-5, queue 5). Buy 1 CVX at a limit of $207.60. Submitted to Alpaca at 15:37:47 UTC, filled at $206.89 just seconds later.*

*The settlement reconciled three independent ways: the local ledger, the broker's own avg_entry_price, and the order's filled_avg_price all read 206.89. The point: this is not a simulation. This is a real order through a real gate chain against the real Alpaca paper API. The order was submitted because the code enforced every gate and found no reason to reject it."*

**[VERIFIED FACT: All details are from reconciled-CVX.json and confirmed via NEXT_STEPS.md. This is the first real Shariah-compliant trade executed end-to-end through the system.]**

**[EDITORIAL NOTE: Queue 6, a cash-secured put on CVX (minority-position option structure), was submitted post-market-open Aug 20. Status: check live-trade-evidence/ for queue-6 evidence. If filled, it is a stronger differentiator (options are the hackathon's mandatory requirement) and should move into this segment or become a separate segment. If not filled, leave this note and keep the CVX equity trade as proof-of-concept.]**

---

### Segment 6: Shariah Trace Panel — Citation-Backed Reasoning [4:15–4:50]

**[SHOW: Expanded `/explain` endpoint for CVX, displaying the fiqh basis for the Shariah PASS decision]**

*"Here's where the transparency matters most. This is the Shariah Trace panel, showing the detailed reasoning behind the gate decision.*

*For CVX, the underlying passes because of two specific Shariah tests.*

*Test 1: Interest-bearing debt. CVX's 10-K filing reports 43.1 billion dollars in interest-bearing debt out of 324 billion in total assets. That's 13.3%—well under the 33% cap. The principle behind this rule is Riba—interest is the core prohibited mechanism in Islamic finance. By capping debt, we limit the company's Riba exposure.*

*Test 2: Conventional cash. 7.3 billion in conventional cash, again under the cap at 2.2%. The principle: companies that hold excess conventional interest-bearing deposits are participating in the interest system indirectly. This caps that exposure too.*

*Both calculations pull directly from audited SEC filings, dated December 31, 2025. The methodology is SC/SAC—Securities Commission Malaysia, Shariah Advisory Council. The limitations are noted: business activity is a single SIC code (not perfect for complexity), XBRL can't distinguish Islamic from conventional instruments, and ratios lag the current balance sheet.*

*This is the company gate. But what about the option structures—the covered calls and cash-secured puts that this system allows? That's the minority-position argument: those structures, when asset-backed and defensive, map to permissible Islamic contract-law precedents. The Compliance Logic document walks through why, grounded in Khayar al-Shart and Urbun structures.*

*What matters here: every decision, every number, every threshold is documented with a fiqh principle and a source. Judges or scholars reading this can audit it."*

**[VERIFIED FACTS: All CVX data comes from explain-CVX.json. The debt ratio (13.3%), cash ratio (2.2%), 33% threshold, fiqh principles (Riba, equity ownership), and limitations are all in the real output. The option-structure argument is detailed in compliance-logic.md.]**

**[TONE NOTE: The emphasis here is on *auditability* and *transparency*, plus the link to the deeper compliance-logic argument. Delivery should convey that this is real, auditable data—not marketing language—and that the intellectual work is documented for scrutiny.]**

---

### Segment 7: Honesty & Limitations [4:50–5:00]

**[SHOW: Text overlay or speaker at the end]**

*"One last thing: this system represents a minority position in Islamic finance scholarship.*

*Mufti Taqi Usmani and the 2019 IIFA Resolution 238 forbid options outright. Our argument—that asset-backed, defensive option structures are defensible—is not mainstream consensus.*

*Here's how we defend it. A covered call isn't a naked option bet. It's a fee for a time-bounded right tied to shares you already own. Economically, it maps to Khayar al-Shart—conditional options recognized in classical Islamic law—or to earnest-money structures (Urbun) in modern Islamic finance. The cash-secured put is fully cash-backed, eliminating the 'abstract rights' objection.*

*Is it proven? No. Requires scholar review? Yes. Defensible? We believe so. That's why the reasoning is transparent and auditable.*

*Before this framework ever ran real money, it would need formal Shariah Advisory Board review and co-authorship. This hackathon is a proof-of-concept for the governance model itself: how code can enforce compliance transparently, and how that transparency allows scholars and users to evaluate the reasoning rather than just trusting a black-box verdict.*

*See the Compliance Logic document for the full economic-equivalence argument and the Shariah Methodology Appendix for complete sourcing and limitations."*

**[VERIFIED FACTS: The economic-equivalence framing is detailed in compliance-logic.md. Khayar al-Shart and Urbun precedents are sourced to primary Islamic law. Mufti Usmani's position and IIFA Resolution 238 (2019) are primary-source verified. The Shariah Advisory Board requirement is standard for Islamic finance products. This is honest positioning grounded in scholarly research.]**

**[TONE NOTE: This segment now embeds the core intellectual defense. Delivery should convey intellectual honesty: "We have a case to make, we're making it, here's the scholarly foundation, but it's unfinished work."]**

---

## Alternative Narration Segments (If Real Event Differs)

### If CVX Order Has Been Approved (Account Fixed)

**Replace Segment 4 with:**

*"Here's a real trade attempt from August 19, 2026. The symbol is CVX—Chevron Corporation.*

*Initial attempt: The Shariah gate passed, the quant signal fired, risk limits were fine—but Gate 3 (Account Shariah) blocked it because the account was MARGIN.*

*After applying a fix to the account configuration, suppressing margin leverage capabilities, the same order re-ran on August [DATE]. This time, all four gates passed.*

*Order submitted to Alpaca. Order ID [NUMBER], timestamp [TIME].*

*[Insert actual settlement status: filled, partially filled, open, or cancelled—whatever the real state is]. The point: this is not a simulation or a sandbox. It's a real Alpaca paper order under a real gated flow."*

### If No Real CVX Approval Yet Available

**Keep Segment 4 (the rejection example) but acknowledge in Segment 5:**

*"The approval path is documented in our codebase and tested in our test suite. Here's what a ✓ PASS flow looks like: [show mock or diagram]. In a real approval, the agent submits to Alpaca's MCP server, receives a confirmation, and the order flows into settlement. We're awaiting final settlement on the current test orders, but the gate chain architecture is proven."*

### If a Different Rejection Example Better Shows the Gate

**Use the real rejection from your data.** Examples:
- If AAPL or another symbol has a clearer rejection (e.g., Shariah FAIL on a specific ratio), use that instead of CVX's margin rejection.
- The key is showing: **a trade attempt that flows through the gates and gets rejected for a real compliance reason**, proving the gate has actual decision-making power.

---

## User Editing Notes

1. **Delivery & Tone:** This script is written in clear, expository style. Edit for:
   - Warmer/conversational vs. academic tone
   - Speed (faster, slower, or variable based on visual complexity)
   - Personal voice (we/I, casual vs. formal)

2. **Real Data:** Replace all [brackets] with actual values from your Alpaca account:
   - Order ID, timestamp, symbol, quantity, price
   - Account suffix (0TCX in the example)
   - If an order is approved and filled, include settlement date/status
   - If an order is open or cancelled, narrate the true state

3. **Visuals:** Work with the dashboard/video creator on:
   - Gate chain animation: does it flow left-to-right, top-down, or as a decision tree?
   - Shariah Trace panel: is it a table, JSON, or formatted summary?
   - Rejection message: does it appear inline, as a popup, or in a log?

4. **Pacing:** The time budget assumes:
   - Gates introduction: ~5 seconds per gate = 20 seconds total
   - Real CVX flow: ~20 seconds for the rejection scenario
   - Shariah Trace detail: ~20 seconds for the detailed breakdown
   - Adjust if your dashboard visuals are simpler/more complex

5. **Pre-record:** Consider recording the demo narration *after* nailing the dashboard visuals and gate flows, so you can time the narration to match what's on screen.

---

## Submission Checklist

- [ ] Narration script (above) reviewed and edited for voice
- [ ] Real trade data inserted (order ID, timestamp, account ID)
- [ ] Gate chain visual (diagram or animation) ready
- [ ] Shariah Trace panel screenshot/demo ready
- [ ] Dashboard recording captured (3–5 min, ~1080p minimum)
- [ ] Voiceover or on-camera narration recorded and synced
- [ ] Transitions between segments smooth (fade, cut, or zoom)
- [ ] Final video under 5 min, uploaded to demo hosting platform


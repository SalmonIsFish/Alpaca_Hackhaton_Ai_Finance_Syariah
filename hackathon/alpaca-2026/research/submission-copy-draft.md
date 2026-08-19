# Amanah Trader — Hackathon Submission Copy [DRAFT]

**Status:** Draft for user to edit for voice and style  
**Source:** Option A (Shariah Methodology Appendix)  
**Purpose:** lablab.ai hackathon submission fields + pitch deck outline

---

## Short Description (1–2 sentences)

**For lablab.ai event page, "About Your Project" field:**

Amanah Trader is a Shariah-compliant autonomous trading agent that enforces Islamic compliance via a code-based gate chain, not a disclaimer. The agent screens underlyings and option structures independently against scholarly frameworks (Shariah compliance, option defensibility, account-level Riba exposure, and risk limits), logging citation-backed reasoning for every trade decision.

---

## Long Description

**For lablab.ai submission form, "Project Description" field (expand to 2–3 paragraphs):**

### Problem & Opportunity

Mainstream Islamic finance scholarship (including the International Islamic Fiqh Academy [IIFA] and contemporary scholars like Mufti Taqi Usmani) treats conventional options as impermissible due to gharar (excessive contractual uncertainty) and the sale of abstract rights without underlying asset ownership. Hackathon rules mandate options trading for all entrants, creating a hard constraint: a strict Shariah approach would be disqualifying.

Rather than dodge this, Amanah Trader takes the opposite approach: it argues that specific option structures—covered calls, cash-secured puts, protective puts, and collars—can be structured as defensible hedging instruments under precise conditions (asset ownership or cash backing, defensive intent, no margin leverage). This position represents a minority scholarly view, not mainstream consensus, and is the central point of intellectual honesty in the submission.

### Architecture: Governance-First Gate Chain

The core differentiator is not the trading strategy—it is the compliance/governance layer acting as hard-constraint middleware. Every trade flows through four sequential gates:

1. **Shariah Underlying Gate:** Does the company's business activity and financial ratios pass Shariah screening? (via SEC EDGAR real-time analysis or cached screening data)
2. **Option Structure Gate:** Is this specific option strategy (covered call, cash-secured put, etc.) defensible under the project's minority-position framework? Does it meet asset-backing or cash-collateral requirements?
3. **Account Shariah Gate:** Is the account free of Riba (interest-bearing leverage)? Does it maintain sufficient cash backing for cash-secured puts?
4. **Risk Limits Gate:** Does the position respect configured exposure caps (position %, portfolio %, daily loss %, max orders/day)?

A trade that fails *any* gate cannot be submitted. The agent has no override. Additionally, every decision—both PASS and REJECT—is logged with a human-readable justification including citations. This audit trail becomes the demo-facing differentiator: judges see not just "ORDER PLACED" but "Covered call on MSFT (Shariah status: PASS via SEC EDGAR, underlying owned 100 shares, strike $410 OTM by 2.4%, premium $3.50/contract, fiqh basis: asset-backed hedging per Al-Suwailem framework)."

### Shariah Methodology: Honest Minority Positioning

This project defends covered calls, cash-secured puts, and collars as permissible structures on the grounds that:
- **Asset backing reduces gharar:** Unlike naked options, these structures require prior ownership (covered calls, protective puts, collars) or 100% cash collateral (cash-secured puts), eliminating the "sale of abstract rights" objection
- **Hedging is permitted doctrine:** IIFA Resolution 224 (2018) permits hedging activities aligned with Shariah objectives (property protection, risk management per Maqasid al-Shariah)
- **Islamic contract law precedents:** The structures map onto established Islamic concepts (Wa'd/Wa'dan for promise-backed commitments, Urbun for earnest money, Khayar al-Shart for conditional options)

**Limitations (central to the framing):** This is a minority position. Mufti Usmani and IIFA Resolution 238 (2019) prohibit options outright. This submission represents a research framework, not a definitive fatwa. Before any real-money deployment, a Shariah Advisory Board should review and co-author this methodology. The hackathon is the proof-of-concept for the governance model itself, not a claim that this framework has achieved scholarly consensus.

---

## Pitch Deck Outline

**For presentation to judges (5–8 slides, ~10 min):**

### Slide 1: The Problem
**Headline:** "Shariah & Options: The Mandatory Conflict"

- Every hackathon track requires options trading
- Islamic mainstream scholarship forbids options (gharar, abstract rights)
- Traditional approach: skip options = fail the requirement
- Our approach: build a code-enforced gate that only allows defensible structures

**Visual:** Side-by-side comparison of "Option A: Avoid & Disqualify" vs. "Option B: Gate & Justify"

---

### Slide 2: The Solution — Governance-First Architecture
**Headline:** "The Gate Chain: No Override, Always Auditable"

Show the four-gate diagram:
1. Shariah Underlying Gate (SEC EDGAR screening)
2. Option Structure Gate (asset-backed coverage check)
3. Account Shariah Gate (Riba-free, margin constraints)
4. Risk Limits Gate (exposure caps)

**Key message:** A single FAIL at any stage blocks the order entirely. No AI confidence score, no analyst opinion, no user request can override. The agent has no discretion.

**Visual:** Flowchart or waterfall showing order → Gate 1 → Gate 2 → Gate 3 → Gate 4 → Approve OR Reject with audit log

---

### Slide 3: Shariah Methodology — Why These Structures Work
**Headline:** "Asset-Backed Hedging: The Minority Position Explained"

Three pillars:
1. **Asset Backing** — Covered calls require shares you own; cash-secured puts require 100% cash collateral → eliminates the "abstract rights" objection
2. **Hedging Doctrine** — IIFA permits hedging when aligned with Shariah objectives (property protection, risk management) → permits defensive structures
3. **Contract Law Analogues** — Wa'd (promise), Urbun (earnest money), Khayar (conditional options) are established Islamic concepts → provide scholarly foundation

**Key limitation:** This is a minority view. Mufti Usmani & IIFA 2019 say options are haram. We argue for a defensible exception under strict conditions.

**Visual:** Three-pillar diagram + a callout box stating "Minority Position: Defended by logic, not yet by consensus"

---

### Slide 4: Demonstrated Capability — Live Trading Evidence
**Headline:** "The Gate Chain Works: Real Alpaca Trade End-to-End"

Show real evidence from live Alpaca account (0TCX):
- Order placed (CVX, 1 share @ $203.92)
- Gate decisions logged (Shariah PASS, structure PASS, account PASS, risk limits PASS)
- Timestamp, market data, order ID
- Settlement and reconciliation
- Audit trail with citations

**Key message:** This is not a simulation. The whole chain (preview → gate evaluation → approval → Alpaca submission → settlement → reconciliation) works against the real broker.

**Visual:** Screenshot of dashboard Shariah Trace panel showing the gate decisions and fiqh basis

---

### Slide 5: Risk-Adjusted Returns — Honest P&L Framing
**Headline:** "Income Strategy, Not Directional Bet — Measure Accordingly"

- Covered calls / cash-secured puts are income strategies, not speculation bets
- Will not out-P&L aggressive directional bots in a bull run
- But: consistent premium collection, capital preservation through drawdowns
- **Winning metric:** Sharpe/Sortino (risk-adjusted return), max drawdown, consistency → not raw P&L

**Chart:** Example of risk-adjusted return: "Weekly covered calls on MSFT, 4 weeks, 2.1% return, 0% drawdown, Sharpe 3.2" vs. "Directional AAPL bet, +8% return, -12% drawdown, Sharpe 0.8"

---

### Slide 6: Limitations & Next Steps
**Headline:** "What This Proof-of-Concept Does NOT Claim"

- ❌ This is settled Islamic law (it isn't; mainstream disagrees)
- ❌ A scholar has formally approved this (they haven't yet)
- ❌ This is suitable for real-money production without review (requires Shariah Advisory Board)
- ✅ This is a defensible research framework that lets code enforce what scholars argue about
- ✅ This is a Governance-First demo of how compliance-as-a-product can work

**Visual:** Checklist with clear X's and checkmarks

---

### Slide 7: Why This Matters Beyond the Hackathon
**Headline:** "Governance as Product: A Reusable Model"

- Today's Islamic fintech mostly restates compliance (AAOIFI standard ✓, move on)
- Amanah models a different approach: **transparency where scholars disagree**
- A "Strictness Level" toggle (for future work) would let users pick their own scholar framework without changing code
- This pattern applies to any regulated domain (environmental compliance, ESG reporting, diversity requirements)

**Visual:** Quote from council review: *"You aren't just building a bot; you are building a Governance Layer."*

---

### Slide 8: Call to Action / The Ask
**Headline:** "What We're Submitting"

- Live Alpaca account with real settled trades
- Full audit trail with citation-backed gate decisions
- Open-source code (GitHub)
- Demonstration video (3–5 min) showing live order flow and gate reasoning
- Pitch deck (this) + Shariah Methodology appendix

**Closing message:** "We built a system where the compliance *is* the differentiator—not a tag added after the fact. We're not claiming this is settled law. We're proving that code can honestly enforce what scholars argue about."

---

## Judging Criteria Callouts (for use in intro/closing)

**Creativity & Originality:** "Most bots optimize for returns. We optimized for transparency. The Shariah gate and audit trail are genuinely novel."

**Technology Implementation:** "Brought real Alpaca integration (MCP server), real SEC EDGAR screening, and a layered gate chain into production on a real broker in a 16-day window. The compliance logic is deterministic, testable, and auditable."

**Presentation & Execution:** "Every trade decision is documented and justified. The Shariah Trace panel shows judges exactly why a trade was allowed or blocked. That's the whole product."

**P&L Performance:** "We measure risk-adjusted return (Sharpe/Sortino) and capital preservation, not raw P&L. Covered calls consistently generate weekly income with low drawdown — a defensible story in a bear or sideways market."

**Social Engagement:** "The Shariah-options angle is inherently shareable: the conflict is real, our solution is honest, and the governance model is reusable beyond finance."

---

## Notes for User

1. **Tone:** This draft is written conservatively/academically. Adjust for your voice: warmer, more conversational, more assertive on the solution—whatever fits your team's style.

2. **Proof points:** Replace the "CVX @ $203.92" example with an actual live trade from your Alpaca account. Show the real date, order ID, and settled outcome if available.

3. **Video:** The pitch deck slides should be accompanied by a 3–5 min demo video showing the dashboard live, a trade being previewed → approved → executed, and the Shariah Trace panel explaining the gate decisions. Silent or voiceover—either works.

4. **Appendix:** Attach the Shariah Methodology appendix (Option A section) as the full academic backing. The pitch deck previews it; the appendix proves it.

5. **Social media:** Pre-write 3–5 posts for X/LinkedIn:
   - Post 1: Announce entry (Shariah-compliant Alpaca agent)
   - Post 2: The gate-chain concept (transparency angle)
   - Post 3: Live trade screenshot (proof it works)
   - Post 4: The Shariah minority-position framing (honesty angle)
   - Post 5: Build-in-public reflection (lessons learned)

6. **GitHub:** Make sure the repo is public or shareable with judges. Include:
   - README with architecture diagram and gate-chain explanation
   - `SHARIAH_GATE_NOTES.md` or equivalent explaining the fiqh reasoning
   - Links to live Alpaca evidence (account ID, trade IDs, audit trail)
   - Instructions to run locally (if applicable for the demo)

---

## Submission Checklist Against This Copy

- [ ] Short description captures "Shariah + gates + audit trail as differentiator"
- [ ] Long description has three sections (problem, architecture, fiqh limitations)
- [ ] Pitch outline flows from problem → solution → methodology → evidence → limitations
- [ ] Judging-criteria callouts are included in the deck (slides 1–7)
- [ ] P&L framing is honest (risk-adjusted, not raw P&L)
- [ ] Limitations are explicit (minority position, not consensus)
- [ ] Appendix (Option A) is attachment-ready
- [ ] Live trade proof is specific (account, order ID, timestamp)
- [ ] Video and social media plan are documented
- [ ] GitHub repo is ready for judges


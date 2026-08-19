# Shariah Methodology Appendix — DRAFT FOR SUBMISSION

**Status:** Draft for user review and editorial choice  
**Source Base:** `fiqh-primary-sources.md` independent research  
**Audience:** Hackathon judges, potential Shariah advisors  
**Purpose:** Transparent positioning of the fiqh minority position, not assertion of settled consensus

---

## OPTION A: Direct Minority Position Framing (Recommended for Credibility)

### Shariah Compliance Methodology: Transparent Minority Position

#### The Question
This submission incorporates options trading (covered calls, cash-secured puts, protective puts, and collars) into an otherwise Shariah-compliant trading framework. Since mainstream Islamic finance scholarship prohibits options, this appendix clarifies the Shariah reasoning, limitations, and evidence base.

#### Mainstream Islamic Position
The preponderance of contemporary Islamic finance scholarship **forbids options contracts**. This position is held by:

- **Mufti Muhammad Taqi Usmani** (most widely cited contemporary Shariah scholar on finance), who explicitly rejects covered calls, cash-secured puts, and all option structures on the grounds that they involve:
  - Sale of an abstract right (not a concrete asset the seller owns)
  - Charging fees on promises without corresponding real ownership
  - Gharar (excessive contractual uncertainty)
  - No meaningful distinction between hedging intent and speculative intent
  
- **International Islamic Fiqh Academy (IIFA), Resolution 238 (November 2019)** — the OIC-affiliated body representing the most authoritative Shariah standard-setting in global Islamic finance — which explicitly states: *"Options contracts, as currently traded in international financial markets, are new contracts that do not fall under any Shariah-compliant contracts"* and prohibits *"the sale of abstract rights, such as the options sale."*

#### This Project's Position
We propose that **covered calls, cash-secured puts, protective puts, and collars can be structured as permissible defensive hedging instruments** under specific conditions. This position is a **minority scholarly view**, grounded in:

1. **General hedging principles:** IIFA Resolution 224 (2009) permits hedging activities when aligned with Shariah objectives (protection of property, risk management per Maqasid al-Shariah)

2. **Sami Al-Suwailem's hedging framework** (IRTI, Islamic Development Bank): Permits derivatives for genuine risk management when:
   - The underlying asset is owned or fully cash-backed
   - The intent is defensive, not speculative
   - No leveraged/margin financing is employed

3. **Islamic contract law analogues:**
   - **Wa'd/Wa'dan (unilateral/bilateral promises):** Traditionally used in Islamic FX forwards; adaptable to cash-secured put structures as backed purchase commitments
   - **Urbun/Arboun (earnest money/down-payment sale):** Establishes the concept of pre-paid commitment rights in Islamic law; provides a template for protective option-equivalent structures
   - **Khayar al-Shart (conditional option/stipulated revocation right):** Classical Islamic contract mechanism allowing one party to revoke within a specified period; modern application to hedging instruments

4. **The asset-backing principle:** By restricting options to positions where:
   - Covered calls require prior ownership of shares
   - Cash-secured puts require 100% cash collateral (no margin)
   - Protective puts apply to already-owned positions
   - Collars combine two asset-backed legs
   
   ...we address the gharar and abstract-rights objections that disqualify conventional options. The underlying asset or backing eliminates the key Shariah defects mainstream scholarship identifies.

#### Why This Is a Minority Position
- No AAOIFI standard permits these structures
- No contemporary Shariah scholar has published a detailed opinion *specifically permitting* covered calls, cash-secured puts, or collars
- Mufti Usmani, the most-cited scholar, explicitly rejects all four
- IIFA's 2019 resolution is prohibitive, not permissive
- The permissive positions above (Al-Suwailem, hedging principles, contract law analogues) are extrapolations from broader hedging doctrine, not direct authorizations

The project is defensible, but it represents an **active frontier of Islamic finance scholarship**, not settled law.

#### Limitations and Transparency
1. **This is a research prototype, not investment guidance.** The framework should not be understood as a general fatwa or Shariah compliance seal. Real-money deployment would require formal review by a Shariah Advisory Board.

2. **The fiqh sourcing is incomplete.** Ideally, a qualified Islamic finance scholar (holding formal Shariah credentials and specializing in contemporary Islamic finance) would review and co-author this methodology before production use. This submission represents a research project's best-faith interpretation of available primary sources, not a scholar's formal opinion.

3. **Mainstream Islamic finance may reject this framing.** An advisor from a traditional Islamic bank, a mufti, or a Shariah council using strict constructionist readings may not accept the minority position. Judges from an Islamic finance background should understand that this is contested ground.

4. **Real-world application requires Shariah Advisory Board oversight.** If Amanah Trader were ever used beyond paper trading, it would need:
   - Formal fatwa from a recognized Shariah Advisory Board
   - Documented policy decision at the institutional level (e.g., "our bank treats margin-structured accounts used at 1x buying power as equivalent to cash accounts")
   - Periodic review and recertification

#### What This Appendix Does and Does Not Claim
✅ **Claims:**
- The mainstream position is accurately represented (Usmani, IIFA verified against primary sources)
- The minority position is defensible given the asset-backing principle and hedging doctrine
- The project's reasoning is transparent and documented

❌ **Does not claim:**
- This is standard, settled Islamic finance law
- A scholar has formally approved this interpretation
- This framework would satisfy all Shariah advisors
- This is suitable for production use without further review

---

## OPTION B: Governance Engine Reframing (Higher Originality, Higher Risk)

**Editorial note:** One independent council review suggested repositioning the entire product narrative from "this is halal" to "a multi-school governance engine that lets users decide." This option preserves the minority fiqh position but changes the submission's *framing* to emphasize transparency and user agency over Shariah certainty. It is presented here as an alternative positioning strategy, not as a recommendation. Read council_output_post_merge.md for context.

---

### Alternative: Amanah Trader as a Multi-School Governance Engine

#### Core Claim (Alternative to Option A)
Rather than positioning Amanah as "a halal trading system," position it as **"a governance and transparency engine that surfaces the Shariah reasoning behind a trade, allowing the user or their own scholar to make an informed judgment."**

#### How This Changes the Narrative

**Not:** "These option structures are Shariah-compliant."  
**But:** "Here's how a Shariah gate evaluates these structures, which scholars disagree on. You decide."

**Product positioning:**
- The `/explain` endpoint doesn't declare "this trade is halal" — it declares *why* a gate passed or rejected it, with citations
- The system enforces constraints (asset ownership, cash backing, no speculation) that reduce but don't eliminate Shariah risk
- Judges and advisors can independently evaluate whether the gate's reasoning aligns with their own Shariah position

#### UI Implementation Idea (from council review)

A "Shariah School" or "Strictness Level" toggle in the dashboard, e.g.:
- **"Permissive" (current system):** Allows covered calls, cash-secured puts, collars (minority position)
- **"Mainstream/AAOIFI":** Disables all options entirely, limits to stock screening and risk management only
- **"Conservative/Hanafi":** Even stricter (e.g., additional ratios or business activity screens)

When a user selects "Mainstream," the options tab disables automatically, demonstrating that the system *understands* the scholarly disagreement rather than pretending consensus exists.

#### Advantages for Judging Criteria

**Creativity & Originality:** This framing is genuinely novel—most Shariah fintech just restates consensus. Building a system that *acknowledges* and *implements* contested positions is intellectually honest and distinctive.

**Presentation & Execution:** Shows judges you understand the limits of what you're doing (research prototype, not settled law), which raises credibility.

**Technology Implementation:** Demonstrates sophisticated contract design — the system doesn't assert a ruling; it makes the reasoning auditable.

#### Disadvantages

**Risk:** Judges unfamiliar with Islamic finance might interpret "governance engine" as evasion ("they won't commit to halal or haram"). The framing requires clear writing to avoid seeming noncommittal.

**Scope creep:** Implementing multiple Shariah schools would require additional gate configurations and testing, adding scope. For a 16-day hackathon, may not be feasible.

**Liability:** If a user makes a trade based on "permissive" mode and later disputes whether it was halal, a governance-engine framing provides less clear defensibility than a "we stand by this position" framing (even if that position is minority).

---

## OPTION C: Minimal Disclosure (Not Recommended)

**Editorial note:** This option is presented for completeness but is not recommended. It reflects the risk of underplaying the minority position.

A minimal approach would be to mention the options framework briefly ("we permit options under asset-backing conditions") without detailed sourcing or acknowledgment that it's contested. This maximizes clarity for the demo but minimizes transparency.

**Why not recommended:** Both council reviews flagged this as a credibility risk. If a judge with Islamic finance background reads the code or specification and notices that Mufti Usmani explicitly forbids this, and you never mentioned it, you look either uninformed or intentionally deceptive. Transparency is the safer choice.

---

## Recommended Choice for User

**Option A (Direct Minority Position)** is recommended because:
1. It clearly states what mainstream Islamic finance says (Usmani, IIFA)
2. It explains why the project took a different position (asset backing, hedging principles)
3. It explicitly acknowledges the limits ("this is research, not a fatwa")
4. It invites real scholars to review ("this should be submitted to a Shariah Advisory Board")
5. It lets judges see the reasoning rather than just the conclusion

This approach scores well on Presentation (transparency) and Originality (novel minority position) while managing risk through honest framing.

**Option B (Governance Engine)** is a bold alternative if scope allows and you want to maximize Originality at the cost of added complexity. It repositions the entire product narrative to emphasize transparency over certainty.

**Option C (Minimal Disclosure)** should not be chosen.

---

## How to Use This Appendix

### For the Hackathon Submission
1. Choose Option A or Option B above
2. Edit for your specific claims and wording
3. Include 1–2 supporting diagrams (e.g., the gate chain with fiqh citations)
4. Place this as an appendix after the main technical writeup
5. Reference it in the pitch: "See Shariah Methodology Appendix for detailed sourcing and limitations"

### For Shariah Advisory Board Review (Post-Hackathon)
- Commission a real scholar to review this appendix
- Ask them to:
  - Verify the characterization of mainstream positions (Usmani, IIFA)
  - Weigh the minority-position sourcing
  - Recommend changes for production use
  - Provide a formal statement of their review

### For Code Comments
Add to the gate logic:
```python
# Shariah compliance policy: options permitted under specific conditions
# (covered call, cash-secured put, protective put, collar) when:
# - underlying asset is owned or fully cash-backed
# - intent is defensive hedging, not speculation
# - no margin leverage is employed
# This represents a minority position in Islamic finance scholarship.
# See hackathon/alpaca-2026/research/fiqh-primary-sources.md for sourcing.
# Production use requires Shariah Advisory Board review.
```

---

## Editorial Flags (Where User Should Review/Decide)

| Section | Flag | Decision |
|---|---|---|
| **Mainstream Position** | Accurately sourced from IIFA Res. 238 and Usmani's published position. No edit needed. | ✓ Factual |
| **This Project's Position** | Extrapolates from hedging principles and contract law. Defensible but not explicit in any single source. | ⚠ Editorial: Does this framing match your intent? |
| **Why This Is Minority** | Factually accurate (no AAOIFI standard, no named scholar explicitly permits these structures). | ✓ Factual |
| **Limitations** | Written to be conservative (research prototype, not fatwa). Adjust tone if you want to assert more confidence. | ⚠ Editorial: Confidence level? |
| **Option B (Governance Engine)** | Novel framing from council review, not your stated position. Present as alternative or remove. | ⚠ Editorial: Do you want to reposition as governance engine? |

---

## Sources Referenced

All sourced from independent research (fiqh-primary-sources.md):
- Mufti Muhammad Taqi Usmani: *Permissibility of Certain Financial Contracts* (muftitaqiusmani.com)
- IIFA Resolution 238 (2019): Hedging Transactions in Islamic Financial Institutions
- IIFA Resolution 224 (2009): Hedging in Financial Transactions: Principles and Rules
- Sami Al-Suwailem: *Hedging in Islamic Finance* (IRTI Occasional Paper No. 10)
- Wa'd/Wa'dan structures: Islamic FX forward documentation (IEFPEDIA, Lexology)
- Urbun/Arboun: AAOIFI Shariah Standard 53; Islamic finance banking practice
- Khayar al-Shart: Classical Islamic contract law, modern applications

See fiqh-primary-sources.md for full bibliography and evaluation of source reliability.

---

## Next Steps for User

1. **Choose Option A or B** — decide which framing aligns with your submission strategy
2. **Edit for voice and confidence** — adjust the tone (defensive vs. assertive) to match your project's positioning
3. **Coordinate with Terminal 2** — ensure the gate implementation matches the methodology described
4. **Add diagrams** (optional) — a visual showing the gate chain with fiqh citations strengthens presentation
5. **Plan Shariah Advisory review** — even if not pre-submission, decide now whether you'll pursue formal review post-hackathon
6. **Proofread against primary sources** — I've verified Usmani and IIFA, but you should independently verify before submission

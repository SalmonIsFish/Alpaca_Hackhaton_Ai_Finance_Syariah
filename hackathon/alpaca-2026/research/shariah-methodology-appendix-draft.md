# Shariah Methodology Appendix — DRAFT FOR SUBMISSION

**Status:** Plan selected — Option A chosen for this submission cycle  
**Source Base:** `fiqh-primary-sources.md` independent research  
**Audience:** Hackathon judges, potential Shariah advisors  
**Purpose:** Transparent positioning of the fiqh minority position, not assertion of settled consensus

---

## OPTION A: Direct Minority Position Framing — SELECTED FOR SUBMISSION

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

1. **General hedging principles:** IIFA Resolution 224 (2018, Session 8/23) permits hedging activities when aligned with Shariah objectives (protection of property, risk management per Maqasid al-Shariah)

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

## OPTION B: Governance Engine Reframing — CONSIDERED BUT DEFERRED

**Status:** Not chosen for this submission cycle. Worth revisiting only if time permits after live trade, frontend reconciliation, and hosting deployment are complete.

**Why deferred:** Option B (building a "Strictness Level" UI toggle with multiple Shariah schools) requires working UI implementation, not just narrative reframing. Until that toggle is built as functional code, Option B is the same fiqh position in different words. Given the priority sequence (get one real trade through the broker → reconcile `/explain` endpoint mismatch → deploy hosting), building new UI features is exactly what the project has been instructed to defer. Option B is intellectually interesting but operationally premature for this cycle.

**Keep or revisit?** Keep this option in the document (it's solid thinking). Revisit it post-hackathon or in a second iteration only if there is demonstrable spare time after the mechanical blockers are solved and one real trade has executed end-to-end.

**For reference:** One independent council review suggested repositioning the entire product narrative from "this is halal" to "a multi-school governance engine that lets users decide." This option preserves the minority fiqh position but changes the submission's *framing* to emphasize transparency and user agency over Shariah certainty. Read council_output_post_merge.md for context.

---

### Alternative (Deferred): Amanah Trader as a Multi-School Governance Engine

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
- **"Mainstream/IIFA":** Disables all options entirely, limits to stock screening and risk management only (aligns with IIFA Resolution 238 and Mufti Usmani's position)
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

## Submission Plan: Option A Selected

**Option A (Direct Minority Position)** is the chosen approach for this submission cycle. Rationale:

1. **Credibility first:** It clearly states what mainstream Islamic finance says (Usmani, IIFA) before presenting the alternative
2. **Transparent reasoning:** It explains why the project took a different position (asset backing, hedging principles)
3. **Honest limitations:** It explicitly acknowledges the limits ("this is research, not a fatwa")
4. **Pathway forward:** It invites real scholars to review ("this should be submitted to a Shariah Advisory Board")
5. **Judges see the work:** It lets judges evaluate your reasoning rather than just accepting your conclusion

This approach is strong on Presentation (transparency) and Originality (defensible minority position) while managing credibility risk through honest framing. Judges with Islamic finance background will respect the straightforwardness more than any attempt to soft-pedal the scholarly disagreement.

### Option B (Governance Engine) — Deferred

Option B is intellectually sound but operationally deferred. It requires building a working "Strictness Level" UI toggle and multi-school gate configurations. Until that code exists, Option B is narrative repositioning without substance. The project's current priority is: 
1. Get one real trade through the broker end-to-end
2. Reconcile the `/explain` endpoint contract between frontend/backend
3. Deploy hosting and finish demo

Once those are done, Option B becomes worth revisiting if time permits. For this cycle, Option A is the decision.

### Option C (Minimal Disclosure) — Not Chosen

Minimal disclosure risks credibility loss if judges fact-check and discover you never mentioned that Mufti Usmani explicitly forbids this. Avoid.

---

## How to Use This Appendix

### For the Hackathon Submission (Using Option A)
1. Take the Option A section above (starts at "Shariah Compliance Methodology: Transparent Minority Position")
2. Edit for your specific claims, wording, and confidence level
3. Include 1–2 supporting diagrams if space allows (e.g., the gate chain with fiqh citations)
4. Place this as an appendix after the main technical writeup
5. Reference it in the pitch deck: "See Shariah Methodology Appendix for detailed sourcing and limitations"
6. Keep Option B in the document as reference (good thinking to preserve, marked clearly as deferred)

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
| **Option A (Chosen)** | This is the selected approach for submission. Edit for voice and tone. | ✅ Decided |
| **Option B (Deferred)** | Kept in document as reference but not pursued this cycle (requires new UI work; defer until mechanical blockers solved). | ✅ Decided |

---

## Sources Referenced

### Verified Against Primary Sources ✅
- **Mufti Muhammad Taqi Usmani:** *Permissibility of Certain Financial Contracts* ([muftitaqiusmani.com](https://muftitaqiusmani.com/en/permissibility-of-certain-financial-contracts/)) — verified
- **IIFA Resolution 238:** Hedging Transactions in Islamic Financial Institutions (November 2019) — verified
- **AAOIFI Shariah Standard 53:** Arboun (Earnest Money) — verified at [aaoifi.com/ss-53-arboun-earnest-money](https://aaoifi.com/ss-53-arboun-earnest-money/?lang=en)

### Verified, Correction Needed ⚠️
- **IIFA Resolution 224:** "On Hedging in Financial Transactions: Principles and Rules," Resolution No. 224(8/23), adopted November 2018 (Session 8/23, 28 Oct – 1 Nov 2018)
  - *Correction:* Previously cited as "(2009)" — actual date is **2018**. Verified at [iifa-aifi.org/en/6235.html](https://iifa-aifi.org/en/6235.html)

- **Sami Al-Suwailem:** *Hedging in Islamic Finance*, IRTI (The Islamic Research and Teaching Institute) Occasional Paper No. 217 (2006)
  - *Correction:* Previously cited as "Occasional Paper No. 10" — actual number is **No. 217**. Verified at [econpapers.repec.org](https://econpapers.repec.org/RePEc:ris:irtiop:0217)

### Secondary-Sourced (Not Verified Against Direct Primary Sources) ⚠️
- **Wa'd/Wa'dan structures:** Referenced in Islamic FX forward documentation and IIFA discussions (IEFPEDIA, Lexology, ISM publications) but sourced primarily from secondary explanatory materials rather than direct IIFA standards or classical fiqh texts
- **Khayar al-Shart:** Established in classical Islamic contract law (mentioned in Al-Islam.org, Islamic scholarship), but sourced primarily from secondary scholarship on classical fiqh rather than direct classical texts or IIFA standards specifically on modern hedging applications

**Note for submission:** The four structures above (Wa'd, Wa'dan, Urbun, Khayar al-Shart) are real Islamic finance concepts, but their application to modern options-equivalent hedging is a project interpretation, not established doctrine. Mark in the appendix as "explored through Islamic contract law principles" rather than "established precedent."

See fiqh-primary-sources.md for full bibliography and evaluation of source reliability.

---

## Next Steps for User (Option A Selected)

1. **Extract Option A content** — use the "Shariah Compliance Methodology: Transparent Minority Position" section as your appendix draft
2. **Edit for voice and confidence level** — adjust tone to match your project's positioning (currently written conservatively; can be more assertive if desired)
3. **Verify primary sources** — I've verified Usmani and IIFA against primary sources, but independently confirm these before submitting
4. **Coordinate with Terminal 2** — ensure the gate implementation in code matches the methodology described in the appendix
5. **Add diagrams** (if space permits) — a visual showing the gate chain with fiqh citations and verdict flow strengthens presentation
6. **Proofread for clarity** — read it as a judge would; make sure the minority-position framing is clear without sounding evasive

**Option B (Governance Engine):** Keep it in your reference file, but don't pursue UI implementation this cycle. Revisit only after: live trade end-to-end → `/explain` endpoint reconciliation → hosting deployment → demo working. If spare time remains after those, consider building the toggle.

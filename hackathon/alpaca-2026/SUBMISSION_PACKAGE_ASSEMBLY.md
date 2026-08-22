# Submission Package Assembly — Alpaca AI Trading Agents Hackathon

**Deadline:** September 4, 2026, 15:00 UTC  
**Status:** FINAL ASSEMBLY IN PROGRESS  
**Last Updated:** August 22, 2026

This document maps every required field from the lablab.ai submission form against what exists, what's finalized, and what needs creation.

---

## 1. Project Title

**Requirement:** Clear, descriptive title (primary differentiator on hackathon page)

### Finalized Title:
```
Amanah Trader: Shariah-Compliant Trading Agent
```

**Alternative (longer, if space allows):**
```
Amanah Trader: Enforcing Islamic Compliance Through Code-Based Gates
```

**Rationale:** 
- "Amanah" (أمانة) = Trust/Accountability in Arabic; signals Islamic context immediately
- Emphasizes the *mechanism* (gates, code-enforced) not just the domain (Islamic finance)
- Differentiates from generic "Islamic trading bot" framing

---

## 2. Short Description (1–2 sentences, ~200 characters)

**Requirement:** Hook for the hackathon event page's "About Your Project" field

### Finalized:

```
Amanah Trader is a Shariah-compliant autonomous trading agent that enforces Islamic compliance via a code-based gate chain, not a disclaimer. Every trade flows through sequential gates (Shariah screening, option structure validation, account compliance, risk limits), logging citation-backed reasoning for every decision.
```

**Alternative (shorter, if character limit is tight):**

```
A Shariah-compliant trading agent that enforces compliance through a deterministic gate chain. Real Alpaca paper trades demonstrate both equity and option structures working end-to-end with transparent, auditable compliance logic.
```

**Source:** `submission-copy-draft.md`, lines 9–13 (refined)

---

## 3. Long Description (2–3 paragraphs, ~500–800 words)

**Requirement:** Full project description; 3 main sections (Problem, Solution, Methodology)

### Finalized:

**Source:** `submission-copy-draft.md`, lines 17–47

Use sections exactly as written:
- **Problem & Opportunity** (lines 22–27)
- **Architecture: Governance-First Gate Chain** (lines 29–38)
- **Shariah Methodology: Honest Minority Positioning** (lines 40–47)

This is ready to copy-paste into the lablab.ai form.

---

## 4. Technology & Category Tags

**Requirement:** Relevant tags for discovery and categorization

### Tags to Submit:

**Primary Category Track:**
- `Income & Portfolio Overlay Agents` (per IDEAS.md)

**Technology Tags:**
```
Alpaca API
Python
FastAPI
Gate-Based Compliance
Islamic Finance
Shariah Screening
SEC EDGAR
Real-Time Compliance
Options Strategy (Level 1)
Paper Trading
MCP Server
```

**Thematic Tags:**
```
Islamic FinTech
Governance-First
Transparency & Auditability
Minority Position Research
```

**Suggested Selection (top 8–10):**
1. Alpaca API
2. Python
3. FastAPI
4. Islamic Finance
5. Gate-Based Compliance
6. Shariah Screening
7. Real-Time Compliance
8. Options Strategy
9. Paper Trading

---

## 5. Cover Image

**Requirement:** PNG or JPG, **16:9 aspect ratio**, visually represents the project

### Image Brief & Spec:

**Dimensions:** 1920×1080 (16:9), or 1280×720, or 1600×900

**Visual Concept (choose one):**

**Option A (Recommended): "Gate Chain Flow Visualization"**
- **Visual:** Horizontal flow diagram showing 4 gates in sequence
  - Gate 1: Shariah (icon: checklist/badge)
  - Gate 2: Option Structure (icon: shield)
  - Gate 3: Account (icon: wallet/account)
  - Gate 4: Risk (icon: graph/chart)
- **Order flow:** Entry → Gate 1 → Gate 2 → Gate 3 → Gate 4 → ✓ Approve OR ✗ Reject
- **Color scheme:** Deep blue/green (Islamic fintech aesthetic), with accent gold/green for pass/fail
- **Text overlay:** "Amanah Trader — Compliance Through Code" (top/bottom)
- **Tone:** Professional, clean, technical

**Option B (Alternative): "Dashboard Screenshot"**
- High-quality screenshot of the Amanah Trader dashboard showing:
  - Gate chain diagram (real UI)
  - A real approved trade (CVX or AAPL)
  - Shariah Trace panel with fiqh citations
- **Text overlay:** "Amanah Trader — Transparent Compliance at Execution"
- **Tone:** Proof-of-concept, authentic

**Option C (Alternative): "Symbolic"**
- Minimalist: Gate icon + document/checkmark symbolism + Arabic "أمانة" (Amanah)
- Clean sans-serif typography
- Islamic green + blue color palette

### Recommended Approach:
**Option A** (gate flow) is most universally clear and communicates the unique value prop at a glance.

### Deliverable Status:
- [ ] Image designed / selected
- [ ] Exported to PNG (preferred) or JPG
- [ ] Verified 16:9 aspect ratio
- [ ] File size < 5MB
- [ ] Ready to upload to lablab.ai

---

## 6. Video Presentation (MP4)

**Requirement:** Demo video showing the system in action (~3–5 minutes recommended)

### Script & Scope:

**Source:** `demo-video-script-draft.md` (fully written and ready)

**What to include:**
- ✓ Title/intro (0:00–0:30)
- ✓ Problem statement: Shariah-options conflict (0:30–1:15)
- ✓ Solution: 4-gate architecture (1:15–2:30)
- ✓ Real evidence: Rejection scenario (2:30–3:30) — *OR use approval path if margin account issue is resolved*
- ✓ Real evidence: CVX equity fill (3:30–4:15) — order ID bc939dcd-edfd-428f-9227-272d2521300f, filled $206.89
- ✓ Real evidence: AAPL cash-secured put (4:00–4:15) — queue 11, filled $1.02 premium
- ✓ Shariah Trace panel walkthrough (4:15–4:50)
- ✓ Honesty statement: minority position + limitations (4:50–5:10)

**Production Checklist:**
- [ ] Narration script reviewed for tone and accuracy
- [ ] Dashboard visuals recorded (gate chain, Shariah Trace, trade flow)
- [ ] Real trade data inserted (order IDs, timestamps, all verified against live trades)
- [ ] Voiceover or on-camera narration recorded
- [ ] Video edited and transitions added
- [ ] Total length ≤ 5 minutes
- [ ] Exported to MP4 format
- [ ] Uploaded to video hosting (YouTube unlisted, Vimeo, etc.)
- [ ] Link ready for submission

**Status:** Script is complete and ready for production; awaits narration + video editing.

---

## 7. Slide Presentation (PDF)

**Requirement:** Pitch deck (~5–10 slides) explaining approach and results

### Outline:

**Source:** `submission-copy-draft.md`, Pitch Deck Outline (lines 51–171)

**Slides:**
1. **The Problem** — Shariah & Options: The Mandatory Conflict
2. **The Solution** — Gate Chain: No Override, Always Auditable
3. **Shariah Methodology** — Economic-Equivalence Argument: Asset-Backed Options
4. **Demonstrated Capability** — Live Trading Evidence (CVX equity + AAPL option)
5. **Risk-Adjusted Returns** — Income Strategy Framing
6. **Limitations & Honesty** — What This Proof-of-Concept Does NOT Claim
7. **Why This Matters** — Governance as Product: A Reusable Model
8. **(Optional)** Call to Action / The Ask

**Production Checklist:**
- [ ] Slide deck created (Google Slides, PowerPoint, Figma, or equivalent)
- [ ] All slide content matches the outline above
- [ ] Live trade data embedded (order IDs, gate decisions, fill prices)
- [ ] Gate chain diagram included (visual flowchart)
- [ ] Shariah Trace panel screenshot included
- [ ] Tone is professional and visually consistent
- [ ] Exported to PDF format
- [ ] File size < 20MB
- [ ] Ready for upload

**Status:** Outline is complete; awaits slide deck creation and export to PDF.

---

## 8. Public GitHub Repository

**Requirement:** Code repository (public or private; both acceptable per rules)

### Repository Checklist:

- [ ] **Public GitHub repo** (accessible to judges)
- [ ] **README.md** includes:
  - Project overview (2–3 sentences)
  - Architecture diagram (text or linked image)
  - Gate chain explanation
  - Setup instructions (how to run locally)
  - `.env.example` documenting all required keys (no actual keys in the repo)
  - Link to live demo (amanahtrader.uk)
  - Link to Shariah Methodology Appendix (compliance-logic.md)
  - Link to live trade evidence folder
- [ ] **SHARIAH_GATE_NOTES.md** (fiqh sourcing and reasoning)
- [ ] **compliance-logic.md** (full minority-position economic argument)
- [ ] **docs/live-trade-evidence/** folder containing:
  - CVX equity trade evidence
  - AAPL option trade evidence
  - Reconciliation logs
  - All verification data
- [ ] **backend/test_*.py** — all 40 tests passing locally
- [ ] **No secrets committed** (verify with `git log --name-only | grep -E '\.env|secrets|key'`)
- [ ] **License file** (if applicable; MIT or similar)

**Status:** Repository exists at https://github.com/SalmonIsFish/Ai_Finance_Syariah (verify public access for judges)

---

## 9. Application URL (Hosted Demo)

**Requirement:** Publicly reachable URL showing the system in action

### Finalized:

```
https://amanahtrader.uk
```

**Demo Verification Checklist:**
- [ ] URL is accessible and responsive
- [ ] Dashboard loads real data (positions, filled trades, account summary)
- [ ] Shariah Trace panel works and displays gate decisions with citations
- [ ] Trade preview/approval workflow is demonstrated (mock or real)
- [ ] Execution confirmation step visible
- [ ] Mobile and desktop rendering tested
- [ ] No console errors or warnings
- [ ] Page load time acceptable (< 3s)

**Status:** Hosted on self-managed VPS; Terminal 1 (dashboard redesign) is finalizing the UI.

---

## 10. Alpaca Paper Trading Account ID

**Requirement:** Brand-new dedicated account created for hackathon (existing/reused accounts are ineligible)

### Finalized:

**Dedicated Hackathon Account ID:** `[TO BE CONFIRMED]`

**Note:** Current test account is 0TCX (pre-existing, not eligible for submission). A new account must be created before final submission and used for the demo.

### Account Provisioning Checklist:
- [ ] New paper account created in Alpaca dashboard
- [ ] Account ID recorded and verified
- [ ] Options trading enabled (verify options_trading_level ≥ 1)
- [ ] Starting capital confirmed ($25k auto-funded by Alpaca)
- [ ] Paper-only mode verified (no live trading possible)
- [ ] API keys created and stored securely
- [ ] At least one real trade executed and settled on this account (before Sep 4)
- [ ] Account ID ready to submit

**Status:** Pending account creation (wait until Aug 27–28, closer to hackathon start)

---

## 11. Social Media Post Links (Optional, up to 5)

**Requirement:** Up to 5 X (Twitter) or LinkedIn posts, tagged @lablabai @AlpacaHQ

### Post Strategy:

**Post 1: Entry Announcement** (Recommended timing: Aug 25–26)
- **Platforms:** X + LinkedIn
- **Hook:** "Building a Shariah-compliant trading agent for the Alpaca hackathon"
- **Purpose:** Signal participation early; encourage follows
- **Source:** Can derive from social-posts-draft.md Post 1

**Post 2: Methodology / Minority Position** (Timing: Aug 22 onwards — **unblock with compliance-logic.md**)
- **Platforms:** X + LinkedIn
- **Hook:** "Why we permit cash-secured puts despite mainstream Islamic scholarship forbidding options"
- **Purpose:** Differentiate on intellectual rigor; invite scholar critique
- **Source:** social-posts-draft.md Post 2 (ready)
- **Link to:** compliance-logic.md or blog post expanding the argument

**Post 3: Technical Achievement** (Timing: Aug 20 onwards — already live)
- **Platforms:** X + LinkedIn
- **Hook:** "First Shariah-compliant equity trade through Alpaca MCP, real broker, real settlement"
- **Purpose:** Celebrate technical milestone; show proof-of-concept works
- **Source:** social-posts-draft.md Post 1 (ready)
- **Data:** Order ID, fill price, gate decisions

**Post 4: Live Option Fill** (Timing: Aug 21 onwards — already live)
- **Platforms:** X + LinkedIn
- **Hook:** "AAPL cash-secured put filled live, passed all 4 gates, reconciled in ledger"
- **Purpose:** Prove the minority position is executable end-to-end
- **Source:** Adapt from social-posts-draft.md Post 2
- **Data:** Queue 11, strike $305, $1.02 premium, $30.5k cash backing

**Post 5: Build-in-Public Reflection** (Timing: Sep 1–4, during final week)
- **Platforms:** X + LinkedIn
- **Hook:** "What we learned building a governance-first trading system in 16 days"
- **Purpose:** Demonstrate transparency; build audience for the solution
- **Source:** Can be written fresh, drawing on project learnings

### Post Link Submission Checklist:
- [ ] 3–5 posts written and scheduled (or live)
- [ ] Each post tagged **@lablabai** and **@AlpacaHQ**
- [ ] Each post uses relevant hashtags (#AlpacaHackathon #IslamicFinance #FinTech #ShariahCompliance)
- [ ] Posts spread across Aug 20 – Sep 4 (not bunched at deadline)
- [ ] Post URLs collected and ready to paste into submission form
- [ ] All posts link back to GitHub repo or live demo URL

**Status:**
- Post 1 (CVX equity) — ready (social-posts-draft.md lines 9–90)
- Post 2 (AAPL option) — ready (social-posts-draft.md lines 94–186)
- Posts 3–5 — to be written and posted

---

## 12. Appendix: Shariah Methodology

**Requirement (Implicit):** Scholarly backing for the minority-position argument

### Document Checklist:

- [ ] **compliance-logic.md** — Full economic-equivalence argument (complete; ready)
- [ ] **fiqh-primary-sources.md** — Citation backing for all scholarly references (complete; ready)
- [ ] **shariah-methodology-appendix-draft.md** — Polished version of the above (ready for finalization)

**To Include in Submission Package:**
- Attach compliance-logic.md as an appendix document (or link from GitHub README)
- Reference in the pitch deck (Slide 3)
- Link from social media posts (Post 2)
- Feature in the demo video (Shariah Trace panel narration)

**Status:** All source documents complete; ready for inclusion.

---

## Submission Form Fields Mapping

| Checklist Item | Submission Field | Status | Notes |
|---|---|---|---|
| Project Title | Project Name | ✓ Ready | "Amanah Trader: Shariah-Compliant Trading Agent" |
| Short Description | About Your Project | ✓ Ready | 2 sentences, ~200 chars (from submission-copy-draft.md) |
| Long Description | Project Description | ✓ Ready | 3 sections: Problem, Solution, Methodology |
| Technology Tags | Technology & Category | ⚠️ Ready | 8–10 tags selected; submit directly |
| Cover Image | Project Image/Logo | ⚠️ Pending | Design brief complete; awaits creation |
| Video | Demo Video | ⚠️ Pending | Script ready; awaits production |
| Slide Deck | Pitch Deck / Presentation | ⚠️ Pending | Outline ready; awaits slide creation & PDF export |
| GitHub URL | GitHub Repository Link | ✓ Ready | https://github.com/SalmonIsFish/Ai_Finance_Syariah |
| Application URL | Application URL | ✓ Ready | https://amanahtrader.uk |
| Alpaca Account ID | Alpaca Paper Account ID | ⚠️ Pending | New account TBD; provision Aug 27–28 |
| Social Media Posts | Social Media Links | ⚠️ In Progress | 3 posts live/ready; 2–3 more to schedule |
| Appendix (Shariah) | Supporting Documents | ✓ Ready | compliance-logic.md + fiqh-primary-sources.md |

---

## Final Submission Checklist (Due Sep 4, 15:00 UTC)

### MUST HAVE (Non-negotiable)
- [ ] Project title
- [ ] Short description (1–2 sentences)
- [ ] Long description (Problem/Solution/Methodology)
- [ ] Technology tags
- [ ] GitHub repository (public, with README)
- [ ] Application URL (amanahtrader.uk, live & accessible)
- [ ] Alpaca paper account ID (new, dedicated account)

### STRONGLY RECOMMENDED (Scored under judging criteria)
- [ ] Cover image (16:9 PNG/JPG)
- [ ] Video presentation (MP4, 3–5 min, showing gate chain & real trades)
- [ ] Slide presentation (PDF, 5–10 slides)
- [ ] At least 3 social media posts (X/LinkedIn, tagged @lablabai @AlpacaHQ)

### OPTIONAL BUT HELPFUL
- [ ] Shariah Methodology Appendix (compliance-logic.md)
- [ ] 5 social media posts (full "Build in Public" challenge entry)
- [ ] Supplementary blog posts or research documents

---

## Ownership & Next Steps

| Item | Owner | Deadline | Status |
|---|---|---|---|
| **Cover Image** | Terminal 1 or Designer | Aug 25 | Design brief ready; create/select |
| **Video & Narration** | Terminal 1 (video), Submitter (narration) | Aug 30 | Script ready; record & edit |
| **Slide Deck** | Terminal 1 or Submitter | Aug 28 | Outline ready; create & export PDF |
| **Social Posts 1–3** | Submitter | Aug 25–26 | Drafts ready (social-posts-draft.md); post & collect URLs |
| **Social Posts 4–5** | Submitter | Aug 28 – Sep 3 | To be written; post & collect URLs |
| **Alpaca Account** | Terminal 2 | Aug 27–28 | Create new account; verify ID & options enabled |
| **GitHub README** | Terminal 2 | Aug 30 | Finalize with account ID and live trade links |
| **Final Submission** | Submitter | Sep 4, 14:00 UTC | Compile all fields & submit to lablab.ai |

---

## Notes & Caveats

1. **Account Eligibility:** The test account 0TCX is ineligible because it's pre-existing. A brand-new account MUST be created for submission and used for the final demo. Do this on Aug 27–28.

2. **Video Narration:** The demo script is complete and detailed. Record narration professionally (clear audio, measured pace). Sync to dashboard visuals carefully.

3. **Social Media Timing:** Post early (Aug 20–26) rather than at the deadline. This builds visibility and demonstrates "build in public" authenticity.

4. **Shariah Transparency:** The minority-position framing is non-negotiable. Do not downplay the scholarly disagreement or overstate fiqh approval. The code works; the fiqh argument is explored research.

5. **P&L Framing:** Judges will look at risk-adjusted returns (Sharpe, Sortino, max drawdown), not raw P&L. Document this framing in the pitch deck and GitHub README.

---

## Document History

| Date | Update | Author |
|---|---|---|
| 2026-08-22 | Initial assembly of submission package; all fields mapped & status recorded | Claude |
| [date] | [update] | [author] |

# Alpaca AI Trading Agents Hackathon — Idea Collection

Hackathon: lablab.ai × Alpaca, **28 Aug – 4 Sep 2026**, $5,000 prize pool.
Source: https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon (fetched 2026-08-18)

This is idea collection only — nothing here has been built yet. Synthesized from Claude's own
analysis of this repo + a council consult with ChatGPT (gpt-5-nano) and Gemini (gemini-3-flash)
via `llm-council-skill`. Raw council transcript: see scratchpad
`council_output_hackathon_fit.json` from this session, or re-run
`llm-council-skill/llm-council/scripts/query_llms.py` for a fresh consult.

## The core tension (read this first)

Every track in this hackathon **requires options trading** — it's a hard qualification gate, not
a track-specific choice. Mainstream Islamic finance scholarship (including AAOIFI) generally
treats conventional listed options as *gharar* (excessive uncertainty) and objects to selling a
"right" rather than a tangible owned asset. A pure "avoid options" Shariah angle would disqualify
the project outright.

Decision made (confirmed with the user): don't dodge this — build a real **Shariah gate** that
restricts *which underlyings* and *which option structures* the agent may use, and make the
reasoning transparent and citation-backed as the actual differentiator, rather than a disclaimer
bolted on afterward. All three "council members" (Claude, ChatGPT, Gemini) independently converged
on the same framing: **the compliance/governance layer is the product**, not a constraint to
minimize. Gemini put it well: *"you aren't just building a bot; you are building a Governance
Layer."*

## Recommended track: Income & Portfolio Overlay Agents

Covered calls / cash-secured puts / wheel strategy on Shariah-screened, already-owned stocks.

**Why this track over the other three:**
- Most fiqh-defensible structure of the four tracks — asset-backed (you own the stock before
  writing the call, or hold 100% cash collateral for the put), which is the closest analogue
  contemporary scholars discuss favorably (framed as *Arboun*/down-payment or *Wa'd*/promise
  structures, not naked speculation).
- Rewards consistency over lucky one-off directional bets — fits a risk-managed brand better than
  Options Alpha (pure direction) or Volatility & Event (straddles/strangles, the hardest structure
  to defend on gharar grounds — all three council members flagged this track as weakest fit).
- Plays directly to what this repo already has: `shariah_gate.py`, `zoya_compliance.py` (a real,
  recognized halal screening provider), `risk_checks.py`, `approval_workflow.py`, and the
  execution-audit trail described in `CLAUDE.md`. The "gate before execution" architecture already
  exists — it just needs an options-structure filter bolted onto the existing chain and a new
  Alpaca adapter to replace `moomoo_paper_adapter.py`.

**Secondary/stretch track if time allows: Hedging & Risk Protection Agents** — protective
puts/collars defending a Shariah-screened portfolio. Also relatively defensible (protective/
necessity framing, "Takaful-like" per Gemini), reuses the same architecture.

## Concrete strategy ideas (by track)

### Income & Portfolio Overlay (primary)

1. **Covered calls on Shariah-screened holdings** — sell OTM calls only on stocks that already
   passed the Zoya/ratio screen and that the agent already owns. Strike must stay above cost
   basis. This is the single most-defensible structure across all three council responses.
2. **Cash-secured puts as "synthetic Arboun"** — sell puts only on Shariah-screened stocks the
   agent would genuinely want to own, backed 100% by cash (no margin — margin/interest is a
   separate Riba problem to gate against). Frame the premium as compensation for a purchase
   commitment, not a speculative bet.
3. **The Wheel** — chain 1 and 2: cash-secured put → assignment → covered call on the assigned
   shares → repeat. Consistent, auditable, and every leg is asset- or cash-backed.

### Hedging & Risk Protection (secondary)

4. **Protective puts as portfolio insurance** — buy puts only against stock the agent already
   holds, sized to the held quantity (no naked puts). Framed as *Takaful*-like risk mitigation
   under genuine need (*hajiyat*) rather than speculation (*tahsiniyat*).
5. **Collars for defined-outcome risk management** — protective put + covered call together on an
   owned Shariah-screened position, capping both upside and downside. Both council models
   independently suggested this as a natural "endowment-style" story (stable, defensible, easy to
   explain in a demo).

### Explicitly out of scope for the "defensible" pitch

Naked/uncovered options, purely directional speculation without an ownership or cash-backing
constraint, and volatility-only bets (straddles/strangles) are flagged by Claude and both council
models as the hardest to defend and are **not** part of the primary or secondary track ideas above.
If the team wants to attempt Options Alpha or Volatility & Event later for breadth, they'd need a
separate, explicitly-labeled "conventional, not Shariah-endorsed" track rather than folding them
into the compliance narrative.

## Cross-cutting differentiators (raised independently by multiple sources)

- **Transparent per-trade "compliance justification" in the audit log** — not just a PASS/REJECT
  flag, but a logged citation-backed reason (e.g. "executed under an Arboun-style structure; 100%
  cash-collateralized; underlying passed Zoya screen on 2026-08-28"). Extends the existing
  execution-audit contract rather than replacing it.
- **Purification calculator** — both ChatGPT and Gemini independently suggested calculating and
  earmarking the portion of premium/interest income considered "impure" for donation, as a
  concrete extra feature that scores on Technology Implementation without needing new external
  APIs (pure computation on existing Zoya ratio data).
- **Hard no-margin / no-Riba constraint enforced in code**, not just policy — e.g. an explicit
  `account.cash >= strike * 100` collateral check before any Alpaca order call, independent of
  what Alpaca's account settings would otherwise allow.
- **Framing for the P&L judging criterion**: don't try to win on raw P&L against directional
  bots — pitch and measure risk-adjusted return (Sharpe/Sortino) and capital preservation through
  drawdowns instead. All three sources flagged this as the honest way to reconcile a risk-managed
  strategy with a P&L-weighted judging rubric.
- **Social engagement criterion**: the Shariah-compliance angle is inherently a strong story for
  the required X/LinkedIn build-in-public posts — documenting the gharar/Arboun reasoning process
  is distinctive content, not just progress screenshots.

## Known gaps / what isn't solved yet

- **Broker migration is real work, not reuse.** `moomoo_paper_adapter.py` only talks to Moomoo —
  confirmed with the user it will be **replaced**, not adapted, since Alpaca's MCP/CLI requirement
  can't be satisfied through Moomoo at all. Alpaca's Trading API + MCP server/CLI integration is a
  new build. The existing Shariah/risk/approval-gate logic is broker-agnostic in spirit (operates
  on ticker/quantity/price, not Moomoo-specific types) but this hasn't been verified by reading
  the adapter interface in detail.
- **A fresh, dedicated Alpaca paper account is mandatory for judging** — reused/existing accounts
  are disqualified per the event page. Needs to be created and its account ID captured before
  final submission.
- No code, no Alpaca integration, and no changes to `backend/` have happened as part of this
  session — see `SHARIAH_GATE_NOTES.md` for a design sketch only.

## Reuse from `E:\Projects Stuff\Multi_Ai_IslamicFinance`

That folder is a separate, more research-heavy Islamic-finance knowledge base (same author, by
the look of the design docs) with sourced fiqh notes and an unbuilt "Shariah-Aware Trader"
product spec. What's actually reusable for this hackathon, and what isn't:

**Reusable — sourced fiqh grounding.** `01-Shariah-Principles/{Riba,Gharar,Maysir}.md` and
`Equity, stock ownership.md` give real, citable definitions (rooted in Quran/Hadith references
and Usmani's *Introduction to Islamic Finance*) instead of the LLM-generated citation claims
this doc originally flagged as a gap. Key line directly supporting the covered-call argument:
*"You must officially own the risk of the shares before you can sell them onward"* — i.e. the
whole defensibility case rests on ownership preceding the sale of a right, which is exactly what
a covered call / cash-secured-put gate should enforce and log. See `SHARIAH_GATE_NOTES.md` for
the citations wired in.

**Not directly reusable — wrong market.** `06-Agent-Design-Specs/shariah-gating-rules.md` and the
`02-Shariah-Compliant-Screening-Malaysia/` universe are scoped to **Bursa Malaysia only**, sourced
from the Securities Commission Malaysia / Shariah Advisory Council list. Alpaca trades **US-listed**
equities and options — the Malaysia SC/SAC list doesn't cover US tickers at all, so that universe
can't be swapped in directly. This repo's existing `zoya_compliance.py` (Zoya covers US-listed
stocks) remains the right screening source, not the Malaysia list.

**Reusable — US-market methodology approach.** `10-International-Paper/international-shariah-policy.md`
already worked out how to screen *non-Malaysian* equities properly: pick one declared methodology
(MSCI Islamic Index / S&P Shariah / FTSE Russell-Yasaar) rather than inventing ratios, and record
a dated per-ticker `{ticker, market, currency, methodology, constituent_status, effective_date,
source_reference, verified_at}`. If Zoya's US coverage or licensing turns out to be a blocker
during the hackathon, this is the documented fallback shape to fetch — not a from-scratch design.

**Important precedent to acknowledge, not hide.** `10-International-Paper/international-paper-scope.md`
(the sister project's own scoping doc for non-Malaysian markets) **explicitly excludes options,
leverage, and derivatives**: *"Leverage and derivatives | Prohibited."* That means the more
rigorously-documented version of this exact system already concluded options should be out of
scope for now. Building the options gate for this hackathon is a deliberate, labeled extension of
that policy — not a continuation of it — and the demo/writeup should say so explicitly rather than
imply this was already vetted. That honesty is itself consistent with the existing project's
stated principle: *"No strategy return, analyst opinion, AI confidence score, or user request can
override a failed Shariah gate"* (`shariah-gating-rules.md`) — the options gate has to hold itself
to the same fail-closed standard, freshly justified.

**Architecture pattern to reuse (not code, the shape).** `06-Agent-Design-Specs/risk-policy.md`'s
hard-limit table matches what's already implemented in this repo's `risk_checks.py` (5%
position / 25% exposure / etc.), and `product-vision.md`'s core loop — *"Code, not the language
model, calculates signals, validates compliance status... An LLM may explain the calculation but
may not choose a larger size"* — is the same deterministic-gate philosophy this repo already
follows per `CLAUDE.md`. Good continuity to mention in the pitch: this isn't a fresh compliance
concept invented for the hackathon, it's the same design philosophy carried from a more mature
sibling project.

## Judging-marks honest assessment ("is this too niche?")

The user asked directly whether the Shariah angle is too niche to score well. Per-criterion, from
Claude's own read plus the council consult:

- **Creativity & Originality — likely a genuine strength.** Both ChatGPT and Gemini independently
  flagged this as differentiated; most entrants will build generic momentum/sentiment bots. The
  risk isn't the subject being niche, it's under-explaining it — if the judges (general
  AI/fintech reviewers, not Islamic-finance scholars) can't follow *why* a trade was allowed or
  blocked in under ~30 seconds of demo video, the originality doesn't land. The "Shariah Trace"
  log format from `SHARIAH_GATE_NOTES.md` exists specifically to solve this.
- **Technology Implementation — realistic upside, real execution risk.** Extending an existing
  audit/gate chain onto a new broker is legitimate technical depth, not a reskin. But going from
  Moomoo-only to a working Alpaca MCP/CLI integration in a 7-day window (28 Aug–4 Sep) starting
  from zero Alpaca code is the actual schedule risk here, not the Shariah framing.
- **P&L Performance — the honest weak point.** Covered calls / cash-secured puts are a low-drama,
  income strategy; they will not out-P&L an aggressive directional bot in a single bullish week,
  and the hackathon window is short enough that a typical 30–45 DTE covered-call cycle won't even
  expire before judging. Mitigations worth deciding on deliberately: (a) explicitly frame and
  report risk-adjusted return (Sharpe/Sortino, max drawdown) rather than competing on raw P&L, and
  (b) pick short-dated (weekly, 0–7 DTE) contracts specifically so trades actually realize P&L
  events inside the 7-day window instead of sitting open at judging time.
- **Presentation & Execution — plays to this repo's strengths.** The existing approval-queue +
  execution-audit habit already produces exactly the kind of transparent trade trail a strong
  demo needs; this isn't new discipline to build, just a new thing to point the camera at.
- **Social Engagement — genuinely helped by the niche, not hurt.** A recognizable "first Shariah-
  compliant options agent on Alpaca" framing is more shareable/discussable content for the
  required X/LinkedIn posts than a generic bot update.

**Bottom line:** the niche isn't the risk — a 7-day build timeline covering a brand-new broker
integration, plus a P&L profile that structurally can't compete on raw returns, is the real risk.
Worth deciding early whether to keep the scope tight (Level 1 options only — see
`SUBMISSION_CHECKLIST.md` — covered calls and cash-secured puts, no protective puts/collars)
to protect delivery time, versus attempting the stretch track.

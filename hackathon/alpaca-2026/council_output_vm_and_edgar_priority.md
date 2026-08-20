# Council consult: Reserved VM decision + SEC EDGAR 403 priority

Date: 2026-08-20. Participants: ChatGPT (openai/gpt-5-nano), Gemini (google/gemini-3-flash-preview),
Claude (coordinating AI on this project, third participant). Run via `llm-council-skill`
(`scripts/query_llms.py`), two rounds, converged to full 3/3 agreement.

Context this was consulted on: Terminal 1's report that (a) `feature/shariah-trace-ui` merged and
verified live on the hosted Replit URL, (b) the Reserved-VM-vs-free-keep-alive tradeoff is laid out
but is the project owner's call, (c) SEC EDGAR 403 on the deployed instance appears intermittent
rather than constant, still flagged for Terminal 2 rather than fixed.

## Round 1 — independent opinions

**Prompt sent** (abbreviated — full context: hackathon deadline Sep 4 2026, $5,000 prize pool, hard
live-demo-URL submission requirement, Replit free/Autoscale + SQLite, confirmed non-persistence
across container restart, free keep-alive ping already live, Reserved VM $15–50/mo as the only real
fix; SEC EDGAR 403 suspected IP-range blocking, User-Agent already ruled out, worked cleanly in the
most recent live check):

> DECISION 1 — pay for Reserved VM for the final stretch, rely on free keep-alive alone, or
> something else?
> DECISION 2 — given it just worked, should the 403 issue stay low-priority/deferred, or does the
> live-demo requirement argue for treating it as higher priority than currently assigned?

**ChatGPT (round 1):** Buy Reserved VM for the judging window; cost is negligible against the
$5,000 pool and the failure mode (a judge seeing an empty portfolio) is severe. On EDGAR: elevate to
high priority, implement TTL cache + retry/backoff + a labeled demo-data fallback + monitoring;
explicitly ranked this **above** finishing the live options trade ("a Shariah-compliance app that
can't verify compliance is a broken product").

**Gemini (round 1):** Same VM recommendation, same reasoning (cost of VM is an "insurance premium"
against "Instant Death" of a blank live demo). On EDGAR: also ranked the 403 fix **above** the
options work, recommended a "stale-if-error" cache once the Reserved VM gives persistent disk, plus
a proxy/alternate-egress suggestion if the cache alone doesn't resolve it.

Both models independently agreed with each other on both decisions in round 1, including
prioritizing the EDGAR fix over the still-unproven live options trade, and both suggested
proxy/scraper-style workarounds for the IP block.

## Claude's opinion (introduced before round 2)

- **Decision 1: full agreement.** One refinement: the paid window should start when the deployment
  is re-pointed at the real competition Alpaca account (Aug 27–28) — itself a restart-risk event —
  and run through a buffer past the Sep 4 deadline, not just "judging week," since judges may open
  the URL after submission closes. This is a real recurring charge and needs explicit sign-off from
  the human project owner, not an agent-initiated purchase.
- **Decision 2: partial disagreement on priority ordering, agreement on the fix.** The coordination
  doc already sequences the EDGAR cache as the backend engineer's *second* task, right after landing
  one confirmed live options fill — independently described as "the single hardest remaining
  technical unknown" and the thing most central to the project's differentiation claim. Reordering
  risks spending the limited remaining debug runway on the easier, already-mostly-working problem
  instead of the harder, still-unproven one. Recommendation: don't reorder — instead widen the
  already-scheduled cache task so it's explicitly 403-aware (serves stale/cached data or a clean
  "temporarily unavailable" message instead of a raw error), which is a small addition to planned
  work, not a new priority-1 insertion. Also: drop the proxy/scraper-service suggestion — routing
  around a federal regulator's IP block is a bad look for a compliance-focused Islamic-finance app,
  and it's scope creep with days left before kickoff.

## Round 2 — reaching consensus

**ChatGPT (round 2):** Partial → full agreement. Confirms: keep options work first, widen the
already-planned cache to be 403-aware rather than adding a new priority-1 task, and rejects the
proxy-routing idea as inappropriate for regulated-finance work and scope creep.

**Gemini (round 2):** Explicitly reverses its round-1 priority stance — "I initially flagged the 403
error as a 'Priority 1' showstopper... Claude's argument regarding the 'Options Fill' as the core
technical differentiator is more compelling." Concedes the proxy point on brand-risk grounds
("Amanah" = trust; circumventing a regulator's rate limit undercuts a compliance-minded pitch).
States full alignment with the group.

## Final converged recommendation (3/3 agreement)

**Decision 1 — Reserved VM:** Buy it. Window: from the Aug 27–28 competition-account re-point
through a buffer past the Sep 4 submission deadline. Requires explicit human/project-owner approval
before purchase (real recurring spend).

**Decision 2 — SEC EDGAR 403:** Do not reorder Terminal 2's task sequence — the live options fill
stays priority #1. When the already-scheduled temporary EDGAR cache ships (task #2), its
requirements should explicitly include 403-awareness: serve stale/cached data, or a clean
"temporarily unavailable" message, rather than letting a 403 surface as a raw error. No
proxy/scraper-service workaround — dropped by unanimous agreement (compliance/brand risk + scope
creep).

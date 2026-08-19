# Parallel Work Split — three terminals

Coordination doc for three terminals working the hackathon build at once. Supersedes the
previous two-terminal version of this doc — that split (`feature/shariah-options-gate` /
`feature/alpaca-adapter`) is done; both branches are merged into `master` and deleted. Written
so a fresh session in any of the three terminals has everything it needs without replaying prior
conversation.

## Why this split

Per `NEXT_STEPS.md` (current as of 2026-08-19), the backend architecture — gate chain, Alpaca
adapter, real SEC EDGAR screening, option strike selection — is built and tested, but **no
trade has ever run end to end against the real broker**, the demo has no judge-facing
justification UI, and the fiqh citations backing the options-structure gate are secondary
summaries rather than primary sources. Three genuinely independent workstreams follow from that:
backend needs to get a real trade working and expose new endpoints; frontend needs to build the
UI those endpoints will feed; research needs to strengthen the citations and answer open
questions neither of the other two should have to stop and chase down themselves.

## ⚠ Blocks everything — resolve first

The current (test, non-hackathon) Alpaca paper account is `MARGIN`, and `account_shariah_gate`
rejects margin accounts outright — **every** order, including plain equity, currently fails
`margin_account_not_permitted`. This is `account_shariah_gate` working as designed, not a bug.
Terminal 2's first task is resolving this (see below) — nothing that depends on a live trade can
proceed until it's resolved. Do **not** relax the gate to unblock this.

Note: the hackathon's own dedicated paper account (created once the event starts) may or may not
have this problem — but the current test account does, and Terminal 2 should get a real trade
working now against whatever CASH account is available, rather than waiting for the event key.

## Terminal 1 (Sonnet) — Frontend / demo

Worktree: `.worktrees/shariah-trace-ui`, branch `feature/shariah-trace-ui`.

Owns:
- `dashboard/index.html` and its JS only.
- **Shariah Trace panel** — a dashboard view showing, per trade: verdict → which rule fired →
  the fiqh basis with citation. This is the judge-facing artifact both council models (see
  `council_output_current_progress.md`) flagged as the single highest-leverage piece for the
  Creativity & Originality and Presentation & Execution judging criteria. Consumes whatever
  `GET /stock/{symbol}/explain`-shaped endpoint Terminal 2 exposes — do not invent the endpoint
  shape unilaterally, coordinate on the contract (see Handoff contract below).
- **Clear the stale Moomoo-era position** — `4.0 AAPL @ 323.3487`, account suffix `1740`, in
  `backend/paper_trading.db`. It predates the Alpaca account and will pollute exposure math in
  any demo screenshot or video.
- **Demo hosting** — get a stub of the dashboard deployed to Streamlit, Replit, or Vercel now
  (submission requires one of these). Prove the deploy path early rather than on the last day.

Does **not** touch: `backend/local_api.py`, any gate module, or `option_strategy.py`.

## Terminal 2 (Opus) — Backend

Worktree: `.worktrees/live-trade-backend`, branch `feature/live-trade-backend`.

Owns:
- **Resolve the margin blocker** (above) — verify via `check_config.py` / `check_alpaca_status`
  whether a CASH paper account is available; provision one if Alpaca supports it. If it does
  not, this needs a documented, scholar-reviewable policy decision about how the system should
  treat a paper margin account — not a code change that weakens `account_shariah_gate`.
- **Get one real trade through end to end** via the `alpaca_mcp` transport — any Shariah-PASS
  symbol, one share (or one Level 1 option leg), full preview → approve → `EXECUTE PAPER` →
  fill → reconcile chain, against the real Alpaca paper API. This is the single most important
  task across all three terminals — `NEXT_STEPS.md` calls it the largest unquantified risk, and
  both council models independently flagged it as the actual thing standing between this project
  and a working submission.
- **Expose `option_strategy.py` over HTTP** and build `GET /stock/{symbol}/explain` — the
  backend half of Terminal 1's trace panel. Coordinate the response shape with Terminal 1 before
  building it out fully (see Handoff contract).
- **Screening store** — SEC EDGAR raw-response cache + a `shariah_screens` table (append-only),
  plus a request throttle on `sec_request` (SEC's own guidance: max ~10 req/s). Design is already
  sketched in `NEXT_STEPS.md` under "Next session — time-varying compliance"; the three open
  questions listed there (purification-tracking scope, re-screen trigger, cache TTL) should be
  answered before building, not deferred further.
- Delete or reroute `backend/us_strategy.py`'s direct `zoya_compliance` import — it is a second,
  parallel screening path to a different provider, which the "one screening record, two views"
  constraint in `NEXT_STEPS.md` explicitly forbids.

Does **not** touch: `dashboard/index.html`/JS, or anything under `hackathon/alpaca-2026/` docs.

## Terminal 3 (Haiku or Sonnet) — Research

Worktree: `.worktrees/hackathon-research`, branch `research/hackathon-notes`. Produces reference
documents only — never edits `backend/` or `dashboard/`.

Owns:
- **Upgrade the fiqh citations from secondary to primary sources.** The options-structure
  allow-list in `SHARIAH_GATE_NOTES.md` currently cites a sister project's paraphrase of Usmani
  and Visser, not primary AAOIFI standard text or directly-quoted scholarly opinion. Both
  council models named this as the top risk to the compliance narrative — find and cite the
  primary sources (or the closest verifiable equivalent) for each of: covered call, cash-secured
  put, protective put, collar.
- **Alpaca account research feeding Terminal 2's blocker** — does Alpaca offer a CASH paper
  trading account distinct from MARGIN, and how is one provisioned/selected at account creation?
  This unblocks Terminal 2 fastest if answered quickly.
- **Submission logistics** — re-verify the lablab.ai Hackathon Rule Book and event page (last
  fetched 2026-08-18) for any changes, and confirm the exact technical constraints of Streamlit /
  Replit / Vercel hosting for a FastAPI + static-dashboard app, to inform Terminal 1's hosting
  work.

Output location: new files under `hackathon/alpaca-2026/research/` (e.g.
`fiqh-primary-sources.md`, `alpaca-cash-account.md`, `submission-logistics.md`) — do not edit
`SHARIAH_GATE_NOTES.md` directly; Terminal 2 or a later session incorporates findings into it
after review.

## Handoff contract (the one place terminals meet)

Terminal 1 and Terminal 2 meet at exactly one interface: the `GET /stock/{symbol}/explain`
response shape (verdict, rule fired, fiqh basis, citation) that Terminal 2 builds and Terminal 1
renders. Before Terminal 1 builds the panel against a guessed shape, agree the JSON contract
first — even a one-message exchange of the intended field names avoids a rebuild. Once that
contract is fixed, both terminals can build independently.

**Known collision risk:** if the `/explain` endpoint needs `local_api.py` route wiring (it
will), that file stays Terminal 2's exclusively — Terminal 1 never edits it.

Terminal 3 has no collision risk with either — it only writes new files under
`hackathon/alpaca-2026/research/`.

## Tooling — plugins and MCP servers to actually use

Added 2026-08-20. Plugins are installed on this machine but went almost entirely unused across
every terminal this session — everything got done through raw Bash/git/manual verification
instead. Some of that manual work is exactly what a plugin exists to do better. This section is
concrete about which plugin, for which situation, so "I could look that up" turns into actually
looking it up.

**Terminal 1 (frontend):**
- **`playwright` MCP — use this, not a claim.** Multiple reports this session said "tested in a
  real browser" or "verified in a real browser" without the manager being able to check it
  independently. Playwright can actually navigate the dashboard, click through the Shariah Trace
  panel, screenshot it, and read the console for errors — do that and report what it actually
  showed, not what you expect it would show.
- **`frontend-design` skill** — load it before any real visual/UX decision on the dashboard (the
  trace panel, the portfolio charts), not just for layout code.
- **`astral` (ruff)** — applies automatically via the PostToolUse hook now; no action needed, but
  `/ruff` is available for an explicit full-file pass if wanted.

**Terminal 2 (backend):**
- **`context7` MCP — use this before trusting memory on an API's behavior.** The quant-agent bug
  this session (silently reading Tiingo instead of the configured provider) and the margin-account
  confusion both trace back to assuming how an API behaves rather than checking. Before writing
  code against Alpaca's REST API, the MCP server's tool surface, or FastAPI internals, pull current
  docs with `context7` rather than relying on training-data recall.
- **`superpowers:systematic-debugging`** — load it at the start of any real bug hunt, not partway
  through. It formalizes the same approach that already found the quant-agent and margin bugs;
  use it deliberately instead of arriving at it by accident.
- **`superpowers:test-driven-development`** — matches this repo's own convention (write the test,
  mutation-check it, then implement) already documented in `CLAUDE.md`.
- **`pyright-lsp` + `astral` (ruff)** — automatic now; a red squiggle or hook-caught lint issue is
  worth reading, not clicking past.
- **`security-guidance` skill** — load it before touching anything credential- or
  account-provisioning-adjacent (`provision_cash_account.py`-style scripts, `.env` handling).

**Terminal 3 (research):** mostly not applicable — this role's actual tools (`WebFetch`,
`WebSearch`) are already being used correctly and were what caught the AAOIFI/IIFA citation
errors. `context7` doesn't apply (no code library docs involved in fiqh research).

**Manager / coordinator (next session in this role):**
- **`code-review` skill** — use it for structured review of what a terminal reports, instead of
  ad hoc manual diff-reading every time. This session's manual verification pattern (independently
  re-running claims against the real broker, re-checking citations) was the right instinct; the
  skill formalizes it and catches things a manual pass might miss.
- **`security-guidance` skill** — load it specifically before signing off on anything touching the
  Alpaca account, credentials, or broker-facing code.
- **`superpowers:verification-before-completion`** — matches the standing rule already in effect
  this session (verify before accepting any terminal's claim as done); load it explicitly rather
  than reinventing the same discipline each time.

## Merge checkpoint

Whichever terminal finishes a milestone first merges into `master` (or a shared integration
branch if more overlap emerges than expected). Before every merge: run the full local test suite
(18 suites, see `CLAUDE.md`) and review whatever landed in `backend/local_api.py`, since that is
the one file with any real concurrency risk. The other terminals rebase on top rather than
continuing to diverge.

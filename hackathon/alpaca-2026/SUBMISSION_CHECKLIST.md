# Submission Checklist — Alpaca AI Trading Agents Hackathon

Mapped from the event page (https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon)
and the general lablab.ai Hackathon Rule Book (https://lablab.ai/hackathon-rules), both fetched
2026-08-18. Nothing here is done yet — this is a checklist to fill in before 4 Sep 2026, 15:00 UTC
(11:00 PM Malaysia Time).

## Account setup

- [ ] Sign up for Alpaca, open a paper trading account for early prototyping (any account is fine
      for this stage).
- [ ] Before final submission: create a **brand-new** Alpaca paper trading account dedicated to
      this hackathon. Projects on a reused/existing account are **not eligible for judging** —
      this is a hard disqualifier per the event page.
- [ ] Record that account's ID — required in the final submission for judges to evaluate P&L.

## Core technical requirements (all mandatory to qualify)

- [ ] Autonomous agent built using Alpaca's **Trading API**.
- [ ] Uses either Alpaca's **MCP server** or **CLI** (not optional — one of the two is required).
      Repo: https://github.com/alpacahq/alpaca-mcp-server — run via `uvx alpaca-mcp-server`
      (needs Python 3.10+ and `uv`); Docker deployment also available.
- [ ] Strategy **incorporates options trading** in some form (mandatory in every track). Level 1
      (covered call + cash-secured put) covers the primary track and needs no account upgrade —
      see `SHARIAH_GATE_NOTES.md` for the full level mapping.
- [ ] Everything runs against the **paper trading environment** — no real capital.

## Alpaca credentials (do this yourself — do not paste the key into chat)

The MCP server reads `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` from **environment variables only**,
set in the MCP client's own config (its docs say "credentials are set in one place only" — no
`.env` file for the MCP server itself). For anything in this repo's own `backend/` that calls
Alpaca directly (outside the MCP server), follow the existing pattern in `backend/config.py`
(`os.getenv(...)` reads from `backend/.env`, same as `ZOYA_API_KEY`) — add
`ALPACA_API_KEY_ID` / `ALPACA_SECRET_KEY` there yourself when that code exists.

- [ ] Create the Alpaca API key/secret in the Alpaca dashboard.
- [ ] Set it directly in your MCP client config / `backend/.env` yourself — not shared in chat.
- [ ] Confirm `ALPACA_PAPER_TRADE` (or equivalent) is `true` before any testing.

## Track

- [ ] Confirm final track: primary = Income & Portfolio Overlay Agents; stretch = Hedging & Risk
      Protection Agents (see `IDEAS.md`).

## Submission package

- [ ] Project title (clear, descriptive).
- [ ] Short description.
- [ ] Long description.
- [ ] Technology & category tags.
- [ ] Cover image — PNG or JPG, **16:9 aspect ratio**.
- [ ] Video presentation — **MP4**.
- [ ] Slide presentation — **PDF**.
- [ ] Public **GitHub repository**.
- [ ] Demo application hosted on **Streamlit, Replit, or Vercel** (per general Rule Book).
- [ ] Application URL.
- [ ] Alpaca paper trading account ID (see Account setup above).
- [ ] Up to 5 social media post links (X or LinkedIn), tagging **@lablabai**/lablab.ai and
      **@AlpacaHQ**/Alpaca. Optional but scored under the extra "Build in Public" challenge and the
      Social Engagement judging criterion.

## Judging criteria to keep in mind while building (from the event page)

- P&L Performance (paper trading results) — frame as risk-adjusted return, not raw P&L; see
  `IDEAS.md`.
- Technology Implementation — how well Alpaca Trading API / MCP / CLI are actually used.
- Creativity & Originality — the Shariah-gate angle is the intended differentiator here.
- Presentation & Execution — demo clarity, reasoning behind trades should be shown, not just
  results.
- Social Engagement — quality + reach of the build-in-public posts.

## Team

- [ ] Confirm team size (1–6 allowed) and, if a team, agree in advance who receives prize funds —
      prizes are paid to one individual, not split automatically by lablab.ai/Alpaca.

## Logistics

- [ ] Register on both the lablab.ai platform and the lablab.ai Discord server (both required to
      participate, per Rule Book).
- [ ] Read the Hackathon Guidelines, Getting Started Guide, and Rule Book before kickoff.
- [ ] Kickoff: Aug 28, 11:00 PM Malaysia Time. Discord Q&A: Aug 29, 12:00 AM Malaysia Time.
- [ ] Manual submission fallback exists (6 hours post-hackathon) only with prior organizer/mentor
      approval for valid technical issues — don't rely on this as a plan.

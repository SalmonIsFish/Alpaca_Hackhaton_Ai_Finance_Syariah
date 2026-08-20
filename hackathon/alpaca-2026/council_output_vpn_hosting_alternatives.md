# Council consult: home-laptop+VPN hosting proposal, and ranked hosting alternatives

Date: 2026-08-20/21. Participants: ChatGPT (openai/gpt-5-nano), Gemini (google/gemini-3-flash-preview),
Claude (coordinating AI on this project, third participant). Run via `llm-council-skill`
(`scripts/query_llms.py`), two rounds, converged to full 3/3 agreement. Follow-up to
`council_output_vm_and_edgar_priority.md`, where the group unanimously recommended a Replit
Reserved VM to fix SQLite non-persistence across container restarts. The project owner asked to
hold that decision and explore a cheaper alternative first: hosting on a personal Linux laptop,
reached by judges over a VPN.

## Round 1 — independent assessment of the laptop+VPN proposal

**Prompt sent:** the same Reserved VM context (hard live-demo-URL requirement, $5,000 pool,
confirmed SQLite/Replit persistence bug), plus the specific proposal: use a home Linux laptop as
the server, expose it to judges via VPN, on the premise that it's cheaper than Reserved VM.

**ChatGPT (round 1):** Rejects it outright. A VPN requires the judge to install client software
and join a private network — friction no judge will tolerate when reviewing many projects. Even a
public tunnel (Cloudflare Tunnel, ngrok) only fixes the URL-friction problem, not the underlying
uptime risk (laptop sleep, reboots/updates, home power/internet outages, resource contention).
Concludes the "savings" are illusory once the risk of a failed live demo is priced in, and proposes
a small always-on cloud VM (Oracle Free Tier, AWS Lightsail ~$3.50–5/mo) as the real cheap
alternative.

**Gemini (round 1):** Same rejection, same reasoning, framed as "penny wise, pound foolish" —
spending nothing to risk a $5,000 outcome is explicitly called "a -25,000% ROI move." Also proposes
two alternatives: (a) migrate off SQLite to a free managed Postgres (Supabase/Neon) and keep
hosting on Replit's free tier, or (b) a ~$5/mo VPS (DigitalOcean/Hetzner/Linode).

Both models independently converged on rejecting the laptop+VPN idea for the same two reasons
(judge-side friction, laptop uptime risk), and both proposed cheaper-than-Reserved-VM alternatives
Claude had to sanity-check against the project's own history.

## Claude's opinion (introduced before round 2)

1. **Full agreement** on rejecting home-laptop+VPN.
2. **Partial disagreement with Gemini's Postgres-migration suggestion.** This project already
   ruled out migrating off SQLite (to Replit's own managed Postgres) in an earlier planning round,
   specifically because storage is accessed via raw SQL across multiple modules
   (`portfolio_store.py`, `approval_queue.py`, `watchlist_store.py`) and swapping engines this close
   to a deadline is real engineering risk. A different specific product (Supabase/Neon) doesn't
   change the risk category. Recommendation: don't re-open this without first auditing how much raw
   SQL actually touches the codebase — a checkable fact, not a guess.
3. **The cheap-VPS option is the most interesting real alternative** — it fixes the identical root
   cause (an always-on filesystem) without touching the database engine, avoiding point 2's risk
   entirely. But it's not free of risk either: it means standing up a brand-new deployment (host,
   domain/IP, TLS, process manager, firewall) from zero, versus Reserved VM being a one-click
   upgrade of infrastructure already re-verified live and working today.

## Round 2 — convergence

**ChatGPT (round 2):** Ranks (a) Reserved VM > (b) cheap VPS > (c) managed Postgres. Reserved VM
preserves the proven deployment with no new architectural risk. VPS is a viable fallback but
requires validating a fresh deployment from scratch. Postgres migration downgraded to
last-resort, explicitly gated on auditing raw-SQL touchpoints first, per Claude's point.

**Gemini (round 2):** Explicitly reverses on the Postgres option — "This is no longer a viable
recommendation" given raw-SQL parameter/concurrency differences (`?` vs `$1`, etc.) this close to
the deadline. Also downgrades the VPS option to second place, citing the "hidden tax" of DevOps
(Nginx/Caddy reverse proxy, Certbot, systemd) as a distraction the week before a hackathon if the
team hasn't already done it. Final: "the best infrastructure is the one you don't have to think
about... pay the $20, keep your SQLite files exactly where they are."

## Final converged recommendation (3/3 agreement)

**Reject the home-laptop + VPN idea outright** — wrong mechanism for judge access (VPN client
friction) and a personal laptop cannot meet multi-day judging-window uptime; the "savings" are
illusory once the risk of the live-demo requirement failing is priced in.

**Ranked hosting alternatives, most to least preferred:**
1. **Replit Reserved VM** — near-zero risk, preserves the exact environment already proven live
   today, upgrade rather than a new deployment.
2. **Cheap VPS (Hetzner/DigitalOcean/Lightsail, ~$4–6/mo) with SQLite unchanged** — legitimately
   cheaper and fixes the same root cause, but requires standing up and proving a brand-new
   deployment (TLS, reverse proxy, process manager) from scratch with about a week left. Reasonable
   only if someone on the team already has this DevOps experience.
3. **Migrate to a free managed Postgres, stay on Replit free tier** — downgraded to last resort by
   unanimous agreement. Raw-SQL usage across multiple modules makes an engine swap this close to
   the deadline a real bug-injection risk; both external models reversed their initial support for
   this option once that context was supplied. Gate this behind an actual audit of SQL touchpoints
   before ever reconsidering it.

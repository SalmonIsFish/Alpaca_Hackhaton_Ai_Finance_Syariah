# Hackathon Submission Logistics & Hosting Constraints

**Research Date:** 2026-08-19  
**Last Verified:** From lablab.ai Alpaca AI Trading Agents Hackathon event page (2026-08-18 to 2026-08-19)  
**Status:** READY FOR SUBMISSION PLANNING

## Summary

The **Alpaca AI Trading Agents Hackathon** (Aug 28 – Sep 4, 2026) requires submissions to:
1. Run on Alpaca's paper trading API via MCP server or CLI
2. Incorporate options trading
3. Deploy to a hosted demo with a public Application URL
4. Include video + pitch deck + GitHub repo
5. Use a **dedicated new Alpaca paper account** created for the hackathon (existing/reused accounts ineligible)

This document covers hosting constraints for each platform when running **FastAPI backend + static HTML dashboard**, and identifies risks for Terminal 1's demo deployment work.

**Correction (2026-08-21):** item 3 originally read "Deploy to Streamlit, Replit, or Vercel (one
of these three is mandatory)." The actual submission form has no such restriction — it's a
free-text Application URL field. The project now hosts on a self-managed VPS at
`https://amanahtrader.uk`, which satisfies the requirement. The platform-specific analysis below
is kept for reference (it's what informed the original Replit choice) but is no longer a
constraint driving the hosting decision.

---

## Official Hackathon Rules Summary

### Timeline
- **Event Dates:** August 28 – September 4, 2026
- **Submission Deadline:** September 4, 2026, 15:00 UTC (hard stop)
- **Early platform deployment:** Now (Aug 19–28) is ideal for proving the deploy path

### Technical Requirements
- Must use **Alpaca Trading API** (live paper trading API, not mocked)
- Must use **Alpaca MCP server** or **Alpaca CLI**
- Must incorporate **options trading** (mandatory in all 4 tracks)
- Must run against **Alpaca's paper trading environment**
- Must use a **brand-new Alpaca paper account** created specifically for the hackathon
  - Reused or existing accounts are **ineligible for judging**
  - Options trading approval may take time; provision early

### Submission Artifacts
- **Code:** GitHub repo (public or private, both OK)
- **Live demo:** URL to deployed application (required for evaluation)
- **Video:** Demo video showing the system in action (recommended)
- **Pitch deck:** 3-5 slides on approach and results (recommended)
- **Social media:** Up to 5 links to X/LinkedIn posts about your project (optional, helps scoring)

### Judging Criteria (5 categories, equal weight expected)
1. **P&L Performance:** Risk-adjusted returns, drawdown management, strategy viability
2. **Technology Implementation:** Code quality, API integration, architecture robustness
3. **Creativity & Originality:** Unique approach, differentiated positioning
4. **Presentation & Execution:** Demo clarity, documentation, professionalism
5. **Social Engagement:** Twitter/LinkedIn visibility, narrative resonance

### Account & Testing Rules
- Create a **dedicated, brand-new paper account** for hackathon judging
- Do **not** reuse existing paper accounts — ineligible
- Do **not** use live trading accounts — will fail the "paper only" requirement
- All testing before hackathon starts should use a separate test account
- Once the event begins, provision the "competition account" and run final tests there

---

## Hosting Platform Comparison

### 1. Streamlit

**Profile:** Python-native, simplest for Python-focused projects, new FastAPI support (2026)

**FastAPI + Static Dashboard Compatibility:**
- ✅ **Native FastAPI support:** Streamlit 2026 introduces `st.App`, an experimental ASGI-compatible entry point
  - Allows running FastAPI routes natively within Streamlit
  - Middleware, lifecycle hooks, and custom routes supported
- ✅ **Traditional approach:** Run FastAPI backend separately; Streamlit frontend calls via `requests` library
  - Frontend on Streamlit Cloud
  - Backend on any cloud (Render, Railway, custom server)
  - Separate domains = Cookie/CORS handling required
- ✅ **Docker:** Full containerization of both services; deploy as multi-container app

**Constraints:**
- Streamlit Cloud's free tier has limitations on concurrent users and compute
- For multi-user trading dashboard, you may hit resource limits during judging
- New ASGI support is experimental; stability not yet proven in production
- Large data science libraries (numpy, pandas) are fine; very large compiled libraries (TensorFlow) can be problematic

**Recommendation for Amanah Trader:**
- If you want the **simplest single-deploy option:** Use Streamlit Cloud with the native FastAPI support (if stable enough)
- If you want **maximum reliability:** Deploy FastAPI backend elsewhere (Render, Railway, or a VPS); Streamlit frontend on Streamlit Cloud calling the backend
- **Risk:** Experimental ASGI support may have bugs; test thoroughly before Sep 4

**Deployment time:** 5–10 minutes once code is ready

---

### 2. Replit

**Profile:** Full-stack Python hosting, free public endpoints, integrated development environment

**FastAPI + Static Dashboard Compatibility:**
- ✅ **Excellent for FastAPI:** Replit provides a permanent public URL for FastAPI backends
- ✅ **Serves static files:** Can host static HTML/JS dashboard in the same Replit (via FastAPI's StaticFiles)
- ✅ **One-click deployment:** Run code → Replit auto-publishes a public endpoint
- ✅ **Always-on:** Free tier includes a persistent endpoint (previously needed paid Replit for uptime)
- ✅ **Dashboard integration:** Your static `dashboard/index.html` can be served from FastAPI and hosted on the same Replit

**Constraints:**
- **Free tier has resource limits:**
  - CPU/memory constraints during high load (might be an issue during live judging)
  - Connection pooling or heavy concurrency may hit limits
- **Database persistence:** SQLite works, but can be fragile; PostgreSQL recommended for robustness
- **Cold starts:** Free tier may have latency on first request after idle period
- **Uptime SLA:** Free tier has no uptime guarantee (though generally reliable)

**Recommendation for Amanah Trader:**
- **Ideal if:** You want a single, simple deployment covering both backend and frontend
- **Risk:** Free tier may not survive heavy load during live demo to judges
- **Mitigation:** Upgrade to paid Replit if budget allows (better resources); or run a stress test before hackathon starts to identify limits

**Deployment time:** 2–5 minutes (literally point-and-run)

---

### 3. Vercel

**Profile:** Frontend-first, serverless Python support (FastAPI via serverless functions), global CDN, premium developer experience

**FastAPI + Static Dashboard Compatibility:**
- ✅ **FastAPI backend:** Supported via Python Serverless Functions (deployed as `/api/...` routes)
- ✅ **Static frontend:** Excellent support for static assets (HTML/CSS/JS) via CDN
- ✅ **Single repository:** Deploy both frontend and backend from one Git repo
- ✅ **Automatic scaling:** Handles traffic spikes well; serverless scales automatically

**Constraints:**
- **File size limits:** Python dependencies can exceed Vercel's limits (especially if you bundle large libraries)
  - SEC EDGAR screening + dependencies might push you near the limit
  - TensorFlow, pandas, numpy combined can hit limits; lightweight dependencies only
  - **Solution:** Minimize dependencies; use lightweight alternatives
- **Cold starts:** Serverless functions have ~1–2s cold start latency on first request
- **Different domains:** Frontend on `*.vercel.app`, backend API on `*.vercel.app/api/...`
  - Cookies work (same domain), but CORS headers must be configured explicitly
- **Database:** No built-in SQLite; need external DB or file-based (problematic for serverless)
  - Use Vercel KV (Redis), Neon (Postgres), or file-based state

**Constraints Specific to Amanah Trader:**
- SEC EDGAR screening module imports heavy dependencies (XBRL parsing)
- Large database files (portfolio_store, paper_trading.db) don't work well in serverless
- **Risk:** May exceed file size limits; cold starts may make the demo feel slow

**Recommendation for Amanah Trader:**
- **NOT IDEAL** for this project due to:
  - Heavy Python dependencies (SEC EDGAR, XBRL parsing)
  - Persistent state requirements (SQLite for approval queue, portfolio tracking)
  - Serverless cold starts will make the demo feel sluggish
- **Consider only if:** You want the premium Vercel developer experience and can refactor to use external database + lighter dependencies

**Deployment time:** 10–15 minutes (more configuration needed)

---

## Recommendation for Terminal 1 (Dashboard/Demo)

### Best Hosting Option: **Replit**

**Why Replit:**
1. **Simplest deployment:** One repo, one-click deploy, one public URL
2. **Supports both backend and frontend:** FastAPI backend + static dashboard in the same deployment
3. **Free tier is adequate:** For a hackathon demo (not sustained production), free Replit resources are sufficient
4. **Proven with Python:** Widely used for Streamlit, FastAPI, and full-stack Python projects
5. **Minimal configuration:** No separate backend/frontend domain management, no CORS complexity

**Setup Steps for Terminal 1:**
1. Push code to GitHub (backend + dashboard in one repo)
2. Import repo into Replit
3. Add startup command to serve both FastAPI and static files
4. Click "Run" → Replit publishes a public URL
5. Share URL in hackathon submission

**Fallback Option: Streamlit** (if you prefer Streamlit UI over custom HTML)
- Use Streamlit's 2026 native ASGI support for FastAPI
- Or run FastAPI backend separately and call from Streamlit frontend
- Simpler than Replit if you're already familiar with Streamlit

**Avoid: Vercel** (for this project)
- File size + cold start limitations are not worth the extra complexity

---

## Account Provisioning Timeline

### Critical Path
1. **Now (Aug 19–26):** Provision a **test account** for development
   - Run through the full preview → approval → execute → reconcile flow
   - Verify Alpaca integration works end-to-end
   - Test options trading approval
   - This is Terminal 2's primary focus

2. **Aug 27–28 (hackathon starts):**
   - Create a **brand-new, dedicated paper account** for the competition
   - Verify it's paper-only and options-enabled
   - Move the winning trade(s) to this account before submission

3. **Sep 1–4 (final submission period):**
   - Run final demo on the competition account
   - Verify all trades settle and reconciliation works
   - Record demo video
   - Publish to hosted platform (Replit/Streamlit/Vercel)

### Account Setup Notes
- **Options approval:** Paper accounts appear to have options pre-enabled (observed as options_trading_level 3 on account 0TCX with no activation delay). Live accounts may require 1–2 business days. For the hackathon, provision the paper competition account by Aug 27 and verify options are enabled immediately.
- **Paper account creation:** Instantaneous
- **Margin vs. Cash:** All Alpaca accounts default to margin (see `alpaca-cash-account.md`)

---

## Submission Checklist

### Code Submission (Due Sep 4, 15:00 UTC)
- [ ] GitHub repo (public or private)
- [ ] README with setup instructions
- [ ] .env.example with all required API keys documented
- [ ] No secrets committed (verify with git-secrets or manual review)
- [ ] All tests pass locally

### Hosted Demo (Due Sep 4)
- [ ] Application deployed to Streamlit, Replit, or Vercel
- [ ] Live URL is stable and accessible
- [ ] Dashboard shows real positions and trade history from Alpaca account
- [ ] Shariah Trace panel displays fiqh citations (Terminal 1's contribution)
- [ ] Demo does **not** require manual configuration to run (API keys pre-set or env vars)

### Video & Pitch (Recommended, helps judging)
- [ ] 3–5 minute demo video
  - Show preview → approval → execution flow
  - Narrate the Shariah gate decisions
  - Highlight fiqh justification
- [ ] Pitch deck (5–10 slides)
  - Problem statement (Shariah-compliant options)
  - Solution approach (gate chain, fiqh framework)
  - Results (trades executed, compliance verdicts)
  - Unique positioning (governance-first, citation-backed)

### Social Media (Optional, helps engagement scoring)
- [ ] Up to 5 posts on X/LinkedIn
  - Announce the hackathon entry
  - Show the gate in action
  - Highlight the fiqh angle
  - Celebrate live trade execution

### Account Management
- [ ] **Test account:** Used for all development (do not submit with this)
- [ ] **Competition account:** Brand-new, created for hackathon (submit with this)
- [ ] **Account verification:** Confirm it's paper-only, options-enabled, and linked to your Alpaca API keys

---

## Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **Options approval takes too long** | Provision test account this week; competition account by Aug 27 |
| **Hosting platform downtime during demo** | Test your hosted demo daily; have a backup URL ready |
| **Browser caching stale position data** | Implement cache-busting headers in FastAPI; add manual "Refresh" button in dashboard |
| **Live Alpaca API unreliable during demo** | Use mocked Alpaca adapter for demo if needed; disclosure in video |
| **Demo account has no starting capital** | Alpaca auto-funds paper accounts with $25k; should be sufficient |
| **Fiqh citations not loading on hosted dashboard** | Test dashboard on mobile and desktop; ensure images/fonts load correctly |
| **Social media visibility low** | Post early (Aug 25+); use hashtags #AlpacaHackathon #IslamicFinance #FinTech |

---

## Timeline Summary

| Date | Milestone | Owner |
|---|---|---|
| **Aug 19** | Provision test Alpaca account; begin integration testing | Terminal 2 |
| **Aug 22** | Confirm hosting platform choice; prototype deploy | Terminal 1 |
| **Aug 26** | All local tests pass; live end-to-end trade working on test account | Terminal 2 |
| **Aug 27** | Create competition account; cold-start options approval | Terminal 2 |
| **Aug 28** | Hackathon begins; final demo video recording | Terminals 1 & 2 |
| **Sep 1** | Hosted demo live and stable; GitHub repo ready | All terminals |
| **Sep 4, 15:00 UTC** | **SUBMISSION DEADLINE** — GitHub repo, hosted URL, video, pitch, social media | All |

---

## Sources

- [Alpaca AI Trading Agents Hackathon — lablab.ai](https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/)
- [Streamlit 2026 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- [FastAPI + Streamlit Integration](https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/)
- [Deploy FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [Deploy FastAPI on Replit](https://www.storylane.io/tutorials/how-to-deploy-a-fastapi-app-on-replit-1eb54)
- [Vercel Backend APIs Guide](https://vercel.com/kb/guide/hosting-backend-apis)

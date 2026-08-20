# Council consult: long-term hosting for Amanah Trader as an ongoing 24/7 project

Date: 2026-08-21. Participants: ChatGPT (openai/gpt-5-nano), Gemini (google/gemini-3-flash-preview),
Claude (coordinating AI on this project, third participant). Run via `llm-council-skill`. Full 3/3
agreement reached in round 1 -- no disagreement surfaced, so no second round was needed. Follow-up
to `council_output_vpn_hosting_alternatives.md`, which covered short-term hackathon-judging hosting
only.

New context: the project owner wants Amanah Trader to become an ongoing, continuously-running
project after the hackathon, not just a demo that gets shut down. Question: for that long-term
home, rent a cheap VPS (~$4-6/mo, self-managed) or self-host permanently on a Linux machine already
owned at home, reached via a real public URL?

## Independent assessments

**ChatGPT:** VPS, clearly. A trading system needs predictable connectivity to the broker API;
residential internet/power outages, CGNAT, and ISP port-blocking are fundamental reliability risks
a VPS doesn't have. Flags the security angle explicitly: a home machine holding broker API keys and
facing the public internet is a target, and a compromise there threatens personal devices sharing
the same network, not just the trading app. Provided a concrete VPS hardening checklist (SSH key
auth, ufw firewall, Let's Encrypt TLS, systemd service with auto-restart, secrets via environment
variables, monitoring/alerting).

**Gemini:** Same conclusion, same core reasons, with two additional points worth keeping: (1) the
"cost paradox" -- a home machine idling 24/7 already draws enough power (~30-60W) that electricity
alone often costs close to what a VPS costs, so "free" self-hosting usually isn't actually free;
(2) the "blast radius" framing -- a VPS is a disposable, isolated sandbox, so a compromise stays
contained to a data-center VM, while a compromised home-hosted server gives an attacker a foothold
inside the same network as personal devices, family photos, etc. Recommended Hetzner or
DigitalOcean specifically, with `ufw` restricted to 80/443/SSH and Docker Compose for reproducible
deployment.

## Converged recommendation (3/3, unanimous, no dissent)

**Standardize on a small cloud VPS for anything long-running and unattended.** Keep the home Linux
machine as a dev/test environment, not the production host. Core reasons, in order of weight:

1. **Reliability** -- a data center has redundant power/network with an SLA; home internet and
   power do not, and an outage mid-trade-lifecycle is a real liability for something meant to run
   unattended.
2. **Networking reality** -- most residential ISPs use CGNAT or block inbound ports, meaning a
   usable public IP often isn't available at all without an extra tunnel service, which reintroduces
   the exact complexity self-hosting was meant to avoid.
3. **Security isolation** -- this system holds live broker API keys. A VPS is a contained sandbox;
   a home server exposed to inbound traffic puts the whole home network at risk if compromised.
4. **Cost** -- once 24/7 electricity and any DDNS/tunnel workaround are counted, home hosting is not
   meaningfully cheaper than a $4-6/mo VPS, and the VPS cost is fixed and predictable.

Next step: pick a provider (Hetzner or DigitalOcean, per Gemini's suggestion) and stand up the VPS
following the hardening checklist above (SSH key auth only, `ufw` restricted to 80/443/SSH,
Let's Encrypt TLS, systemd-managed process with auto-restart, secrets via environment variables,
basic uptime/health monitoring).

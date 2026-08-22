# VPS Runbook — amanahtrader.uk

The production topology for Amanah Trader, which until now existed only on the box. A rebuild
or a handover was blocked without it. **No secrets in this file** — every credential is
referenced by location, never by value.

Audited over SSH on 2026-08-22. Everything below is read from the running server, not inferred
from the repo.

## Topology

| | |
|---|---|
| Host | `159.65.220.83`, DigitalOcean droplet `amanahtrader-vps` (kvm, 2 GB RAM, 48 GB disk, 7% used) |
| OS | Ubuntu 24.04.4 LTS, kernel 6.8.0-138-generic, no reboot pending |
| Domain | `amanahtrader.uk` + `www.amanahtrader.uk` |
| TLS | Let's Encrypt, expires 2026-11-18, `certbot.timer` enabled |
| Web | nginx 1.24.0 (Ubuntu), the only public surface |
| App | systemd `amanah-trader.service`, uvicorn on `127.0.0.1:8000` |
| Login | `ssh -i ~/.ssh/amanahtrader_vps amanah@159.65.220.83` |

`root` is locked at the OS account level by design — a password reset does not enable it. `amanah`
is the only login, is in `sudo`, and has **passwordless** sudo.

## The app

Checkout lives at `/home/amanah/amanah-trader`, tracking `origin/master` from
`github.com/SalmonIsFish/Alpaca_Hackhaton_Ai_Finance_Syariah.git`. Working tree clean.

```ini
# /etc/systemd/system/amanah-trader.service
[Unit]
Description=Amanah Trader FastAPI backend
After=network.target

[Service]
Type=simple
User=amanah
Group=amanah
WorkingDirectory=/home/amanah/amanah-trader/backend
Environment="PATH=/home/amanah/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/amanah/amanah-trader/.venv/bin/python -m uvicorn replit_app:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Three things about that unit are load-bearing and easy to break:

- **The entrypoint is `replit_app:app`, not `local_api:app`.** Despite the name, `replit_app.py`
  imports the same `local_api.app` object and mounts `/dashboard` onto it, so it serves the whole
  API *plus* the static dashboard. `backend/replit_start.sh` is **not** used and binds
  `0.0.0.0:8080`, which is wrong for this host — ignore it.
- **The bind is `127.0.0.1`.** uvicorn is not reachable except through nginx. Confirmed against
  `ss -tlnp`: nothing but 22, 80 and 443 listen on a public interface.
- **`Environment=PATH` starts with `/home/amanah/.local/bin`.** That is the only reason
  `PAPER_EXECUTION_ADAPTER=alpaca_mcp` works: the adapter shells out to `uvx alpaca-mcp-server`,
  and `uv`/`uvx` 0.12.5 live in that directory and are **not** on the default login PATH. Strip or
  reorder that line and broker execution breaks at demo time with a confusing error. The uv
  package cache is warm at `~/.cache/uv`.

Python 3.12.3 in `/home/amanah/amanah-trader/.venv`.

### Deploy

There is no deploy script. Deployment is `git pull` in the checkout followed by
`sudo systemctl restart amanah-trader`. `backend/.env` is **not** in git (`.gitignore:1`) and is
placed on the box by hand — see Credentials below.

### Runtime configuration

`/home/amanah/amanah-trader/backend/.env` — mode `0600`, owner `amanah:amanah`.
The execution-deciding values, which are not secrets:

```
PAPER_EXECUTION_ADAPTER=alpaca_mcp
PAPER_EXECUTION_ENABLED=true
```

`ALPACA_MODE` is absent and therefore defaults to `paper`; `alpaca_paper_adapter` hardcodes the
paper host regardless, so live trading stays impossible by construction rather than by config.

`ALLOWED_ORIGINS` is not yet set on the box. Once the CORS change is deployed, set it to
`https://amanahtrader.uk` — until then the app falls back to its permissive local-dev default.

## State

`/home/amanah/amanah-trader/backend/paper_trading.db` — SQLite, mode `0644`, owner `amanah`.

This is the demo's system of record and it exists **only on this box**. `backend/*.db` is
gitignored by design, so a trade run from a local checkout writes to a local file the deployed
instance never sees. Run the demo trade *through the deployed instance* so its own database
captures the position. There is currently **no backup of this file** — see Known gaps.

## Audit results, 2026-08-22

### Sound

| Check | Result |
|---|---|
| `PasswordAuthentication` | `no` |
| `PermitRootLogin` | `no` |
| `PubkeyAuthentication` | `yes`, `PermitEmptyPasswords no`, `KbdInteractive no` |
| ufw | active, `deny (incoming)` default, only 22/80/443 open (v4 and v6) |
| Listening publicly | 22, 80, 443 only — app bound to loopback |
| `backend/.env` | `0600 amanah:amanah` |
| unattended-upgrades | enabled and active |
| certbot | `certbot.timer` enabled, cert valid 88 days |
| Secrets in `~/.bash_history` | **0 matches** |
| Secrets in `/root/.bash_history` | no file |
| Secrets in `journalctl -u amanah-trader` | **0 matches** |
| Secrets in nginx logs | **0 matches** |
| Alpaca key shape (`PK…`) anywhere in the journal | **0 matches** |

The secret scan counted matches without printing values. Nothing needs rotating on the evidence
of this audit.

### Gaps found

1. **No authentication on the deployed API.** `POST /paper/execute/{queue_id}` is reachable by
   anonymous callers; its only gate is the phrase `EXECUTE PAPER`, which is hardcoded at
   `backend/local_api.py:110`, published in this open-source repo, and echoed back to any caller
   in the rejection payload at `local_api.py:1533`. It is a typo-guard, not a credential. Two real
   broker fills have already been placed through this instance.
2. **`fail2ban` is not installed, against 11,348 failed SSH auth attempts in 7 days.** None can
   succeed — password auth is off and only pubkey is offered — so this is noise rather than
   exposure, but it is free to stop.
3. **nginx proxies everything to uvicorn, including junk.** The vhost is Certbot's default: a
   single `location /`. Of **261,092** requests logged today from 1,079 unique IPs, **260,957 were
   404s** and only **101** were 200s. Real traffic in that window was 61 dashboard loads and a
   handful of API calls. Every scanner request currently costs a Python round-trip and about
   89 MB/day of access log.
4. **The box is actively scanned for exactly this project's secrets.** Bots have requested
   `/secrets.yml`, `/secrets.json` and `/.streamlit/secrets.toml` repeatedly from Google Cloud
   ranges. They found nothing — those paths 404 — but it establishes that "nobody will look" is
   not a defence.
5. **`server_tokens` is commented out** (`nginx.conf:21`), so `Server: nginx/1.24.0 (Ubuntu)`
   discloses the exact version. No HSTS, `X-Content-Type-Options`, `X-Frame-Options` or
   `Referrer-Policy` headers are set.
6. **`/docs`, `/redoc` and `/openapi.json` are public**, advertising the full write surface. They
   have been hit 14 times.
7. **`amanah` has passwordless sudo and runs the app.** Any RCE in the app is root on this box.
   Accepted for a hackathon deployment; recorded so the trade-off is deliberate.
8. **4 packages upgradable.** Routine `apt update && apt upgrade` was last run manually by the
   project owner; no reboot is pending.

Nothing has hit `/paper/execute`, `/paper/reconcile` or `POST /audit` — **0 requests** across the
whole log. The exposure is real but has not been exercised.

## The nginx vhost

As audited, before hardening. Certbot generated all of it; nothing was added by hand.

```nginx
server {
    server_name amanahtrader.uk www.amanahtrader.uk;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/amanahtrader.uk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/amanahtrader.uk/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = www.amanahtrader.uk) { return 301 https://$host$request_uri; }
    if ($host = amanahtrader.uk)     { return 301 https://$host$request_uri; }
    listen 80;
    server_name amanahtrader.uk www.amanahtrader.uk;
    return 404; # managed by Certbot
}
```

The hardened replacement is kept in the repo at `docs/deployment/nginx/amanahtrader.uk.conf`, so
the vhost is reviewable in git even though the file that runs lives on the box. The operator-key
map is deliberately **not** in that file — it is a separate include holding a secret.

## Credentials

`deployed-instance-trades.json:16` records that the local `backend/.env` was `scp`-ed to the VPS
verbatim, which puts the same Alpaca credentials on a Windows dev box and on a public server.

**At kickoff (Aug 27–28), do not repeat that.** When the dedicated competition account is created,
issue it a **separate key pair for the VPS** and place only that pair in the VPS `.env`. The local
checkout keeps its own keys for the test account.

Kickoff sequence:

1. Create the dedicated Alpaca paper account.
2. Issue VPS-only API keys; write them into `/home/amanah/amanah-trader/backend/.env` (`0600`).
3. Run `provision_cash_account.py --no-shorting --apply` against the new account.
4. Confirm `check_alpaca_status` reports `CASH`, `max_margin_multiplier=1`, `no_shorting=True`.
5. Restart the unit; confirm `/system/mode` on the live host.

The nginx operator key lives only in `/etc/nginx/conf.d/amanah_operator_key.conf`, mode `0600`,
root-owned. It is never committed and never printed into a session — read it with `cat` on the box
when you need to drive a demo trade.

## Known gaps, not yet closed

- No backup of `paper_trading.db`. Losing the droplet loses the demo trade history.
- No infrastructure as code. This document is the recovery path; a rebuild is manual.
- No monitoring or alerting. A crashed unit is discovered by loading the site.

## Stale files in the repo

Flagged rather than deleted, since they carry history:

| File | Why stale |
|---|---|
| `backend/LOCAL_DEPLOYMENT.md` | Moomoo-era, references a OneDrive path |
| `replit.md`, `.replit` | Replit hosting, superseded by this VPS |
| `backend/replit_start.sh` | Binds `0.0.0.0:8080`; the systemd unit above is authoritative |

`backend/replit_app.py` is **not** stale despite the name — it is the live entrypoint.

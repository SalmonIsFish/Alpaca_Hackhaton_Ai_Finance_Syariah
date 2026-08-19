"""Replit deploy entrypoint: one process, one public port, serving both the
FastAPI API (local_api.app) and the static dashboard together.

Owned by Terminal 1 (frontend/hosting), not local_api.py, per CLAUDE.md's
boundary -- Terminal 2 owns that file exclusively. This module only imports
the existing `app` object and mounts a StaticFiles directory onto it; it adds
no routes that could collide with anything local_api.py defines, and it makes
no gate, screening, or execution decisions of its own.

Replit's free tier exposes exactly one public port, which is why the API and
the dashboard -- normally two separate local processes (see CLAUDE.md
"Running it") -- need to be combined here. Local development is unaffected:
`backend/run_local.ps1` / the uvicorn command in CLAUDE.md still start the API
alone, and the dashboard is still opened as a plain file or via its own static
server, exactly as before.

The dashboard's own apiBase default already special-cases this: when
dashboard/index.html is not opened on localhost/127.0.0.1, it defaults the API
base field to same-origin (window.location.origin), so visiting the deployed
URL needs no manual configuration.
"""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from local_api import app

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"

app.mount("/dashboard", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")

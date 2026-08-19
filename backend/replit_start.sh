#!/usr/bin/env bash
# Replit start command -- see .replit at the repo root and backend/replit_app.py.
# Installs dependencies and runs the combined API + dashboard entrypoint on
# whatever port Replit assigns (falls back to 8080 for local testing of this
# script itself).
set -e
cd "$(dirname "$0")"
python -m pip install -r requirements.txt
python -m uvicorn replit_app:app --host 0.0.0.0 --port "${PORT:-8080}"

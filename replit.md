# Amanah Trader on Replit

## Run

Start the existing application workflow:

```bash
bash backend/replit_start.sh
```

The script installs the dependencies declared in `backend/requirements.txt` and
starts the combined FastAPI API and dashboard on port 8080.

## Preview paths

- Dashboard: `/dashboard/`
- Health check: `/health`

The root path (`/`) returns the API status document.

## Default safety state

The imported project starts in paper-trading approval mode. Broker submission
and paper execution are disabled until the project's own configuration enables
them.
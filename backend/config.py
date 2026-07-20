"""Local configuration for the read-only/paper backend.

Credentials are loaded from backend/.env and are never printed.
"""

from dataclasses import dataclass
from pathlib import Path
import os

BACKEND_DIR = Path(__file__).resolve().parent


def _load_local_env() -> None:
    """Load simple KEY=value entries without requiring a third-party package."""
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()


@dataclass(frozen=True)
class Settings:
    tiingo_api_token: str | None
    zoya_api_key: str | None
    zoya_environment: str
    shariah_universe_path: str | None
    shariah_wiki_path: str | None
    moomoo_mode: str
    moomoo_host: str
    moomoo_port: int


def load_settings() -> Settings:
    mode = os.getenv("MOOMOO_MODE", "paper").strip().lower()
    if mode != "paper":
        raise ValueError("MOOMOO_MODE must remain 'paper'; live mode is disabled")

    try:
        port = int(os.getenv("MOOMOO_PORT", "11111"))
    except ValueError as exc:
        raise ValueError("MOOMOO_PORT must be an integer") from exc

    return Settings(
        tiingo_api_token=os.getenv("TIINGO_API_TOKEN") or None,
        zoya_api_key=os.getenv("ZOYA_API_KEY") or None,
        zoya_environment=os.getenv("ZOYA_ENVIRONMENT", "sandbox").strip().lower(),
        shariah_universe_path=os.getenv("SHARIAH_UNIVERSE_PATH") or None,
        shariah_wiki_path=os.getenv("SHARIAH_WIKI_PATH") or None,
        moomoo_mode=mode,
        moomoo_host=os.getenv("MOOMOO_HOST", "127.0.0.1"),
        moomoo_port=port,
    )

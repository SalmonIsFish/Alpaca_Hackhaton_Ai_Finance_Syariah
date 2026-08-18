"""Verify check_moomoo_status fails fast when OpenD isn't listening.

Without this pre-check, the moomoo SDK's own connection retry/backoff runs
for minutes against a closed port -- this is what made the dashboard's
status refresh (and test_local_api_smoke.py) hang. A closed local port
should return "unreachable" in well under a second, not minutes.
"""

import os
import socket
import time

import moomoo_status


def find_unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def main() -> None:
    original_host = os.environ.get("MOOMOO_HOST")
    original_port = os.environ.get("MOOMOO_PORT")
    closed_port = find_unused_port()
    os.environ["MOOMOO_HOST"] = "127.0.0.1"
    os.environ["MOOMOO_PORT"] = str(closed_port)
    try:
        started = time.monotonic()
        result = moomoo_status.check_moomoo_status()
        elapsed = time.monotonic() - started

        assert result["status"] == "unreachable", result
        assert result["paper_account_ready"] is False
        assert result["reason"] == "moomoo_opend_not_listening"
        # Generous upper bound -- this used to take minutes via the SDK's
        # own retry loop; a closed local port should fail in well under 5s.
        assert elapsed < 5, f"check_moomoo_status took {elapsed:.1f}s against a closed port"
    finally:
        if original_host is None:
            os.environ.pop("MOOMOO_HOST", None)
        else:
            os.environ["MOOMOO_HOST"] = original_host
        if original_port is None:
            os.environ.pop("MOOMOO_PORT", None)
        else:
            os.environ["MOOMOO_PORT"] = original_port

    print("PASS: check_moomoo_status fails fast against a closed port instead of hanging.")


if __name__ == "__main__":
    main()

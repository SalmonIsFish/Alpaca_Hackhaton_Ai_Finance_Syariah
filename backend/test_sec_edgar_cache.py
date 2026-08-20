"""Verify the temporary SEC EDGAR disk cache and request throttle.

The network is never touched: ``cached_fetch`` takes the fetch callable as an
argument, so every test here passes a counting fake and asserts on *how many
times it was called*, not on what came back. That is the whole point of the
shim -- a second screen of the same symbol must not reach SEC at all.

Each test gets its own temporary cache directory, so nothing here can read or
write ``backend/sec_edgar_cache/``.
"""

import tempfile
from pathlib import Path

import sec_edgar_cache
import sec_edgar_screen


OK = {"ok": True, "status_code": 200, "data": {"hello": "world"}}
NOT_FOUND = {"ok": False, "status_code": 404, "data": {}, "reason": "http_404"}
URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"


def counter(response):
    """A fetch callable that records how many times it was actually invoked."""
    calls = []

    def fetch():
        calls.append(1)
        return response

    return fetch, calls


def main() -> None:
    with tempfile.TemporaryDirectory() as raw:
        cache_dir = Path(raw)

        # ------------------------------------------------ cold call fetches once
        fetch, calls = counter(OK)
        first = sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        assert len(calls) == 1, calls
        assert first["data"] == {"hello": "world"}, first
        assert first["cache"] == "miss", first

        # --------------------------------------- second call inside TTL is a hit
        fetch, calls = counter(OK)
        second = sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        assert len(calls) == 0, "a cached URL must not reach SEC again"
        assert second["data"] == {"hello": "world"}, second
        assert second["ok"] is True, second
        assert second["cache"] == "hit", second

        # ------------------------------------------- an expired entry re-fetches
        fetch, calls = counter(OK)
        third = sec_edgar_cache.cached_fetch(
            URL, fetch, cache_dir=cache_dir, ttl_seconds=0.0001, now=_later
        )
        assert len(calls) == 1, "an entry older than the TTL must be re-fetched"
        assert third["cache"] == "miss", third

    # ------------------------------------------------- failures are never cached
    # A 404 or a transport error is a *transient* answer about SEC, not an answer
    # about the company. Caching it would freeze a symbol into ERROR for the whole
    # TTL, and the screen fails closed on ERROR -- so the symbol would look
    # non-compliant for a day because of one bad request.
    with tempfile.TemporaryDirectory() as raw:
        cache_dir = Path(raw)
        fetch, calls = counter(NOT_FOUND)
        sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        assert len(calls) == 1, calls
        fetch, calls = counter(NOT_FOUND)
        again = sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        assert len(calls) == 1, "a failed response must not be served from cache"
        assert again["ok"] is False, again
        assert list(cache_dir.glob("*.json")) == [], "nothing should be written for a failure"

    # --------------------------------- a live failure falls back to a stale entry
    # An intermittent 403 (SEC blocking a shared egress IP, a rate limit, ...) is
    # an answer about SEC's mood, not about the company. If we already have a real
    # prior answer on disk, serving it -- clearly marked stale -- beats failing the
    # whole screen closed and showing a judge an ERROR for a company we screened
    # successfully an hour ago.
    with tempfile.TemporaryDirectory() as raw:
        cache_dir = Path(raw)
        fetch, calls = counter(OK)
        sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        assert len(calls) == 1, calls

        # The entry is now older than a very short TTL, so the next call is a
        # live attempt -- which fails.
        fetch, calls = counter(NOT_FOUND)
        stale = sec_edgar_cache.cached_fetch(
            URL, fetch, cache_dir=cache_dir, ttl_seconds=0.0001, now=_later
        )
        assert len(calls) == 1, "an expired entry must still attempt a live fetch first"
        assert stale["ok"] is True, stale
        assert stale["data"] == {"hello": "world"}, stale
        assert stale["cache"] == "stale", stale
        assert stale["stale_age_hours"] > 0, stale
        assert stale["live_fetch_reason"] == "http_404", stale

        # Serving the stale entry must not touch it on disk -- its cached_at
        # stays the original write time, and no failure is written either.
        entry_files = list(cache_dir.glob("*.json"))
        assert len(entry_files) == 1, entry_files

    # ---------------------- a failure with nothing on disk still fails closed
    # No prior answer exists to fall back to, so this must behave exactly as
    # before: the raw failure, untouched.
    with tempfile.TemporaryDirectory() as raw:
        cache_dir = Path(raw)
        fetch, calls = counter(NOT_FOUND)
        no_fallback = sec_edgar_cache.cached_fetch(
            URL, fetch, cache_dir=cache_dir, ttl_seconds=3600
        )
        assert no_fallback["ok"] is False, no_fallback
        assert no_fallback["cache"] == "miss", no_fallback

    # --------------------------------------------------- ttl_seconds=0 disables
    with tempfile.TemporaryDirectory() as raw:
        cache_dir = Path(raw)
        for _ in range(2):
            fetch, calls = counter(OK)
            result = sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=0)
            assert len(calls) == 1, "ttl_seconds=0 must disable the cache entirely"
            assert result["cache"] == "disabled", result
        assert list(cache_dir.glob("*.json")) == [], "a disabled cache must not write"

    # ------------------------------------------- a corrupt cache file re-fetches
    # The shim must degrade to "slow but correct", never to an exception on the
    # screening path.
    with tempfile.TemporaryDirectory() as raw:
        cache_dir = Path(raw)
        fetch, calls = counter(OK)
        sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        entry = next(iter(cache_dir.glob("*.json")))
        entry.write_text("{ this is not json", encoding="utf-8")
        fetch, calls = counter(OK)
        recovered = sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        assert len(calls) == 1, "a corrupt cache entry must fall back to a live fetch"
        assert recovered["data"] == {"hello": "world"}, recovered

    # ------------------------------------------- distinct URLs are distinct keys
    with tempfile.TemporaryDirectory() as raw:
        cache_dir = Path(raw)
        other = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000019617.json"
        fetch, calls = counter(OK)
        sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        fetch, calls = counter(OK)
        sec_edgar_cache.cached_fetch(other, fetch, cache_dir=cache_dir, ttl_seconds=3600)
        assert len(calls) == 1, "a different URL must not read another URL's entry"
        assert len(list(cache_dir.glob("*.json"))) == 2

    # ------------------------------------------------------------- the throttle
    # SEC asks for no more than ~10 requests/second. Two back-to-back live
    # fetches must be separated by at least the configured interval.
    slept = []
    clock = [1000.0]

    def sleep(seconds):
        slept.append(seconds)
        clock[0] += seconds

    sec_edgar_cache.reset_throttle()
    sec_edgar_cache.throttle(min_interval_seconds=0.125, now=lambda: clock[0], sleep=sleep)
    assert slept == [], "the first request must not be delayed"
    sec_edgar_cache.throttle(min_interval_seconds=0.125, now=lambda: clock[0], sleep=sleep)
    assert len(slept) == 1 and abs(slept[0] - 0.125) < 1e-9, slept

    clock[0] += 10.0
    sec_edgar_cache.throttle(min_interval_seconds=0.125, now=lambda: clock[0], sleep=sleep)
    assert len(slept) == 1, "a request after the interval has elapsed must not sleep"
    sec_edgar_cache.reset_throttle()

    # ------------------------------------- a cache hit must not spend the budget
    # Throttling a hit would make repeated demo takes slow for no reason.
    with tempfile.TemporaryDirectory() as raw:
        cache_dir = Path(raw)
        throttled = []
        original = sec_edgar_cache.throttle
        sec_edgar_cache.throttle = lambda **kwargs: throttled.append(1)
        try:
            fetch, _ = counter(OK)
            sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
            assert len(throttled) == 1, "a live fetch must be throttled"
            fetch, _ = counter(OK)
            sec_edgar_cache.cached_fetch(URL, fetch, cache_dir=cache_dir, ttl_seconds=3600)
            assert len(throttled) == 1, "a cache hit must not be throttled"
        finally:
            sec_edgar_cache.throttle = original

    # ------------------------------- sec_request actually routes through the cache
    # The shim is worthless if it is never wired in. Screening the same symbol
    # twice must produce exactly one HTTP fetch -- which is what a demo re-take
    # does over and over.
    with tempfile.TemporaryDirectory() as raw:
        original_dir = sec_edgar_cache.CACHE_DIR
        original_fetch = sec_edgar_screen._sec_fetch
        sec_edgar_cache.CACHE_DIR = Path(raw)
        sec_edgar_cache.reset_throttle()
        fetches = []

        def fake_fetch(url):
            fetches.append(url)
            return {"ok": True, "status_code": 200, "data": {"cik": 320193}}

        sec_edgar_screen._sec_fetch = fake_fetch
        try:
            first = sec_edgar_screen.sec_request(URL)
            second = sec_edgar_screen.sec_request(URL)
            assert fetches == [URL], f"sec_request must fetch once, not {len(fetches)} times"
            assert first["data"] == {"cik": 320193}, first
            assert second["data"] == {"cik": 320193}, second
            assert second["ok"] is True, second
        finally:
            sec_edgar_screen._sec_fetch = original_fetch
            sec_edgar_cache.CACHE_DIR = original_dir
            sec_edgar_cache.reset_throttle()

    print(
        "PASS: sec_edgar_cache serves repeat screens from disk, never caches failures, and throttles live fetches."
    )


def _later() -> float:
    """A clock far enough ahead that any short TTL has expired."""
    import time

    return time.time() + 3600.0


if __name__ == "__main__":
    main()

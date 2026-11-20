"""
Shared, rate-limited access to the USPTO Open Data Portal (api.uspto.gov).

Every ODP request in this repo (CLI scripts, web app, ad hoc skill code) goes
through odp_get() so that the ODP limits hold machine-wide:

- One request in flight per API key: ODP blocks concurrent calls with the same
  key (HTTP 429). A cross-process file lock serializes requests across threads,
  CLI scripts and the web app on this machine.
- At least MIN_INTERVAL_S between requests: ODP allows 4-15 requests/second
  depending on call type; 0.3s (~3.3/s) stays under the lowest figure.
- HTTP 429 is retried with exponential backoff, then raised.

The limits are fixed constants with no override, by design.

Usage:
    from odp_client import odp_get, odp_get_json
    data = odp_get_json("https://api.uspto.gov/api/v1/patent/applications/search",
                        api_key, params={"q": "...", "limit": 100})
"""

import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import fcntl
except ImportError:  # non-POSIX: fall back to an in-process lock only
    fcntl = None

MIN_INTERVAL_S = 0.3
MAX_429_RETRIES = 4
BACKOFF_BASE_S = 2.0
LOCK_PATH = os.path.join(tempfile.gettempdir(), "uspto-odp-client.lock")

_thread_lock = threading.Lock()


class _OdpLock:
    """Exclusive lock held for the whole request; the lock file stores the last request time."""

    def __enter__(self):
        if fcntl is None:
            _thread_lock.acquire()
            self._fh = None
            return self
        self._fh = open(LOCK_PATH, "a+")
        fcntl.flock(self._fh, fcntl.LOCK_EX)
        return self

    def last_request_time(self) -> float:
        if self._fh is None:
            return getattr(_OdpLock, "_last", 0.0)
        self._fh.seek(0)
        try:
            return float(self._fh.read().strip() or 0)
        except ValueError:
            return 0.0

    def mark_request_time(self) -> None:
        now = time.time()
        if self._fh is None:
            _OdpLock._last = now
            return
        self._fh.seek(0)
        self._fh.truncate()
        self._fh.write(str(now))
        self._fh.flush()

    def __exit__(self, *exc):
        if self._fh is None:
            _thread_lock.release()
        else:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
            self._fh.close()
        return False


def odp_get(url: str, api_key: str, params: dict | None = None, timeout: float = 30) -> bytes:
    """
    GET an ODP URL and return the response body.

    Raises urllib.error.HTTPError for non-2xx responses (including 404, which ODP
    uses for "zero results") after exhausting 429 retries. Redirects (e.g. signed
    document download URLs) are followed immediately within the same call.
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-Api-Key": api_key})
    for attempt in range(MAX_429_RETRIES + 1):
        with _OdpLock() as lock:
            wait = lock.last_request_time() + MIN_INTERVAL_S - time.time()
            if wait > 0:
                time.sleep(wait)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == MAX_429_RETRIES:
                    raise
            finally:
                lock.mark_request_time()
        time.sleep(BACKOFF_BASE_S * (2 ** attempt))
    raise RuntimeError("unreachable")


def odp_get_json(url: str, api_key: str, params: dict | None = None, timeout: float = 30) -> dict:
    return json.loads(odp_get(url, api_key, params, timeout))

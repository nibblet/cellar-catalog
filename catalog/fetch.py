"""Polite fetcher: identifies itself, honours a per-host delay, caches to disk so re-runs never re-hit a site."""
from __future__ import annotations

import hashlib
import time
import urllib.request
from pathlib import Path

USER_AGENT = "CellarCatalog/0.1 (+https://github.com/nibblet/cellar-ios; catalog importer, contact paul.cobb@homevestors.com)"


class Fetcher:
    def __init__(self, cache_dir: Path, delay_seconds: float):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay_seconds
        self._last = 0.0

    def _path(self, url: str) -> Path:
        return self.cache_dir / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".html")

    def get(self, url: str, *, refresh: bool = False) -> str:
        p = self._path(url)
        if p.exists() and not refresh:
            return p.read_text(encoding="utf-8")
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", errors="replace")
        self._last = time.monotonic()
        p.write_text(body, encoding="utf-8")
        return body

"""Fetch every page a source lists into the cache. Safe to re-run; only misses hit the site.
usage: crawl.py <source> <cache dir>"""
import importlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher

src = importlib.import_module(f"catalog.sources.{sys.argv[1]}")
f = Fetcher(Path(sys.argv[2]), delay_seconds=getattr(src, "DELAY", 10))
urls = src.list_urls(f)
print(f"{len(urls)} URLs")
for i, u in enumerate(urls, 1):
    f.get(u)
    print(f"{i:3}/{len(urls)} {u}", flush=True)
print("done")

"""Fetch every Drew Estate product page into the cache. Safe to re-run; only misses hit the site."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog.fetch import Fetcher

cache = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cache/drewestate")
f = Fetcher(cache, delay_seconds=10)
sitemap = f.get("https://drewestate.com/products-sitemap.xml")
urls = sorted(set(re.findall(r"<loc>(https://drewestate\.com/products/[^<]+/)</loc>", sitemap)))
print(f"{len(urls)} product URLs")
for i, u in enumerate(urls, 1):
    f.get(u)
    print(f"{i:3}/{len(urls)} {u}", flush=True)
print("done")

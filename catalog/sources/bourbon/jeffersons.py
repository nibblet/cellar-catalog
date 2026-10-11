"""jeffersonsbourbon.com (Jefferson's Bourbon, Pernod Ricard USA). The host's Cloudflare rule returns 403 to the
importer's honest client (home, robots.txt, sitemaps), which we do not work around, so `crawl.py` cannot fill this
cache. With the owner's explicit approval (2026-10-11) the pages were READ BY HAND in the app's own browser pane
(a normal browser: every page loaded without any challenge; nothing was solved, spoofed or automated; 9 page loads
at human pace) and the main-content text of each product page was saved into the cache under the page's URL
(cache/jef). `Fetcher.get` serves cached text, so this module parses it like a crawled page; a re-read means
refreshing those files by hand the same way. The rebuilt site now states a proof in prose on two of the four
Essential Collection pages ("bottled at 88 proof"; "aged a minimum of 8 years and bottled at 96 proof"); Triple
Rye and Ocean state none (Ocean's page has no number at all) and the Limited Editions section lists no product
pages. The seeded Very Small Batch (82.3) and Reserve (90.2, 4 yr) are older labels; the Reserve page is the same
product slug now sold as the 8 Year, so the old row is renamed and corrected."""
from __future__ import annotations

import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Jefferson's"
DELAY = 6
SITEMAP = "https://jeffersonsbourbon.com/sitemap.xml"
IMAGE_PREFIX = "https://jeffersonsbourbon.com/"
CATALOG_FAMILIES = ["Jefferson's"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Kentucky Straight Bourbon Whiskey"
# slug → (expression, aliases, class)
REFILE = {
    "jeffersons-bourbon": ("Very Small Batch", ["Jefferson's Very Small Batch Bourbon", "Jefferson's Bourbon"], "Bourbon Whiskey"),
    "jeffersons-reserve": ("Reserve 8 Year Old", ["Jefferson's Reserve"], BOURBON),
    "jeffersons-rye": ("Triple Rye", [], "Blended Rye Whiskey"),
    "jeffersons-ocean-bourbon": ("Ocean Aged at Sea", ["Jefferson's Ocean"], BOURBON),
}
CORE = {"Very Small Batch", "Reserve 8 Year Old", "Triple Rye", "Ocean Aged at Sea"}
RARITY = [(r"ocean", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [f"https://jeffersonsbourbon.com/whiskeys/{slug}/" for slug in REFILE]


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[slug]
    name = f"Jefferson's {expression}"
    text = re.sub(r"\s+", " ", page)
    m = re.search(r"bottled at (\d{2,3}(?:\.\d+)?) proof", text, re.I)
    a = re.search(r"aged a minimum of (\d+) years", text, re.I)
    years, label = age(a.group(0)) if a else (None, None)
    return BottlingRecord(
        brand_family="Jefferson's", expression=expression, name=name, source_url=url,
        proof=float(m.group(1)) if m else None, age_years=years, age_label=label, class_raw=class_raw,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )

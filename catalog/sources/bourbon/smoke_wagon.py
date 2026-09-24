"""smokewagon.com (Nevada H&C Distilling Co, Las Vegas — smokewagonwhiskey.com is a parked domain, not
the maker). A Wix site with almost no numeric data: only Small Batch states a proof ("even at 100
proof"); Straight Bourbon and the Rye page (the live one is at /copy-of-smoke-wagon-rye — the plain
/rye URL the old sitemap still lists is Wix's own retired "Old first version" of that page) describe
mash bills and blending philosophy with no proof at all; Uncut Unfiltered gives a floor, not a number
("115-116 plus proof"). Silver Dollar is a vodka, not whiskey, and is not crawled. A bottle photo, where
one exists, is the first `<img alt="Smoke Wagon ...">` on the page; most pages have none."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Smoke Wagon"
DELAY = 6
SITEMAP = "https://www.smokewagon.com/pages-sitemap.xml"
IMAGE_PREFIX = "https://static.wixstatic.com/"
CATALOG_FAMILIES = ["Smoke Wagon"]
PRODUCER_BY_FAMILY = {}

# path → (expression, aliases).
REFILE = {
    "straight-bourbon": (None, ["Smoke Wagon Straight Bourbon"]),
    "small-batch": ("Small Batch", []),
    "uncut-unfiltered": ("Uncut Unfiltered", []),
    "copy-of-smoke-wagon-rye": ("Rye", ["Smoke Wagon Rye"]),
}
NOT_CORE = re.compile(r"uncut unfiltered", re.I)
RARITY = [(r"uncut unfiltered", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted({f"https://www.smokewagon.com/{p}" for p in REFILE})


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    path = urlparse(url).path.strip("/")
    if path not in REFILE:
        return None
    expression, aliases = REFILE[path]
    name = f"Smoke Wagon {expression}" if expression else "Smoke Wagon"
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    own = flat.split("| Nevada Distilling Company LLC")[0]
    m = re.search(r"\b(\d{2,3}(?:\.\d+)?)[- ]proof\b", own, re.I)
    pf = float(m.group(1)) if m and not re.search(r"\d{2,3}(?:\.\d+)?\s*(?:-|–|to)\s*\d{2,3}[- ]proof", own, re.I) else None
    years, label = age(own)
    rye = bool(re.search(r"\brye\b", name, re.I))
    class_raw = "Straight Rye Whiskey" if rye else "Straight Bourbon Whiskey"
    mash_raw = "; ".join(re.findall(r"mash bill (?:of|consisting of) ([^.]+)\.", own, re.I))
    im = re.search(r'src="([^"]+)"[^>]*alt="Smoke Wagon[^"]*"', page) or re.search(r'alt="Smoke Wagon[^"]*"[^>]*src="([^"]+)"', page)
    img = im.group(1) if im else None
    return BottlingRecord(
        brand_family="Smoke Wagon", expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=mash_raw or None, mash_style="high_rye" if "high rye" in own.lower() else None,
        description=_text(own[:600]), image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )

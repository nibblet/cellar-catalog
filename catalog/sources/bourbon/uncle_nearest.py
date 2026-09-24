"""unclenearest.com (Uncle Nearest, Inc., Shelbyville, TN). No product sitemap; the lineup is the site
nav. One WordPress page per bottling: the proof, where stated, is in prose ("bottled at 100 proof",
"is a 93-proof whiskey", "this 84-proof Tennessee whiskey"); Master Blend, Single Barrel and Single
Barrel Rye state only "cask strength" / "barrel strength" with no number. Uncut/Unfiltered Rye states
its age as "raised for at least four years" (the maker's own word for "aged"). The bottle shot is the
one image whose alt text starts "Bottle of" / "Bottle Image of"."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Uncle Nearest"
DELAY = 6
SITEMAP = "https://unclenearest.com/wp-sitemap.xml"  # no product sitemap; used only as IMAGE_PREFIX's fallback host
IMAGE_PREFIX = "https://unclenearest.com/"
CATALOG_FAMILIES = ["Uncle Nearest"]
PRODUCER_BY_FAMILY = {}

# slug → (expression, aliases, class hint).
REFILE = {
    "premium-aged-whiskey": ("1856", [], None),
    "1884-small-batch-whiskey": ("1884", [], None),
    "nearest-green-tennessee-whiskey": ("Nearest Green", [], "Tennessee Whiskey"),
    "master-blend": ("Master Blend Edition", [], None),
    "single-barrel-whiskey": ("Single Barrel", [], None),
    "single-barrel-rye-whiskey": ("Single Barrel Rye", [], "Straight Rye Whiskey"),
    "straight-rye-whiskey": ("Rye", [], "Straight Rye Whiskey"),
    "toasted-single-barrel-whiskey": ("Toasted Single Barrel", [], None),
    "uncut-unfiltered-straight-rye-whiskey": ("Uncut/Unfiltered Rye", ["Uncle Nearest Uncut Unfiltered Rye"], "Straight Rye Whiskey"),
}
NOT_CORE = re.compile(r"master blend|single barrel|toasted|uncut|nearest green$", re.I)
RARITY = [(r"toasted|uncut", "unicorn"), (r"master blend|single barrel", "lottery"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://unclenearest.com/{slug}/" for slug in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = urlparse(url).path.strip("/")
    if slug not in REFILE:
        return None
    expression, aliases, class_hint = REFILE[slug]
    name = f"Uncle Nearest {expression}"
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    own = (flat.split("| Cart| Whiskeys|", 1)[-1] or flat).split("DRINK HONORABLY")[0][:3000]
    pf = None
    m = re.search(r"\b(\d{2,3}(?:\.\d+)?)[- ]proof\b", own, re.I)
    if m and not re.search(r"(?:cask|barrel)[- ]strength", own[:m.start()][-60:], re.I):
        pf = float(m.group(1))
    years, label = age(own.replace("raised for", "aged for"))
    if years is None and label is None:
        years, label = age(name)
    rye = bool(re.search(r"\brye\b", expression, re.I))
    class_raw = class_hint or ("Straight Rye Whiskey" if rye else "Tennessee Whiskey")
    mash = "rye" if rye else None
    # The hero bottle shot's file name always says "bottle"; the footer carries a shared "footer-bottles.png".
    tags = re.findall(r"<img[^>]+>", page)
    img = next((g.group(1) for t in tags if (g := re.search(r'src="([^"]+)"', t)) and re.search(r"bottle", g.group(1), re.I) and "footer-bottles" not in g.group(1)), None) \
        or next((g.group(1) for t in tags if re.search(r'alt="Bottle of', t) and (g := re.search(r'src="([^"]+)"', t))), None)
    desc = _text((re.search(r"Whiskey\| ([^|]{40,500})", own) or [None, None])[1])
    return BottlingRecord(
        brand_family="Uncle Nearest", expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=mash, description=desc, image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )

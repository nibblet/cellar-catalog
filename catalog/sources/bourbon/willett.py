"""kentuckybourbonwhiskey.com — Willett Distillery (formerly willettdistillery.com, which now redirects
here; the Kentucky Bourbon Distillers legal name is the domain). One WordPress page per bottling under
/whiskey/<slug>/, each a `whiskeyPageImage` bottle shot, an "N% by volume | M Proof" line, a paragraph,
and one or two mash-bill blocks with a "N BARREL ENTRY PROOF" figure that is not the bottling proof. The
site hosts several of the family's historic brands on one domain — Rowan's Creek, Noah's Mill, Johnny
Drum, Pure Kentucky, Kentucky Vintage, Old Bardstown, Speakeasy — each its own family, same as the
Willett-labeled bottlings. The Family Estate small-batch blends and the Pot Still Reserve Cask Strength
state no proof ("to vary among batches")."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Willett"
DELAY = 6
SITEMAP = "https://www.kentuckybourbonwhiskey.com/whiskey-sitemap.xml"
IMAGE_PREFIX = "https://www.kentuckybourbonwhiskey.com/"
CATALOG_FAMILIES = ["Willett", "Old Bardstown", "Rowan's Creek", "Noah's Mill", "Johnny Drum", "Pure Kentucky", "Kentucky Vintage", "Speakeasy"]
PRODUCER_BY_FAMILY = {}

# slug → (family, expression, aliases). The family is the shelf brand, not always "Willett".
REFILE = {
    "kentucky-vintage": ("Kentucky Vintage", None, ["Willett Vintage Bourbon", "Vintage Bourbon", "Kentucky Vintage Bourbon"]),
    "old-bardstown-estate-bottled": ("Old Bardstown", "Estate Bottled", ["Old Bardstown Estate Bourbon", "Old Bardstown Estate Bottled Bourbon"]),
    "old-bardstown-90-proof": ("Old Bardstown", "90 Proof", []),
    "old-bardstown-bottled-in-bond": ("Old Bardstown", "Bottled in Bond", ["Old Bardstown Bottled in Bond Bourbon"]),
    "pure-kentucky": ("Pure Kentucky", None, ["Willett Pure Kentucky XO", "Pure Kentucky XO"]),
    "willett-wheat": ("Willett", "Wheat", []),
    "willett-pot-still-reserve": ("Willett", "Pot Still Reserve", []),
    "willett-pot-still-reserve-2": ("Speakeasy", None, []),  # the slug is a leftover; the page's own name is Speakeasy
    "willett-pot-still-reserve-3": ("Willett", "Pot Still Reserve Cask Strength", []),
    "noahs-mill": ("Noah's Mill", None, []),
    "rowans-creek": ("Rowan's Creek", None, []),
    "johnny-drum-private-stock": ("Johnny Drum", "Private Stock", ["Willett Johnny Drum Private Stock"]),
    "willett-family-estate": ("Willett", "Family Estate Small Batch 4 Year", []),
    "willett-family-estate-4-year-rye": ("Willett", "Family Estate Small Batch 4 Year Rye", []),
}
NOT_CORE = re.compile(r"cask strength|speakeasy|90 proof|family estate", re.I)
RARITY = [(r"speakeasy|family estate", "lottery"), (r"cask strength|90 proof|bottled in bond", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted({u for u in re.findall(r"<loc>(https://www\.kentuckybourbonwhiskey\.com/whiskey/[a-z0-9-]+/)</loc>", fetcher.get(SITEMAP))})


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    family, expression, aliases = REFILE[slug]
    name = f"{family} {expression}" if expression else family
    flat = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    flat = re.sub(r"\s+", " ", flat).replace("’", "'")
    flat = re.sub(r"(\|\s*)+", "| ", flat)
    own = flat.split("| Search| ", 1)[-1].split("| See the Full Collection")[0]
    # "125 BARREL ENTRY PROOF" is the mash bill's entry proof, not the bottling proof.
    m = re.search(r"\b(\d{2,3}(?:\.\d+)?) Proof\b", re.sub(r"\d{2,3}\s*BARREL ENTRY PROOF", "", own))
    pf = float(m.group(1)) if m else None
    desc = _text((re.search(r"Proof\| ([^|]+)", own) or [None, None])[1])
    years, label = age(name)
    rye = bool(re.search(r"\brye\b", name, re.I))
    class_raw = "Kentucky Straight Rye Whiskey" if rye else "Kentucky Straight Bourbon Whiskey"
    if expression == "Bottled in Bond":
        class_raw += " Bottled-in-Bond"
    mash = "rye" if rye else "wheated" if "Wheat" in name else None
    img = (re.search(r'<img src="([^"]+)" class="whiskeyPageImage"', page) or [None, None])[1]
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=mash, description=desc, image_url=html.unescape(img) if img else None,
        aliases=sorted(set(aliases) - {name}), is_core_range=not NOT_CORE.search(name),
    )

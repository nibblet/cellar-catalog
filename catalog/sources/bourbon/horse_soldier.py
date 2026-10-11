"""horsesoldierbourbon.com (Horse Soldier Bourbon — the brand of American Freedom Distillery, a veteran-owned
company that sources and blends its bourbon and has just opened Horse Soldier Farms in Somerset, KY). Shopify
store; the shop sells ~100 products (apparel, barware, sauces, a book) but only five are whiskey, found by the
site's own "Bourbon SKU" product type and its "Our Bourbon" nav (Straight, Small Batch, Barrel Strength) plus the
two limited releases. Everything else (tees, glassware, Rekker Rum, bundles) is merch or not whiskey and is not
crawled. Scope comes from the REFILE table, never from `product_type`.

Per page: the copy ends in a "Proof: 95° / 47.5% ABV" line (Straight 87, Small Batch 95, Liberty Edition 100) or
a structured "Mash: ... / Age: 10 YO / Proof: 120" block (Commander's Select VII). The Barrel Strength page
states NO proof in text: it is printed on the bottle label in the maker's own product photo
(HSB19073_BarrelStrengthStack.png — "60.75 ALC/VOL ... 121.5 PROOF", ABV x 2 agrees). That reading was made BY HAND
from the full-size photo (Shopify image id 43121065525463, the evidence) and is used only while that same
file is still on the cached page; if the maker swaps the photo the proof silently drops instead of going stale.
The standalone bottle render on the same page (reserve.webp) leaves the proof/ABV spots blank.
The flagship's age is the maker's own "small batches of 4 year old bourbon". Small Batch and Barrel Strength both
call themselves "wheated" in the copy; the mash-bill percentages are stated only for Commander's Select VII.
Not on the site (so left as seed, not flagged discontinued): a 87-proof "Single Barrel"."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Horse Soldier"
DELAY = 6
SITEMAP = "https://horsesoldierbourbon.com/sitemap.xml"
IMAGE_PREFIX = "https://horsesoldierbourbon.com/"
CATALOG_FAMILIES = ["Horse Soldier"]
PRODUCER_BY_FAMILY = {}

STRAIGHT = "Straight Bourbon Whiskey"
# handle → (expression, aliases, class_raw)
REFILE = {
    "straight-bourbon-whiskey": (None, ["Horse Soldier Straight Bourbon", "Horse Soldier Premium Straight Bourbon", "Horse Soldier Straight Bourbon Whiskey"], STRAIGHT),
    "small-batch-bourbon-whiskey": ("Small Batch", ["Horse Soldier Signature Small Batch", "Horse Soldier Premium Small Batch Bourbon"], STRAIGHT),
    "barrel-strength-straight-bourbon-whiskey": ("Barrel Strength", ["Horse Soldier Reserve Barrel Strength", "Horse Soldier Reserve"], STRAIGHT),
    "commanders-select-vii-horse-soldier-bourbon": ("Commander's Select VII", ["Horse Soldier Commanders Select VII"], "Bourbon Whiskey"),
    "liberty-edition-horse-soldier-bourbon": ("Liberty Edition", [], "Kentucky Straight Bourbon Whiskey"),
}
CORE = {None, "Small Batch", "Barrel Strength"}
RARITY = [(r"liberty|commander", "limited"), (r".", "shelf")]
MASH_BILLS = {}

# Proof printed on the bottle label of the maker's own photo, read by hand: handle → (image file name, proof as pictured).
LABEL_PROOF = {
    "barrel-strength-straight-bourbon-whiskey": ("HSB19073_BarrelStrengthStack", 121.5),
}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://horsesoldierbourbon.com/products/{h}" for h in REFILE)


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1]
    if handle not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[handle]
    name = f"Horse Soldier {expression}" if expression else "Horse Soldier"
    flat = _flatten(page)
    # The product's own copy: after the buy box, before the share links. The nav and footer name every
    # bottling and the home page's carousel quotes other products' numbers.
    start = flat.find("Quantity must be 1 or more")
    end = flat.find("| Share|", start)
    own = flat[start:end] if start >= 0 and end > start else ""

    proof = None
    pm = re.search(r"Proof:\s*\|?\s*(\d{2,3}(?:\.\d+)?)", own)
    if pm:
        proof = float(pm.group(1))
    elif handle in LABEL_PROOF and LABEL_PROOF[handle][0] in page:
        proof = LABEL_PROOF[handle][1]

    years, label = age(own)
    am = re.search(r"Age:\s*(\d{1,2})\s*(?:YO|yr|year)", own, re.I)  # the structured field beats a "laid down 10 years ago"
    if am:
        years, label = float(am.group(1)), f"{am.group(1)} yr"

    mm = re.search(r"Mash:\s*([^|]+?)\s*(?:\||$)", own)
    mash_raw = mm.group(1) if mm else None

    style = "wheated" if re.search(r"[\"“”]wheated[\"“”] bourbon", own, re.I) else None  # the copy's own word, for the two pages with no percentages

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    if img and img.startswith("http://"):
        img = "https://" + img[7:]
    desc = own.split("Quantity must be 1 or more", 1)[-1]
    desc = re.sub(r"^\W*(Sold out|Add to cart.*?Update)\W*", "", desc, flags=re.S).replace("|", " ")
    desc = re.sub(r"\s+", " ", desc).strip()[:600] or None

    return BottlingRecord(
        brand_family="Horse Soldier", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw, mash_style=style, description=desc,
        image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}),
        is_core_range=expression in CORE,
    )

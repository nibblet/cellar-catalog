"""copperandkings.com (Copper & Kings American Brandy Co., Louisville — a brandy distillery that finishes
purchased Kentucky straight bourbon in its brandy barrels; brandy, absinthe and gin are out of scope).
WordPress + a Shopify buy-button: the WP product post carries the copy and the bottle photo, the
"Loading product…" widget is client-side only (price, variants). `wp-sitemap-posts-product-1.xml` lists
every product; only two are whiskey — `kentucky-straight-bourbon` and `kings-proof-bourbon`; the rest are
brandy, bundles, a club membership. The bourbon page is the **2-pack** SKU of the flagship ("Blend of
Kentucky Straight Bourbons finished in Brandy Barrels (2-Pack)"): it states "Aged Blend of 5-17+ Years"
and no proof, so it lists the row without confirming it. King's Proof states "Bottled at 114.8 proof" and
a 5-to-15-year blend. Neither age is a single number (a blend's age range is a display label, never
`age_years`; the existing seed's 12 is not supported by the maker and is left untouched). "Blend of Kentucky
Straight Bourbons" is a component statement, not the label's class: the class is read as straight bourbon
(`spirit_type()` would otherwise see a blend, the same call Doc Swinson's makes for its blends of straight
bourbons). The product's bottle photo is the first `<div class="slide"><img>` in `.media-gallery`."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "Copper & Kings"
DELAY = 6
SITEMAP = "https://copperandkings.com/wp-sitemap.xml"
IMAGE_PREFIX = "https://copperandkings.com/"
CATALOG_FAMILIES = ["Copper & Kings"]
PRODUCER_BY_FAMILY = {}

# product handle → (expression, aliases). "Bourbon" is the row the catalog already holds ("Copper & Kings Bourbon").
REFILE = {
    "kentucky-straight-bourbon": ("Bourbon", []),
    "kings-proof-bourbon": ("King's Proof", ["Copper & Kings King's Proof Bourbon", "Copper & Kings Kings Proof"]),
}
CORE = {"Bourbon", "King's Proof"}
RARITY = [(r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return sorted(f"https://copperandkings.com/product/{h}/" for h in REFILE)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'")
    return re.sub(r"(\|\s*)+", "| ", t)


def parse(url: str, page: str) -> BottlingRecord | None:
    handle = url.rstrip("/").split("/")[-1]
    if handle not in REFILE:
        return None
    expression, aliases = REFILE[handle]
    name = f"Copper & Kings {expression}"
    own = _flatten(page)
    # The product's own copy: from "WHAT MAKES IT SPECIAL" to the next section ("FLAVOR"), never the site chrome or "More Spirits".
    cm = re.search(r"WHAT MAKES IT SPECIAL\|\s*(.*?)\|\s*FLAVOR", own)
    copy = cm.group(1) if cm else ""

    pm = re.search(r"(?:bottled at|at)\s+(\d{2,3}(?:\.\d+)?)\s*proof", copy, re.I) or re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", copy, re.I)
    proof = float(pm.group(1)) if pm else None

    # A blend's age range ("5-to-15 year old", "Aged Blend of 5-17+ Years") is a label, not a number.
    am = re.search(r"\b(\d{1,2})\s*(?:-\s*to\s*-|-|–|to)\s*(\d{1,2})(\+)?[- ]*years?", copy, re.I)
    age_label = f"{am.group(1)}–{am.group(2)}{am.group(3) or ''} yr" if am else None

    img = re.search(r'class="media-gallery">\s*<div class="slider"><div class="slide"><img src="([^"]+)"', page)
    image = html.unescape(img.group(1)) if img else None

    return BottlingRecord(
        brand_family="Copper & Kings", expression=expression, name=name,
        source_url=f"https://copperandkings.com/product/{handle}/", proof=proof, age_years=None, age_label=age_label,
        class_raw="Kentucky Straight Bourbon Whiskey", description=_text(copy)[:600] if copy else None,
        image_url=image, finish="Brandy Barrels", aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )

"""hkyoungbourbon.com (H.K. Young Bourbon Co., Hopkinsville KY — a non-distiller brand that buys Kentucky straight
bourbon, finishes it in Independent Stave Company toasted barrels and blends it; press names Bardstown Bourbon
Company and Green River as the sources, the site itself names Green River for the wheated). Showit site on
WordPress/Yoast, robots Crawl-delay 10 (honoured). The Yoast page sitemap lists only the home page, /shop and per-state
retailer pages; the product pages are linked from the nav, so URLS below is the nav (Toasted Barrel Blend →
/ourblends, Toasted Small Batch → /toasted-bourbon, Wheated Bourbon → /wheated-blend). /shop is crawled too: its
four cards corroborate every figure (Toasted Barrel Blend 117.4, Small Batch 91.4, Wheated 122.4) but is not parsed.

Three bottlings. Toasted Small Batch ("bottled at 91.4 proof", a "6-7 year" blend — a range, so a label only) and
Wheated Bourbon ("Bottled at 122.4 proof ... built on a 7-year-old Kentucky Straight Bourbon foundation") state
their proof in prose. Toasted Barrel Blend is one page for every batch, oldest first (#1 Gambit 116.6, #2 Panacea
116.6, #3 From Georgia, With Love 114.4, #4 The Reckoning 117.4): the current bottling is the LAST batch block —
the opposite order from Barrell — and /shop's 117.4 agrees. Its age ("7 - 8 years" on /shop, component ages in the
batch notes) is a range, not a statement, and the page's "6yr 6mo / 7yr 7mo" are components, so no age is read from it.
Class is the label's "Kentucky Straight Bourbon Whiskey": the page calls the product "a blend of Kentucky straight
bourbon", which is bourbon blended with bourbon, never `blend` (High West rule). The finish is the brand's own toasted
oak. Not imported: the "Wheated Single Barrel" /shop card (a hand-picked Bourbon Bishop / Bourbon Papi barrel at
129.6 proof — a pick, not a bottling) and the single-barrel selection program."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "H.K. Young"
DELAY = 10
SITEMAP = "https://hkyoungbourbon.com/sitemap_index.xml"
IMAGE_PREFIX = "https://static.showit.co/"
CATALOG_FAMILIES = ["H.K. Young"]
PRODUCER_BY_FAMILY = {}

KSB = "Kentucky Straight Bourbon Whiskey"
# page slug → (expression, aliases, class)
REFILE = {
    "ourblends": ("Toasted Barrel Blend", ["H.K. Young Kentucky Straight Bourbon, Toasted Barrel Blend", "H.K. Young Toasted Blend"], KSB),
    "toasted-bourbon": ("Toasted Small Batch", [], KSB),
    "wheated-blend": ("Wheated Bourbon", ["H.K. Young Toasted Wheat Blend", "H.K. Young Wheated Barrel Blend"], KSB),
}
CORE = {"Toasted Barrel Blend", "Toasted Small Batch", "Wheated Bourbon"}
RARITY = [(r"wheated", "allocated"), (r"barrel blend", "allocated"), (r".", "shelf")]
MASH_BILLS = {}
FINISH = "Toasted Barrel"
EXTRA_URLS = ["https://hkyoungbourbon.com/shop"]  # corroboration only; parse() returns nothing for it


def list_urls(fetcher) -> list[str]:
    return [f"https://hkyoungbourbon.com/{slug}" for slug in REFILE] + EXTRA_URLS


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[slug]
    name = f"H.K. Young {expression}"
    flat = _flatten(page)
    # The nav and footer carry no figures; the product copy ends at the shop link (or the awards band on the blend page).
    own = flat.split("| Awards", 1)[0] if slug == "ourblends" else flat.split("| Shop All Products|", 1)[0]

    proof = years = label = None
    if slug == "ourblends":
        blocks = re.findall(r"(\d{2,3}\.\d)\| (\d{2}(?:\.\d+)?)%\| Alc", own)
        if blocks:  # batches run oldest first; the last block is the current bottling
            p, abv = blocks[-1]
            proof = float(p) if abs(float(p) - 2 * float(abv)) < 0.15 else None
    else:
        pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof(?:\s*\((\d{2}(?:\.\d+)?)% ABV\))?", own, re.I)
        if pm:
            proof = float(pm.group(1))
            if pm.group(2) and abs(proof - 2 * float(pm.group(2))) >= 0.15:
                proof = None  # the page contradicts itself; state nothing
        years, label = age(own)

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    desc = own.split("Toasted barrel | Blend|", 1)[-1] if slug == "ourblends" else own.split("| ABOUT US| home|", 2)[-1]
    desc = re.sub(r"\s+", " ", desc.replace("|", " ")).strip()[:600] or None

    return BottlingRecord(
        brand_family="H.K. Young", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, finish=FINISH, description=desc,
        image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}),
        is_core_range=expression in CORE,
    )

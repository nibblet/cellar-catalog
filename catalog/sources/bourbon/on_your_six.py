"""onyour6.com (On Your 6 Bourbon, "OY6" — the brand's own Shopify store). The brand is written "On Your 6" and "OY6" on
its site; the catalog files it as "On Your Six" and that spelling is kept (a family rename is a hygiene job, not an
importer's). The other domains that look right are not the maker: onyoursix.com 301s to battlesaint.com (no DNS),
onyoursixbourbon.com / onyoursix.us are GoDaddy parking pages ("/lander"), onyoursix.co is an unrelated security firm.
The store's footer and the Reg CF press release (invest.onyour6.com) tie the domain to the brand.

robots.txt is Shopify's template with no Crawl-delay (DELAY is the project's 6). Its comment block asks automated
shoppers to use a UCP/MCP checkout endpoint; that concerns buying, and nothing here touches a cart or checkout. No age
gate stands in front of the product page (the store serves it to any client).

The store sells ONE bottle (sitemap_products_1.xml: the bourbon, a gift card, and merchandise/BBQ sauce): /products/on-your-6-bourbon,
titled "On Your 6 Classic Bourbon". Its "Bourbon Specs" block states ALC/VOL 40%, PROOF 80, "AGED: Minimum 2 years",
"MASH BILL: 72% corn, 18% rye, 10% barley" and "BARREL ENTRY PROOF: 118".
- proof 80 is the bottling's statement (40% ALC/VOL agrees); barrel ENTRY proof 118 is not a bottling proof.
- "Minimum 2 years" is a floor, not an age statement (the owner's rule since 2026-10-12, as for Brother's Bond): no age
  is read and the seeded NAS stands. The seed's own curation specs say age_years 2; that is the floor read as an age.
- the page never says "straight" or names a distillery, so class_raw is "Bourbon Whiskey" (spirit type bourbon; nothing inferred).
The catalog row is "On Your Six Bourbon" (expression "Bourbon"); the module keeps that name (the maker's "On Your 6 Classic
Bourbon" and "On Your 6 Bourbon" are aliases for matching only) so no rename is written."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import mash_bill as _mash_bill, proof as parse_proof

PRODUCER = "On Your Six"
DELAY = 6
SITEMAP = "https://onyour6.com/sitemap.xml"
IMAGE_PREFIX = "https://onyour6.com/"
CATALOG_FAMILIES = ["On Your Six"]
PRODUCER_BY_FAMILY = {}

URL = "https://onyour6.com/products/on-your-6-bourbon"
RARITY = [(r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [URL]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    return re.sub(r"[\s|]*\|[\s|]*", " | ", re.sub(r"\s+", " ", t))


def parse(url: str, page: str) -> BottlingRecord | None:
    if url != URL:
        return None
    flat = _flat(page)
    m = re.search(r"The Bourbon Specs \|(.*?)(?: \| The Fine Print|$)", flat)
    if not m:
        return None
    spec = m.group(1)
    pm = re.search(r"\bPROOF: (\d{2,3}(?:\.\d+)?)\b", spec)
    proof = parse_proof(pm.group(1)) if pm else None
    mm = re.search(r"MASH BILL: (\d[^|]*?)(?= \| |$)", spec)
    mash_raw = mm.group(1).strip().rstrip(".") if mm else None
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    img = html.unescape(og.group(1)).replace("http://", "https://") if og else None
    # AGED: "Minimum 2 years" is a floor; BARREL ENTRY PROOF is not a bottling proof. Neither is read.
    return BottlingRecord(
        brand_family="On Your Six", expression=None, name="On Your Six Bourbon", source_url=url, proof=proof,
        age_years=None, age_label=None, class_raw="Bourbon Whiskey", mash_raw=mash_raw, image_url=img,
        aliases=["On Your 6 Classic Bourbon", "On Your 6 Bourbon"], is_core_range=True,
    )

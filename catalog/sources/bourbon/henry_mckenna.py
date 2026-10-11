"""Henry McKenna — heavenhilldistillery.com/henry-mckenna-single-barrel.php (Heaven Hill, Bardstown KY). henrymckenna.com
is a parked Hover domain (a placeholder page, port 443 times out, and no copy about the whiskey), and the brand has no
site of its own: Heaven Hill's "Our Brands" page links exactly one Henry McKenna bottle. heavenhilldistillery.com/henry-mckenna.php
returns 200 but is the site's generic shell (title only, no bottle block), so it is not read. The sitemap lists only the
single-barrel page. robots.txt is "Allow: /" with no Crawl-delay.

This is a separate module from heaven_hill.py on purpose (heaven_hill.py also lists this page; it is not edited here). The
page states, in its own "Proof: | 100 Proof | Age: | 10 Years Old" block, 100 proof and 10 years, and its copy calls it
Bottled-in-Bond. Its image is `images/brands/detail/mckena-4708.png`, the page's `brand-bottle` element.

The 80 proof "Henry McKenna Straight Bourbon" (Breaking Bourbon: "Heaven Hill's website doesn't feature Henry McKenna Straight
Bourbon in its brand lineup") has no maker page, so the flagship seed row cannot be confirmed here and shows as STALE;
it is not passed to --stale-only (absence from a brand page is not the maker saying it is discontinued)."""
from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof as parse_proof

PRODUCER = "Heaven Hill"
DELAY = 6
SITEMAP = "https://heavenhilldistillery.com/sitemap.xml"
IMAGE_PREFIX = "https://heavenhilldistillery.com/"
CATALOG_FAMILIES = ["Henry McKenna"]
PRODUCER_BY_FAMILY = {}

URL = "https://heavenhilldistillery.com/henry-mckenna-single-barrel.php"
RARITY = [(r"single barrel", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [URL]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    return re.sub(r"[\s|]*\|[\s|]*", " | ", re.sub(r"\s+", " ", t))


def parse(url: str, page: str) -> BottlingRecord | None:
    if url != URL:
        return None
    flat = _flat(page)
    pm = re.search(r"Proof: \| ([^|]+) \|", flat)
    proof = parse_proof(pm.group(1)) if pm and not re.search(r"varies", pm.group(1), re.I) else None
    am = re.search(r"Age: \| ([^|]+) \|", flat)
    years, label = age(am.group(1)) if am else (None, None)  # "10 Years Old"; the Bottled-in-Bond explainer's "four years" is outside this block
    img = None
    for tag in re.findall(r"<img[^>]+>", page):
        if "brand-bottle" in tag and (s := re.search(r'src="([^"]+)"', tag)) and "-mob" not in s.group(1):
            img = urljoin(URL, s.group(1).split("?")[0])
            break
    return BottlingRecord(
        brand_family="Henry McKenna", expression="Single Barrel", name="Henry McKenna Single Barrel", source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw="Kentucky Straight Bourbon Whiskey Bottled-in-Bond", image_url=img,
        aliases=["Henry McKenna Single Barrel, Bottled-in-Bond", "Henry McKenna 10 Year Bottled in Bond"], is_core_range=True,
    )

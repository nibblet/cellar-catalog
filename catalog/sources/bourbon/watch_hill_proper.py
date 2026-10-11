"""watchhillwhiskeyco.com (Watch Hill Whiskey Co., the whiskey brand of Watch Hill Proper, the Prospect, Kentucky bourbon
bar; watchhillwhiskey.com is a parked GoDaddy lander and watchhillproper.com is the bar's Squarespace site, which
links here). Shopify; robots.txt is the standard storefront file with no Crawl-delay, so DELAY is the project's usual 6.
Nothing is bought or checked out: the pages are plain public HTML. The shelf family is "Watch Hill Proper" (the seed
rows' family and the maker row), the bottles are Watch Hill Whiskey Co. releases in five series (Proper, Definitive,
Sandbox, Chef, Exceptional).

Each series is one page; there are no per-bottle pages, so the pages state the batches as a list:
- Exceptional Series: "The record so far | Batch 03 | Kentucky straight bourbon, 18 years old. Three barrel blend at
  128.0 proof. | Batch 02 ... 124.1 proof | Batch 01 ... 146.2 proof". Three one-off sell-out barrels; like Booker's, the
  highest-numbered batch is the row (Batch 03: 18 yr, 128.0, which is what the seed holds).
- Definitive Series: a new blend every month, "blended once and never repeated" (Batch 11 today: Kentucky Straight
  Bourbon, Single Barrel, 115 Proof, Aged 12 years). One row for the series, the latest batch supplying proof and age.
  This is a judgment call (the batches differ from each other, even in spirit type); remove the page from PAGES to drop it.
- Chef Series: the whiskey page states no figures, but the bar's own page (watchhillproper.com/whwc-1, linked from the bar's
  nav as Watch Hill Whiskey Co.) states "a blend of 12-year-old rye whiskeys ... a complex, memorable 130.4-proof whiskey" and
  "Straight Rye Whiskey - 12 Years Old" for Chef Series Batch 1. Same company (watchhillproper@kbmbrands.com), so it is the
  maker's page; that page's Exceptional proofs are the same except Batch 01 (146.15 vs 146.2) and are not used.
- Sandbox Series: names Honey Toasted Reserve as "the current release" and states no proof. The seeded 'Honey Toasted
  Reserve 2026 Release' carries a release label, which the matcher never claims, so it stays a seed.
- Proper Series: four planned expressions ("None of the four is available yet", Kentucky Straight Bourbon "110 proof ...
  coming soon"): not a bottle yet, not imported.

og:image on every page is one site-wide banner (the Four Grain lifestyle shot), so no image is taken."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Watch Hill Proper"
DELAY = 6
SITEMAP = "https://www.watchhillwhiskeyco.com/sitemap.xml"  # reference only; list_urls() names the series pages
IMAGE_PREFIX = "https://www.watchhillwhiskeyco.com/"
CATALOG_FAMILIES = ["Watch Hill Proper"]
PRODUCER_BY_FAMILY = {}

WC = "https://www.watchhillwhiskeyco.com/pages/"
EXCEPTIONAL = WC + "exceptional-series"
DEFINITIVE = WC + "definitive-series"
CHEF_WHISKEY = WC + "chef-series"
SANDBOX = WC + "sandbox-series"
CHEF_BAR = "https://www.watchhillproper.com/whwc-1"
URLS = [EXCEPTIONAL, DEFINITIVE, CHEF_WHISKEY, SANDBOX, CHEF_BAR]

# url → (expression, [catalog names it answers to])
PAGES = {
    EXCEPTIONAL: ("Exceptional Series", ["Watch Hill Exceptional Series (Batch 03)"]),
    DEFINITIVE: ("Definitive Series", []),
    CHEF_BAR: ("Chef Series Rye", ["Watch Hill Chef Series", "Watch Hill Whiskey Chef Series (Batch 01)"]),
}
CORE = set()
RARITY = [(r"exceptional", "allocated"), (r".", "limited")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return list(URLS)


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"(\|\s*)+", "| ", t)


def _batches(text: str) -> dict[int, str]:
    """'Batch 03| ...| Batch 02| ...' → {3: '...', 2: '...'} (the record section only)."""
    i = text.find("The record so far")
    j = text.find("The other series", i)
    block = text[i:j] if i >= 0 else ""
    parts = re.split(r"Batch (\d+)\|", block)
    return {int(parts[k]): parts[k + 1].strip(" |") for k in range(1, len(parts) - 1, 2)}


def parse(url: str, page: str) -> BottlingRecord | None:
    if url not in PAGES:
        return None
    expression, aliases = PAGES[url]
    name = "Watch Hill " + expression
    text = _flat(page)
    proof = years = label = None
    class_raw = None

    if url == EXCEPTIONAL:
        b = _batches(text)
        if not b:
            return None
        s = b[max(b)]  # "Kentucky straight bourbon, 18 years old. Three barrel blend at 128.0 proof."
        m = re.search(r"\bat (\d{2,3}(?:\.\d+)?) proof", s)
        proof = float(m.group(1)) if m else None
        years, label = age(s)
        class_raw = "Kentucky Straight Bourbon Whiskey" if re.search(r"straight bourbon", s, re.I) else None
    elif url == DEFINITIVE:
        b = _batches(text)
        if not b:
            return None
        s = b[max(b)]  # "Kentucky Straight Bourbon Whiskey, Single Barrel — 115 Proof| Aged 12 years"
        m = re.search(r"(\d{2,3}(?:\.\d+)?)\s+Proof", s)
        proof = float(m.group(1)) if m else None
        years, label = age(s.split("|", 1)[1] if "|" in s else "")
        cm = re.match(r"((?:Kentucky )?Straight (?:Bourbon|Rye) Whiskey)", s)
        class_raw = cm.group(1) if cm else None
    elif url == CHEF_BAR:
        i = text.find("Chef Series|")
        s = text[i:i + 900] if i >= 0 else ""
        m = re.search(r"(\d{2,3}(?:\.\d+)?)-proof", s)
        proof = float(m.group(1)) if m else None
        am = re.search(r"Chef Series Batch 1\|\s*(Straight Rye Whiskey - \d+ Years? Old)", s)
        if am:
            years, label = age(am.group(1))
            class_raw = "Straight Rye Whiskey"
    if class_raw is None:
        return None  # a page whose class statement did not read is left for a human

    return BottlingRecord(
        brand_family="Watch Hill Proper", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, image_url=None,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )

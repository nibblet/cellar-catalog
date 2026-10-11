"""IJW Whiskey Company (Louisville KY) — the catalog files Puncher's Chance under this family. IJW's own
site (ijwwhiskey.com) is a one-image "Website Coming Soon" holding page with no robots.txt and no
products, so it cannot be a source. Puncher's Chance is a brand of Wolf Spirit Distillery (Eugene, OR)
that buys its whiskey from IJW ("Crafted from sourced five- and six-year-old Kentucky Straight Bourbons
from IJW Whiskey Company"). The brand's own pages are therefore the maker's page for these rows:
puncherschancebourbon.com (WordPress, states the flagship's 90 proof and 75/13/12 mash bill in its home
copy, no product pages) and its shop, ourwolfspirit.com (Shopify), whose Puncher's Chance collection
carries ABV/proof, "Primary Grain" and "Production" lines in each product's description.

Crawled as one request: the collection's products.json (ourwolfspirit.com robots allows it; the brand
site asks a 10 s crawl delay, honoured). Each product's `body_html` has the spec block. Traps handled
here: (1) the flagship and the Undisputed describe their whiskey as "5- and 6-year-old" — an elliptical
component list that states two ages and no aggregate, so no age is read (the seed's 4 years stays
uncorrected; the maker says the youngest is 5); (2) the Left Cross is "Aged for 14 years" but also
mentions "12-year-old Jamaican rum casks" — the "aged" sentence wins, the finish is the rum casks;
(3) the Unified Belt is a bourbon + Irish whiskey + sherry-finished bourbon blend whose quoted mash bill
belongs to only one component, so it is a blend with no mash bill and no age; (4) the seed row named just
"Puncher's Chance" (14 yr, 96 proof) is the Left Cross — the only 14-year at 96 — so the Left Cross
aliases the bare brand name rather than the flagship, whose expression key would otherwise collide with
it ("puncherschance"), hence the flagship's expression stays None and it matches by name."""
from __future__ import annotations

import html
import json
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "IJW Whiskey Company"
DELAY = 10
SITEMAP = "https://ourwolfspirit.com/sitemap.xml"
IMAGE_PREFIX = "https://cdn.shopify.com/"
CATALOG_FAMILIES = ["IJW Whiskey Company"]
PRODUCER_BY_FAMILY = {}
FAMILY = "IJW Whiskey Company"
BRAND = "Puncher's Chance"

COLLECTION = "https://ourwolfspirit.com/collections/punchers-chance-bottles/products.json?limit=250"
PRODUCT = "https://ourwolfspirit.com/products/{}"

# handle → (expression, aliases, class statement, finish). expression None is the flagship (see module note).
REFILE = {
    "punchers-chance-kentucky-straight-bourbon-whiskey": (None, [], "Kentucky Straight Bourbon Whiskey", None),
    "punchers-chance-bourbon-the-undisputed": ("The Undisputed Single Barrel", [], "Kentucky Straight Bourbon Whiskey", None),
    "the-left-cross-14-year-old-rum-barrel-aged-bourbon": ("The Left Cross", ["Puncher's Chance"], "Kentucky Straight Bourbon Whiskey", "Jamaican Rum Casks"),
    "the-distance-12-year-tennessee-straight-bourbon": ("The D12TANCE", [], "Tennessee Straight Bourbon Whiskey", "California Cabernet Sauvignon Barrels"),
    "punchers-chance-bourbon-the-unified-belt": ("The Unified Belt", [], "Blended Whiskey", None),
}
CORE = {None, "The Undisputed Single Barrel"}
RARITY = [(r"left cross|d12tance", "allocated"), (r".", "shelf")]
MASH_BILLS = {}
NO_MASH = {"punchers-chance-bourbon-the-unified-belt"}  # a blend: the quoted recipe is one component's
NO_AGE = {"punchers-chance-bourbon-the-unified-belt"}   # four-year + four-year + fourteen-year components


def list_urls(fetcher) -> list[str]:
    return [COLLECTION]


def _text(fragment: str | None) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).replace("\xa0", " ").replace("’", "'")
    return re.sub(r"\s+", " ", t).strip()


def _own(body_html: str) -> str:
    """The product's own copy, cut before the shipping / third-party-retailer boilerplate."""
    t = _text(body_html)
    t = re.sub(r"^Description Details Availability & Shipping\s*", "", t)
    return re.split(r"Get FREE SHIPPING|Please be advised", t)[0].strip()


def _spec(body_html: str, label: str) -> str | None:
    t = _text(body_html)
    m = re.search(rf"{label}:\s*(.+?)(?=\s+(?:ABV|Made By|Origin|Primary Grain|Production|Please be advised)\b|$)", t)
    return m.group(1).strip() if m else None


# "5- and 6-year-old", "five- and six-year-old", "5 and 6-year": two component ages, no aggregate.
_COMPONENTS = re.compile(r"\b\w+-?\s+(?:and|&)\s+\w+[- ]year(?:s)?(?:[- ]old)?\b", re.I)


def parse(url: str, page: str) -> list[BottlingRecord] | None:
    if url != COLLECTION:
        return None
    out = []
    for p in json.loads(page).get("products", []):
        handle = p["handle"]
        if handle not in REFILE:
            continue
        expression, aliases, class_raw, finish = REFILE[handle]
        name = f"{BRAND} {expression}" if expression else f"{BRAND} Kentucky Straight"
        body = p.get("body_html") or ""
        own = _own(body)

        abv = _spec(body, "ABV") or ""
        pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", abv, re.I) or re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", own, re.I)
        proof = float(pm.group(1)) if pm else None

        grain = None if handle in NO_MASH else _spec(body, "Primary Grain")
        mash_raw = ", ".join(f"{pct}% {g.strip().title()}" for pct, g in re.findall(r"(\d+(?:\.\d+)?)\s*%\s*([A-Za-z]+)", grain)) if grain else None

        years = label = None
        if handle not in NO_AGE:
            years, label = age(_COMPONENTS.sub(" ", f"{p['title']}. {own}"))

        imgs = p.get("images") or []
        out.append(BottlingRecord(
            brand_family=FAMILY, expression=expression, name=name, source_url=PRODUCT.format(handle),
            proof=proof, age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash_raw,
            description=own[:600] or None, image_url=imgs[0]["src"] if imgs else None, finish=finish,
            aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
        ))
    return out

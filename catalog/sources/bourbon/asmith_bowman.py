"""asmithbowman.com (A. Smith Bowman Distillery, Fredericksburg VA — Sazerac-owned; WordPress + Avada +
WooCommerce, static HTML, robots allows everything with no Crawl-delay, Yoast sitemap_index.xml).

Three kinds of page, all stating proof in the same visible block ("N | PROOF | P% | ALC/VOL | NAME | descriptor")
and then repeating the whole block once more (a mobile/hidden copy, sometimes an OLDER copy: Gingerbread #2's
second block still says "Our Gingerbread Beer Finished Bourbon was released in 2013", Cask Strength's says
"141.1 proof" under a 144.5 headline, Twice Finished's says "Release No. 18" under "Release No. 19"). The FIRST block
is the current one; everything is read from it and the repeat is cut off.

* Brand pages (/bowman-brothers/, /isaac-bowman/, /john-j-bowman/, /cask-strength/) plus the WooCommerce product
  pages (/product/<slug>/), which carry the same proof and add the gift-shop price (msrp_usd). The product page is
  listed last, so it wins the dedupe.
* Abraham Bowman limited releases, one WordPress page each (Release No. 1 Rye through No. 21 Rum Finished). Every one
  states a proof; an age only when the prose gives a TOTAL ("At 18 years of age", "total age of this bourbon to 15
  years", "11 years and one month"). Multi-stage prose ("barrels aged four years ... then shipped to Potomac Point
  Winery"), component ages ("a 16-year-old bourbon ... and 14-year-old bourbon", Last Millennium) and barrel
  history ("originally aging Bowman Brothers Bourbon from 2004 to 2012") are not the bottling's age: AGE_RE names
  the one sentence per page that is, and a page without an entry states none.
* Lottery pages for the newer releases (Oak Series, Special Release #26 Rye, Cask Strength #2-#4): proof is in prose
  ("Bottled at 135 proof"); several state none (French Oak, Cask Strength 2024/2025) and are not crawled.

Traps: older Abraham pages declare their canonical/og:image on a stale host (alternatemail.asmithbowman.com) and one
site-wide Abraham image, so source_url is built from the slug here and the image is the page's own
"NN-A-Smith-Bowman-<release>.png"; /release-20-lottery/ is a byte-for-byte mirror of /gingerbread-2/ (same
timestamp) and is not listed; /rye-expectations/ and /cane-and-coffee/ answer 200 with "Product Unavailable"; page
titles on the 2024 lottery pages carry an editor's e-mail address (never stored). The Abraham numbering is the maker's
(#26 is the 2026 rye) but a page's own "Release No." is not trusted for identity (Twice Finished prints 19 then 18),
so expressions are named by what the release is.

Families follow the catalog's brand-per-family habit (Bowman Brothers, John J. Bowman, new Isaac Bowman); the Abraham
releases and the Cask Strength series stay in the seed's own 'A. Smith Bowman' family so the two existing Abraham rows
match in place instead of orphaning."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord

PRODUCER = "A. Smith Bowman"
DELAY = 6
SITEMAP = "https://asmithbowman.com/sitemap_index.xml"
IMAGE_PREFIX = "https://asmithbowman.com/"
CATALOG_FAMILIES = ["A. Smith Bowman", "Bowman Brothers", "John J. Bowman", "Isaac Bowman"]
PRODUCER_BY_FAMILY = {}

FAM = "A. Smith Bowman"
BOURBON = "Virginia Straight Bourbon Whiskey"

# slug → (family, expression, aliases, class_raw, finish, core, age regex or None)
# The age regex has one group and is searched in the page's own first block with "|" markup flattened.
_AB = lambda expr, aliases, cls, finish, age_re=None: (FAM, expr, aliases, cls, finish, False, age_re)  # noqa: E731
BRAND_PAGES = {
    "bowman-brothers": ("Bowman Brothers", "Small Batch", [], BOURBON, None, True, None),
    "isaac-bowman": ("Isaac Bowman", "Port Barrel Finished", [], BOURBON, "Port Barrel", True, None),
    "john-j-bowman": ("John J. Bowman", "Single Barrel", [], BOURBON, None, True, None),
    "cask-strength": (FAM, "Cask Strength", ["Limited Edition Cask Strength", "A. Smith Bowman Limited Edition Cask Strength",
                                             "A. Smith Bowman 10 Year Cask Strength"],
                      BOURBON, None, False, r"aged for (\d{1,2}) years"),
}
ABRAHAM_PAGES = {
    "rye-whiskey": _AB("Rye Whiskey", [], "Rye Whiskey", None),                                      # Release No. 1, 90 proof
    "bourbon-whiskey-2011": _AB("2011 Bourbon Whiskey", [], "Bourbon Whiskey", None, r"At (\d{1,2}) years of age"),
    "bourbon-whiskey-2012": _AB("2012 HazMat Bourbon Whiskey", ["Abraham Bowman 2012 Bourbon Whiskey"], "Bourbon Whiskey", None,
                                r"(\d{1,2})-year old bourbon"),
    "port-finished-bourbon-2012": _AB("Port Finished 2012", [], "Bourbon Whiskey", "Port Barrels"),
    "last-millennium-bourbon-whiskey": _AB("Last Millennium", [], "Bourbon Whiskey", None),
    "gingerbread-beer-finished-bourbon": _AB("Gingerbread Beer Finished", [], "Bourbon Whiskey", "Gingerbread Stout Barrels"),
    "port-finished-bourbon-2013": _AB("Port Finished 2013", ["Abraham Bowman Bourbon", "Abraham Bowman Port Finished"],
                                      "Bourbon Whiskey", "Port Barrels"),
    "double-barrel-bourbon": _AB("Double Barrel", [], "Bourbon Whiskey", None),
    "cider-finished-bourbon": _AB("Cider Finished", [], "Bourbon Whiskey", "Apple Cider Barrels"),
    "vanilla-bean-infused": _AB("Vanilla Bean Infused 24 Months", [], "Bourbon Whiskey", None),
    "coffee-finished-bourbon": _AB("Coffee Finished", [], "Bourbon Whiskey", "Coffee Barrels"),
    "high-rye-bourbon": _AB("High Rye", ["Abraham Bowman High Rye Bourbon"], "Bourbon Whiskey", None),
    "touriga-and-merlot-wine-finished-bourbon": _AB("Touriga & Merlot Wine Finished", [], "Bourbon Whiskey", "Touriga & Merlot Wine Barrels",
                                                    r"aging for[\s|]*(\d{1,2}) years"),
    "wheat-bourbon": _AB("Wheat", ["Abraham Bowman Wheat Bourbon"], "Bourbon Whiskey", None),
    "gingerbread-cocoa-finished-bourbon": _AB("Gingerbread Cocoa Finished", [], "Bourbon Whiskey", "Gingerbread Stout Barrels"),
    "sequential-2nd-use-barrels": _AB("Sequential Series 2nd Use Barrels", [], "Bourbon Whiskey", None),
    "sequential-4th-use-barrels": _AB("Sequential Series 4th Use Barrels", [], "Bourbon Whiskey", "Port Wine Barrels"),
    "sweet-xvi": _AB("Sweet XVI", [], "Bourbon Whiskey", None, r"After (\d{1,2}) years"),
    "bourbon-whiskey-2019": _AB("2019 Bourbon Whiskey", [], "Bourbon Whiskey", None),
    "twice-finished-whiskey-2019": _AB("Twice Finished", ["Abraham Bowman Twice Finished Whiskey"], "Whiskey", "Port And Sauternes Barrels",
                                       r"total age of this whiskey to (\d{1,2}) years"),
    "gingerbread-2": _AB("Gingerbread #2", [], "Bourbon Whiskey", "Gingerbread Stout Barrels", r"aged for (\d{1,2}) years"),
    "rum-finished-bourbon": _AB("Rum Finished", [], "Bourbon Whiskey", "Caribbean Rum Casks", r"total age of this bourbon to (\d{1,2}) years"),
}
# Newer releases announce themselves on the lottery page; proof (and age) are in prose, and a page that states
# none yields a proof-less record, which is listed but never added.
LOTTERY_PAGES = {
    "abraham-french-oak-lottery-2024": _AB("Oak Series: French Oak", [], "Bourbon Whiskey", "French Oak", r"aged for (\d{1,2}) years"),
    "abraham-american-oak-lottery-2024": _AB("Oak Series: American Oak", [], "Bourbon Whiskey", None),
    "abraham-hungarian-oak-lottery-2025": _AB("Oak Series: Hungarian Oak", [], "Bourbon Whiskey", None, r"aged for (\d{1,2}) years"),
    "abraham-rye-lottery-2026": _AB("Special Release #26 Rye Whiskey", [], "Rye Whiskey", None, r"aged for (\d{1,2}) years"),
}
# Read but not a bottling record of its own: the 2022 lottery page repeats /cask-strength/'s 10-year; the 2024 and
# 2025 cask strength lotteries (9-year; "#4") state no proof; /release-20-lottery/ mirrors /gingerbread-2/.
SHOP_PAGES = {"bowman-brothers", "isaac-bowman", "john-j-bowman"}  # /product/<slug>/ pages that add the price

REFILE = {**BRAND_PAGES, **ABRAHAM_PAGES, **LOTTERY_PAGES}
CORE = {"Small Batch", "Port Barrel Finished", "Single Barrel"}  # the maker's "core line of bourbons" (spirits page)
RARITY = [(r"oak series|cask strength|special release", "lottery"), (r"abraham", "allocated"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    urls = [f"https://asmithbowman.com/{s}/" for s in REFILE]
    urls += [f"https://asmithbowman.com/product/{s}/" for s in sorted(SHOP_PAGES)]
    return urls


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("’", "'").replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


PROOF_BLOCK = re.compile(r"(\d{2,3}(?:\.\d+)?)\|\s*PROOF\|")


def _first_block(own: str) -> str | None:
    """The page's own proof block, cut before the repeated copy."""
    m = PROOF_BLOCK.search(own)
    if not m:
        return None
    again = PROOF_BLOCK.search(own, m.end())
    return own[m.start(): again.start() if again else own.find("DAILY HOURS", m.end())]


def _slug(url: str) -> tuple[str, bool]:
    parts = url.rstrip("/").split("/")
    return parts[-1], parts[-2] == "product"


def parse(url: str, page: str) -> BottlingRecord | None:
    slug, shop = _slug(url)
    if slug not in REFILE or (shop and slug not in SHOP_PAGES):
        return None
    family, expression, aliases, class_raw, finish, core, age_re = REFILE[slug]
    own = _flat(page)
    lottery = slug in LOTTERY_PAGES

    msrp = None
    if shop:  # WooCommerce product page: "Shop| Bowman Brothers| $| 32.99| Virginia Straight Bourbon Whiskey| 750 ML| 90 Proof"
        pm = re.search(r"\$\|\s*(\d+(?:\.\d{2})?)\|", own)
        msrp = float(pm.group(1)) if pm else None
        sm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*Proof\b", own)
        proof = float(sm.group(1)) if sm else None
        scope = own
    elif lottery:
        scope = own.split("Event Rental| Shop|", 2)[-1].split("LOTTERY DETAILS", 1)[0]  # the release's own copy, before the lottery rules
        pm = re.search(r"Bottled at (\d{2,3}(?:\.\d+)?) proof", scope)
        proof = float(pm.group(1)) if pm else None
    else:
        scope = _first_block(own) or ""
        pm = PROOF_BLOCK.search(scope)
        proof = float(pm.group(1)) if pm else None  # "Varies | PROOF" (the umbrella Abraham page) has no number

    years = label = None
    if age_re:
        am = re.search(age_re, scope if not shop else own)
        if am:
            years = float(am.group(1))
            label = f"{int(years)} yr"

    brandlike = family != FAM
    name = f"{family} {expression}" if brandlike else (f"A. Smith Bowman {expression}" if slug == "cask-strength" else f"Abraham Bowman {expression}")

    img = None
    if shop or slug in BRAND_PAGES:
        im = re.search(r'property="og:image" content="([^"]+)"', page)
        img = im.group(1) if im else None
    elif not lottery:
        # "3-_-A-Smith-Bowman-_-Bourbon-Whiskey-HazMat.png" is spelled differently from its siblings, and WordPress also
        # lists "-500x915" resized copies: take the original.
        cands = re.findall(r'src="(https://asmithbowman\.com/wp-content/uploads/\d{4}/\d{2}/\d+-(?:_-)?A-Smith-Bowman-[^"]+\.(?:png|jpg))"', page)
        img = next((c for c in cands if not re.search(r"-\d+x\d+\.", c)), None)

    rye = "rye whiskey" in class_raw.lower()
    if shop:
        desc = None
    elif lottery:
        desc = _text(scope[:600])
    else:
        desc = _text(scope.split("ALC/VOL|", 1)[-1][:600])

    return BottlingRecord(
        brand_family=family, expression=expression, name=name,
        source_url=f"https://asmithbowman.com/{'product/' if shop else ''}{slug}/", proof=proof, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style=("rye" if rye else None), description=desc,
        image_url=html.unescape(img) if img else None, finish=finish, msrp_usd=msrp,
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE and family != FAM,
    )

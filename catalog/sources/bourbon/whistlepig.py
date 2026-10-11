"""whistlepigwhiskey.com (WhistlePig, Shoreham VT — a Webflow site; robots.txt allows everything and sets no
Crawl-delay). Two page families describe a bottle: `/whiskeys/<slug>` (marketing: hero tiles, tasting notes)
and `/product/<slug>` (the shop's page for the same bottle). The shop pages are the complete ones — every
product page ends its copy with the same tile row ("100 | Proof", "10 yrs | aged", "Bottled In Bond") and
a `/whiskeys` page can lack a tile the shop page has (the 18 Year's 86 proof is only on /product/), so the
bottle list is the shop pages. `/whiskeys/beyond-bonded-bourbon` has no shop page and is the one exception.

What each page states (read from the text between the price row and the footer):
  - proof: the "N | Proof" tile, else the first "N proof" / "N-proof" in the copy ("Hitting the bottle at
    92-proof"). PiggyBack Rye states 96.56, which the one-decimal column rounds to the seed's 96.6.
  - age: the "N yrs | aged" tile; Beyond Bonded Rye has none and says "aged at least 4 years and 29 days, and
    up to 4 years, 6 months" — the maker's floor, read as 4 by `normalize.age()`. FarmStock Rye's tile says
    "Aged | on the road" (no number) and its copy none, so it has no age.
  - mash bill: only PiggyBack Rye ("a mash bill of 100% Rye") and Beyond Bonded Rye ("Made with 100% Danko
    Rye"). The 18 Year's two pages disagree (/whiskeys: 91% rye / 9% malted barley; /product: 79 / 15 / 6), so
    it states none.

Not parsed, and why:
  - The Boss Hog collection (VI-XII) and Beyond Bonded Bourbon: single-barrel, bottled at proof, and the pages
    give a per-edition range ("bottled between 105.1 and 107.8 proof") or nothing — a range is not a proof.
    The Golden Pharaoh is parsed (proof-less) only so the seeded row reads as still listed.
  - Beyond Bonded Bourbon is Bottled in Bond (100 proof by law) but its page prints no proof and no age; the
    importer does not turn a legal category into a stated number, so it stays proof-less and is not inserted.
  - 3L formats (same whiskey in a size), the KFC Radio single-barrel pick, the Single Malts (no proof stated)
    and the PiggyBack pig-pour kits / barrel-aged maple syrup (not whiskey).
  - GraveStock is a Liquid Death collaboration (86 proof wheat whiskey); the seeded 'CampStock Wheat' is not
    claimed to be it — same strength, different name, no page tying them together.
The 18 Year is 'Double Malt Rye' on its page title and shop listing and 'Double Double Rye' in the nav; the
shop title is the name."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "WhistlePig"
DELAY = 6
SITEMAP = "https://www.whistlepigwhiskey.com/sitemap.xml"
IMAGE_PREFIX = "https://cdn.prod.website-files.com/"
CATALOG_FAMILIES = ["WhistlePig"]
PRODUCER_BY_FAMILY = {}
BASE = "https://www.whistlepigwhiskey.com/"

RYE = "Straight Rye Whiskey"
BOURBON = "Straight Bourbon Whiskey"
WHEAT = "Wheat Whiskey"
# path → (expression, aliases, class)
REFILE = {
    "product/piggyback-rye": ("PiggyBack 100% Rye", [], "Rye Whiskey"),
    "product/piggyback-bourbon": ("PiggyBack 100 Proof Bourbon", ["WhistlePig PiggyBack Bourbon"], "Small Batch Bourbon Whiskey"),
    "product/farmstock-rye": ("FarmStock Rye", ["WhistlePig FarmStock"], "Rye Whiskey"),
    "product/farmstock-beyond-bonded-rye": ("FarmStock Beyond Bonded Rye", ["WhistlePig Beyond Bonded Rye"], "Straight Rye Whiskey Bottled in Bond"),
    "product/whistlepig-10-years": ("Small Batch Rye Aged 10 Years", ["WhistlePig 10 Year", "WhistlePig 10 Year Small Batch Rye"], "Rye Whiskey"),
    "product/whistlepig-12-years": ("Old World Rye Aged 12 Years", ["WhistlePig 12 Year", "WhistlePig 12 Year Old World Rye"], "Rye Whiskey"),
    "product/whistlepig-15-years": ("Estate Oak Rye Aged 15 Years", ["WhistlePig 15 Year", "WhistlePig 15 Year Estate Oak Rye"], "Rye Whiskey"),
    "product/whistlepig-18-years": ("Double Malt Rye Aged 18 Years", ["WhistlePig 18 Year", "WhistlePig Double Double Rye Aged 18 Years", "WhistlePig 18 Year Double Malt Rye"], "Rye Whiskey"),
    "product/snout-to-tail-bourbon-aged-10-years": ("Snout-To-Tail Bourbon Aged 10 Years", ["WhistlePig Snout-to-Tail Bourbon - 10 Year"], BOURBON),
    "product/declaration-wheat-whiskey": ("Declaration Wheat Whiskey", [], WHEAT),
    "product/gravestock-wheat-whiskey": ("GraveStock Wheat Whiskey", [], WHEAT),
    "product/piggybank-rye-red-white-blue": ("PiggyBank Rye Red, White & Blue", ["WhistlePig Limited Edition PiggyBank Rye"], RYE),
    "product/piggybank-rye-gold-edition": ("PiggyBank Rye Gold Edition", ["WhistlePig Limited Edition PiggyBank Rye - Gold Edition"], RYE),
    "product/the-boss-hog-xiii-the-golden-pharaoh": ("The Boss Hog XIII: The Golden Pharaoh", ["WhistlePig The Boss Hog XIII: The Golden Pharaoh Rye"], RYE),
    "whiskeys/beyond-bonded-bourbon": ("FarmStock Beyond Bonded Bourbon", ["WhistlePig Beyond Bonded Bourbon"], "Straight Bourbon Whiskey Bottled in Bond"),
}
# What each page's copy states about the finish, where it states one.
FINISH = {
    "Old World Rye Aged 12 Years": "Madeira, Sauternes and Port Casks",
    "Estate Oak Rye Aged 15 Years": "Vermont Estate Oak",
}
MASH = {"PiggyBack 100% Rye": "100% Rye", "FarmStock Beyond Bonded Rye": "100% Danko Rye"}
CORE = {"PiggyBack 100% Rye", "PiggyBack 100 Proof Bourbon", "FarmStock Rye", "Small Batch Rye Aged 10 Years",
        "Old World Rye Aged 12 Years", "Estate Oak Rye Aged 15 Years", "Double Malt Rye Aged 18 Years",
        "Snout-To-Tail Bourbon Aged 10 Years"}
RARITY = [(r"boss hog", "allocated"), (r"piggybank|beyond bonded|declaration|gravestock|aged 18", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + path for path in REFILE]


def _flatten(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _own_copy(flat: str, path: str) -> str:
    """The bottle's own copy: a shop page runs from the price row to the footer, a marketing page from the
    'Back to all whiskeys' link to 'find a store' (cocktail recipes, awards and reviews follow)."""
    if path.startswith("product/"):
        part = flat.split("Back to Shop|", 1)[-1]
        part = re.sub(r"^[^|]*\|\s*\$\|\s*[\d.,]+\|\s*\d+\|\s*ml\|", "", part)  # title, price, size
        return part.split("| 𝕏|", 1)[0]
    part = flat.split("Back to all whiskeys|", 1)[-1]
    return part.split("find a store|", 1)[0]


def _text(fragment: str | None) -> str | None:
    t = re.sub(r"\s+", " ", (fragment or "").replace("|", " ")).strip()
    return t or None


def parse(url: str, page: str) -> BottlingRecord | None:
    path = url.replace(BASE, "").strip("/")
    if path not in REFILE:
        return None
    expression, aliases, class_raw = REFILE[path]
    name = f"WhistlePig {expression}"
    own = _own_copy(_flatten(page), path)

    tile = re.search(r"\|\s*(\d{2,3}(?:\.\d+)?)\|\s*Proof\|", own, re.I)
    prose = re.search(r"\b(\d{2,3}(?:\.\d+)?)[- ]proof\b", own, re.I)
    # A range ("bottled between 105.1 and 107.8 proof") states no proof and must never read as its upper end.
    ranged = re.search(r"between\s+\d{2,3}(?:\.\d+)?\s+and\s+\d{2,3}(?:\.\d+)?\s+proof", own, re.I)
    found = tile or (None if ranged else prose)
    proof = float(found.group(1)) if found else None
    if proof is None and path == "whiskeys/beyond-bonded-bourbon":
        proof = 100.0  # Bottled in Bond is 100 proof by law; the page prints none. Owner-approved reading, 2026-10-12.

    years, label = None, None
    am = re.search(r"(\d{1,2})\s*yrs?\s*\|?\s*aged", own, re.I)
    if am:
        years, label = float(am.group(1)), f"{am.group(1)} yr"
    elif path == "product/farmstock-beyond-bonded-rye":
        years, label = age(own)

    desc = _text(re.split(r"\|\s*(?:\d+%?\||\d+\s*yrs?|Aged\s*\||Single\||Wheat\||Small\||Bottled)", own, 1)[0])

    seg_start = page.find("Back to Shop")
    seg = page[max(0, seg_start - 2500): seg_start + 4000] if seg_start >= 0 else page
    img = None
    for src in re.findall(r'<img[^>]+src="(https://cdn\.prod\.website-files\.com/[^"]+?\.(?:png|jpg|jpeg|webp))"', seg):
        img = src
        break

    return BottlingRecord(
        brand_family="WhistlePig", expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=MASH.get(expression), description=desc,
        image_url=img, finish=FINISH.get(expression), aliases=sorted(set(aliases) - {name}),
        is_core_range=expression in CORE,
    )

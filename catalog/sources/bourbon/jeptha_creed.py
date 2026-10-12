"""jepthacreed.com (Jeptha Creed Distillery, Shelbyville KY — WordPress + WooCommerce, no JS needed; the
"are you 21" interstitial is a front-end overlay over a page the server sends in full, not a gate in
front of the content, and nothing here goes around it). Yoast product sitemap lists every SKU; the real
whiskey is a handful of pages among moonshine, flavored vodka, brandy, bitters, jam and merch.

Each product page prints "50% | 100 proof | $price" under its title, a MASHBILL block of "N% Grain" lines
(maker's own grain varietals: Bloody Butcher / Bruce's Blue / heirloom corn, malted rye, malted wheat,
malted barley), and tasting notes. Everything after "You're on a Roll Now" is a carousel of *other*
products (their proof, "6 Year Old Wheated Bourbon" in a pull-quote) and is cut off before reading.
Age is stated on exactly two pages: the Four Grain copy ("aged at least 4 years") and the 6 Year Wheated
title; the Solera page's "10 years of dedication" is an anniversary, not an age, so age is read only
from the title plus sentences that say "aged". Bottled-in-Bond states no age (the legal 4-year floor is
not an age statement). Single Barrel Reserve is a program page (three mash bills, no proof) and is not
crawled. The class is the page's own word, "Bourbon" — no page says "Straight". tasting_notes is the page's own
NOSE / PALATE / FINISH lines under the mash bill (SIGHT, the colour, is not read), read only after the "Try These Next" carousel is cut off."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Jeptha Creed"
DELAY = 6
SITEMAP = "https://jepthacreed.com/product-sitemap.xml"
IMAGE_PREFIX = "https://jepthacreed.com/"
# "Bruce's" is the catalog's family for Bruce's Blue Bourbon, a Jeptha Creed product (producer = Jeptha Creed).
CATALOG_FAMILIES = ["Jeptha Creed", "Bruce's"]
PRODUCER_BY_FAMILY = {}

# slug → (brand_family, expression, aliases). Aliases carry the family prefix, same as name.
REFILE = {
    "four-grain-bourbon": ("Jeptha Creed", "Four Grain", ["Jeptha Creed 4 Grain Corn", "Jeptha Creed Four Grain Bourbon"]),
    "bottled-in-bond-bourbon": ("Jeptha Creed", "Bottled-in-Bond", ["Jeptha Creed Bottled in Bond Rye Heavy", "Jeptha Creed Bottled-in-Bond Bourbon"]),
    "six-year-old-wheated-bourbon": ("Jeptha Creed", "6 Year Wheated", ["Jeptha Creed 6 Year Old Wheated Bourbon"]),
    "red-white-and-blue-bourbon": ("Jeptha Creed", "Red, White & Blue", ["Jeptha Creed Red, White & Blue Bourbon"]),
    "jeptha-creed-solera": ("Jeptha Creed", "Solera", ["Jeptha Creed Solera Bourbon"]),
    "bloody-butchers-creed-90-corn-bourbon": ("Jeptha Creed", "Bloody Butchers Creed 90% Corn", ["Jeptha Creed Bloody Butchers Creed 90% Corn Bourbon"]),
    "bruces-blue-bourbon": ("Bruce's", "Blue Bourbon", ["Bruce's Blue Bourbon"]),
}
# The four the site shelves under Craft Bourbon; the rest are Limited Editions.
CORE = {"Four Grain", "Bottled-in-Bond", "6 Year Wheated", "Red, White & Blue"}
RARITY = [(r"solera|bloody butchers|blue bourbon", "lottery"), (r"red, white", "allocated"), (r".", "shelf")]
MASH_BILLS = {}

URL = "https://jepthacreed.com/product/{}/"


def list_urls(fetcher) -> list[str]:
    return sorted(URL.format(s) for s in REFILE)


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


def _style(parts: list[tuple[float, str]]) -> str | None:
    """Mash percentages → the catalog's family, from the maker's stated recipe only."""
    g = {"corn": 0.0, "rye": 0.0, "wheat": 0.0, "barley": 0.0}
    for pct, grain in parts:
        gl = grain.lower()
        k = "rye" if "rye" in gl else "wheat" if "wheat" in gl else "barley" if "barley" in gl else "corn" if "corn" in gl else None
        if k:
            g[k] += pct
    if g["corn"] and g["rye"] and g["wheat"] and g["barley"]:
        return "four_grain"
    if g["wheat"] and not g["rye"]:
        return "wheated"
    if g["rye"]:
        return "high_rye" if g["rye"] >= 20 else "traditional"
    return "traditional" if g["corn"] else None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in REFILE:
        return None
    family, expression, aliases = REFILE[slug]
    name = f"{family} {expression}" if family == "Jeptha Creed" else "Bruce's Blue Bourbon"
    own = _flatten(page)
    own = own.split("You're on a Roll Now", 1)[0]  # the "Try These Next" carousel is other products
    head = own.split("Home| /| Spirits", 1)[-1]   # past the nav, which lists no proof

    pm = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", head, re.I)
    proof = float(pm.group(1)) if pm else None

    mm = re.search(r"MASHBILL\|\s*((?:\d+(?:\.\d+)?\s*%[^|]*\|\s*)+)", head)
    parts = [(float(p), g.strip()) for p, g in re.findall(r"(\d+(?:\.\d+)?)\s*%\s*([^|]+)", mm.group(1))] if mm else []
    mash_raw = ", ".join(f"{p:g}% {g}" for p, g in parts) or None

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    title = _text(h1.group(1)) or "" if h1 else ""
    aged = " ".join(s for s in re.split(r"(?<=[.!?])\s+|\|", head) if re.search(r"\baged\b", s, re.I))
    years, label = age(f"{title}. {aged}")

    img = (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    desc = _text(head.split("Tasting Notes", 1)[-1].split("MASHBILL", 1)[0][:600])

    nose, palate, finish = (re.search(r"\|\s*%s\|\s*([^|]+)" % k, own) for k in ("NOSE", "PALATE", "FINISH"))
    notes = " ".join(f"{k}: {m.group(1).strip()}" for k, m in (("Nose", nose), ("Palate", palate), ("Finish", finish)) if m) or None
    notes = notes[:900].rsplit(" ", 1)[0] if notes and len(notes) > 900 else notes

    return BottlingRecord(
        brand_family=family, expression=expression, name=name,
        source_url=URL.format(slug), proof=proof, age_years=years, age_label=label,
        class_raw="Bottled-in-Bond Bourbon" if slug == "bottled-in-bond-bourbon" else "Bourbon Whiskey",
        mash_raw=mash_raw, mash_style=_style(parts), description=desc,
        tasting_notes=notes, image_url=html.unescape(img) if img else None, aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )

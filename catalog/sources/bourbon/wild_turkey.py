"""Campari's Wild Turkey sites — wildturkeybourbon.com and russellsreserve.com (one WordPress theme). A
product page carries a schema.org Product (name, description; Russell's also the image), and the facts
in a PROCESS teaser ("101 proof aged between 6-8 years", "112.8 Barrel proof, 6-, 8-, and 12-year
blend") or the copy ("bottled at 90 proof"). Wild Turkey's page hero is a lifestyle shot; its bottle
shots come from the product sitemap's image entries. The Single Rickhouse page is whichever release is
current, named by its h1. American Honey is a liqueur and is skipped."""
from __future__ import annotations

import html
import json
import re
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof, titlecase

PRODUCER = "Wild Turkey"
DELAY = 5
SITEMAP = "https://www.wildturkeybourbon.com/product-sitemap.xml"
IMAGE_PREFIX = "https://www."
CATALOG_FAMILIES = ["Wild Turkey", "Russell's Reserve"]
SKIP = re.compile(r"american-honey|/en-us/|private-barrel", re.I)

SITEMAP_IMAGES: dict[str, str] = {}  # filled by list_urls: product name (upper) → bottle thumb from the products index

# slug → (family, expression, aliases). None = the flagship.
REFILE = {
    "wild-turkey-101": ("Wild Turkey", "101", ["Wild Turkey 101 Bourbon"]),
    "wild-turkey-bourbon": ("Wild Turkey", "Bourbon", ["Wild Turkey 81", "Wild Turkey Kentucky Straight Bourbon"]),
    "wild-turkey-101-rye": ("Wild Turkey", "101 Rye", ["Wild Turkey Rye 101"]),
    "wild-turkey-rye": ("Wild Turkey", "Rye", ["Wild Turkey 81 Rye"]),
    "kentucky-spirit": ("Wild Turkey", "Kentucky Spirit", ["Wild Turkey Kentucky Spirit Single Barrel"]),
    "rare-breed": ("Wild Turkey", "Rare Breed", ["Wild Turkey Rare Breed Barrel Proof"]),
    "rare-breed-rye": ("Wild Turkey", "Rare Breed Rye", []),
    "jimmys-70th-anniversary-bourbon": ("Wild Turkey", "Jimmy Russell 70th Anniversary", ["Wild Turkey Jimmy's 70th Anniversary"]),
    "10-year-old-bourbon": ("Russell's Reserve", "10 Year", ["Russell's Reserve 10 Year Old Bourbon"]),
    "6-year-old-rye": ("Russell's Reserve", "6 Year Rye", ["Russell's Reserve 6 Year Old Rye"]),
    "single-barrel-bourbon": ("Russell's Reserve", "Single Barrel", ["Russell's Reserve Single Barrel Bourbon"]),
    "single-barrel-rye": ("Russell's Reserve", "Single Barrel Rye", []),
    "13-year-old-bourbon": ("Russell's Reserve", "13 Year", []),
    "15-year-old-bourbon": ("Russell's Reserve", "15 Year", []),
    "single-rickhouse": ("Russell's Reserve", "Single Rickhouse", ["Russell's Reserve Single Rickhouse Camp Nelson E", "Russell's Reserve Single Rickhouse Collection"]),
}
NOT_CORE = re.compile(r"master's keep|anniversary|13 year|15 year|single rickhouse|generations|archives", re.I)
RARITY = [
    (r"master's keep|13 year|15 year|single rickhouse|anniversary", "lottery"),
    (r"kentucky spirit|rare breed rye|russell's reserve single barrel", "limited"),
    (r".", "shelf"),
]
MASH_BILLS = {}
PRODUCER_BY_FAMILY = {}


def list_urls(fetcher) -> list[str]:
    urls: set[str] = set()
    xml = fetcher.get(SITEMAP)
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        img = re.search(r"<image:loc>([^<]+)</image:loc>", block)
        if loc and re.search(r"/products/[^/]+/$", loc.group(1)):
            urls.add(loc.group(1))
    # Every product page shows its siblings' bottle thumbs with the sibling's name as alt text; once the
    # pages are cached, that is where each bottle's own shot comes from.
    for u in list(urls):
        p = fetcher._path(u)
        if p.exists():
            for tag in re.findall(r"<img[^>]+>", p.read_text(encoding="utf-8")):
                src = re.search(r'(?:data-imgsrc|src)="([^"]+/app/uploads/[^"]+)"', tag)
                alt = re.search(r'alt="([^"]+)"', tag)
                if src and alt and not re.search(r"logo|flag|_Detail|sour|cocktail", src.group(1), re.I):
                    SITEMAP_IMAGES.setdefault(html.unescape(alt.group(1)).replace("’", "'").upper().strip(), src.group(1))
    xml = fetcher.get("https://www.russellsreserve.com/page-sitemap.xml")
    urls |= {u for u in re.findall(r"<loc>(https://www\.russellsreserve\.com/our-products/[^/<]+/)</loc>", xml)}
    return sorted(u for u in urls if not SKIP.search(u))


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'").replace("®", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _product(page: str) -> dict | None:
    for m in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
        try:
            j = json.loads(m)
        except ValueError:
            continue
        for g in (j.get("@graph") or [j]):
            if isinstance(g, dict) and g.get("@type") == "Product":
                return g
    return None


def parse(url: str, page: str) -> BottlingRecord | None:
    host = urlparse(url).netloc
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    if slug in REFILE:
        family, expression, aliases = REFILE[slug]
    elif slug.startswith("masters-keep-"):  # each Master's Keep release keeps its name: "Master's Keep Voyage"
        family, expression, aliases = "Wild Turkey", "Master's Keep " + titlecase(slug[len("masters-keep-"):].replace("-", " ")), []
        if slug == "masters-keep-17-year":
            aliases = ["Wild Turkey Master's Keep"]  # the catalog's generic Master's Keep row is the 86.8-proof 17 Year
    else:
        return None  # a product this module does not know how to name
    prod = _product(page)
    name_raw = _text((prod or {}).get("name")) or _text((re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S) or [None, ""])[1])
    description = _text((prod or {}).get("description"))
    process = _text((re.search(r"<h3>PROCESS</h3>.*?<p>(.*?)</p>", page, re.S) or [None, ""])[1])
    h1 = _text((re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S) or [None, ""])[1])
    # Proof: the PROCESS line, a "Proof | 128" note, or the product's own copy up to the sibling teasers.
    own = html.unescape(re.sub(r"<[^>]+>", "|", re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)))
    own = re.sub(r"\s+", " ", own).replace("’", "'")
    own = re.split(r"See details|More to discover|AWARD WINNING|PREVIOUS SINGLE RICKHOUSE", own)[0]
    pf = proof(process) if process else None
    if pf is None:
        m = re.search(r"\bProof\|\s*\|?\s*(\d{2,3}(?:\.\d+)?)", own)
        pf = float(m.group(1)) if m else None
    if pf is None:
        copy = " ".join(x for x in (description, own[-6000:]) if x)
        if not re.search(r"\d{2,3}(?:\.\d+)?\s*(?:-|–|to|and)\s*\d{2,3}(?:\.\d+)?[- ]proof", copy, re.I):
            m = re.search(r"\b(\d{2,3}(?:\.\d+)?)[- ]proof\b|\bbottled at (?:a barrel proof of )?(\d{2,3}(?:\.\d+)?)", copy, re.I)
            pf = float(next(g for g in m.groups() if g)) if m else None
    # Age: the PROCESS line or the copy. A range, a blend of ages, or "up to" is a display label, not a number.
    years, label = None, None
    for text in (process or "", description or ""):
        rng = re.search(r"(?:aged )?(?:between )?(\d{1,2})\s*(?:-|–|to|and)\s*(\d{1,2})[- ]years?", text, re.I)
        blend = re.findall(r"(\d{1,2})-(?:,| and| &amp;| &)", text)
        upto = re.search(r"up to (\d{1,2}) years", text, re.I)
        if blend and len(blend) >= 2:
            last = re.search(r"(\d{1,2})-year", text)
            years, label = None, f"{blend[0]}–{last.group(1) if last else blend[-1]} yr"
            break
        if rng:
            years, label = None, f"{rng.group(1)}–{rng.group(2)} yr"
            break
        if upto:
            years, label = None, f"up to {upto.group(1)} yr"
            break
        years, label = age(text)
        if years:
            break
    if years is None and label is None and expression:
        years, label = age(expression)
    if slug == "single-rickhouse" and h1:
        aliases = sorted(set(aliases) | {f"Russell's Reserve {h1}"})
    name = f"{family} {expression}" if expression else family
    class_raw = "Kentucky Straight Rye Whiskey" if re.search(r"\brye\b", name, re.I) else "Kentucky Straight Bourbon Whiskey"
    if re.search(r"bottled in bond", name, re.I):
        class_raw += " Bottled-in-Bond"
    img = (prod or {}).get("image") or None
    if isinstance(img, list):
        img = img[0] if img else None
    if not img or re.search(r"slider|logo|detail-", img, re.I):
        img = SITEMAP_IMAGES.get((name_raw or "").upper()) or SITEMAP_IMAGES.get((h1 or "").upper()) or img
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf, age_years=years, age_label=label,
        class_raw=class_raw, mash_raw=None, mash_style="rye" if class_raw.startswith("Kentucky Straight Rye") else None,
        description=description, image_url=img or None,
        aliases=sorted({*aliases, *([titlecase(name_raw) if name_raw.isupper() else name_raw] if name_raw else [])} - {name}), is_core_range=not NOT_CORE.search(name),
    )

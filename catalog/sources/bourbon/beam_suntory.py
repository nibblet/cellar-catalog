"""Beam Suntory's brand sites — jimbeam.com, knobcreek.com, makersmark.com, basilhaydenbourbon.com and
beamdistilling.com (Baker's, Booker's, Little Book, Old Grand-Dad, Old Overholt, Hardin's Creek, Clermont
Steep). One Drupal platform: every bottling page carries a schema.org Product (name, description, bottle
image), most a "tasting-note" slider with a PROOF entry, and the rest state the proof in prose ("bottled
at 100 proof", "Now at 90-proof"). Age is stated in the product's own description or not at all; sibling
teasers on the page are ignored. Legent's site renders nothing server-side and is not covered."""
from __future__ import annotations

import html
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlparse

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof, titlecase

PRODUCER = "Jim Beam"
PRODUCER_BY_FAMILY = {"Maker's Mark": ("Maker's Mark", "4890088a-d33f-4212-b5a0-74326430f362"), "Star Hill Farm": ("Maker's Mark", "4890088a-d33f-4212-b5a0-74326430f362")}
DELAY = 5
SITEMAP = "https://www.jimbeam.com/sitemap.xml"  # one of five; list_urls reads them all
IMAGE_PREFIX = "https://www."
CATALOG_FAMILIES = ["Jim Beam", "Knob Creek", "Maker's Mark", "Basil Hayden", "Baker's", "Booker's", "Little Book", "Old Grand-Dad",
                    "Old Overholt", "Hardin's Creek", "Clermont Steep", "James B. Beam", "Legent", "Star Hill Farm", "Beam's Pin Bottle"]

# host → (family or None when the first path segment names it, product-path pattern, listing pages to
# harvest links from, slugs that are not a bottling)
SITES = {
    "www.jimbeam.com": ("Jim Beam", r"^/bourbons/[^/]+$", ["/bourbons"],
                        r"apple|peach|honey|kentucky-fire|red-stag|cooler|orange|vanilla|black-cherry|pineapple|^/bourbons/(flavors|ready-to-drink|premium|limited-edition|original)$"),
    "www.knobcreek.com": ("Knob Creek", r"^/whiskies/[^/]+$", ["/whiskies"], r"^/whiskies/(bourbon|rye)$"),
    "www.makersmark.com": ("Maker's Mark", r"^/(bourbons|whisky)/[^/]+$", ["/bourbons", "/limited-release-bourbons", "/premium-bourbons"],
                           r"global-travel|wood-finishing-series-collection$"),
    "www.basilhaydenbourbon.com": ("Basil Hayden", r"^/whiskies/[^/]+$", ["/", "/whiskies"], r"current-release|previous-releases"),
    "www.beamdistilling.com": (None, r"^/(bakers|bookersbourbon|littlebook|old-grand-dad-bourbon|old-overholt|hardins-creek|clermont-steep)/(whiskies|our-bourbons)/[^/]+$|^/bakers/bourbon$",
                               ["/bakers/bourbon", "/bookersbourbon/whiskies/current-batches", "/bookersbourbon/whiskies/previous-batches", "/littlebook/whiskies",
                                "/old-grand-dad-bourbon/our-bourbons", "/old-overholt/whiskies", "/hardins-creek/whiskies", "/clermont-steep"],
                               r"current-|previous-|past-releases|/(whiskies|our-bourbons)$|bookersbourbon/whiskies/20(1\d|2[0-2])-|excerpt"),  # old batches only add stale aliases
}
BD_FAMILIES = {"bakers": "Baker's", "bookersbourbon": "Booker's", "littlebook": "Little Book", "old-grand-dad-bourbon": "Old Grand-Dad",
               "old-overholt": "Old Overholt", "hardins-creek": "Hardin's Creek", "clermont-steep": "Clermont Steep"}

# What a product name starts with before the expression, longest first.
PREFIXES = {
    "Jim Beam": ["JIM BEAM"], "Knob Creek": ["KNOB CREEK"], "Maker's Mark": ["MAKER'S MARK", "MAKER'S"], "Basil Hayden": ["BASIL HAYDEN"],
    "Baker's": ["BAKER'S"], "Booker's": ["BOOKER'S"], "Little Book": ["LITTLE BOOK"], "Old Grand-Dad": ["OLD GRAND-DAD"],
    "Old Overholt": ["OLD OVERHOLT"], "Hardin's Creek": ["HARDIN'S CREEK"], "Clermont Steep": ["CLERMONT STEEP"],
}

# (host, page slug) → (family, expression, aliases the catalog may know it by). None = the flagship.
REFILE: dict = {
    ("www.jimbeam.com", "jim-beam"): ("Jim Beam", None, ["Jim Beam White Label", "Jim Beam White"]),
    ("www.jimbeam.com", "jim-beam-black"): ("Jim Beam", "Black", ["Jim Beam Black 7 Year", "Jim Beam Black Extra Aged"]),
    ("www.knobcreek.com", "9-year-old-single-barrel-reserve-bourbon-whiskey"): ("Knob Creek", "Single Barrel Reserve 9 Year", ["Knob Creek Single Barrel Select, 9 Year", "Knob Creek Single Barrel Reserve"]),
    ("www.knobcreek.com", "7-year-old-single-barrel-reserve-rye-whiskey"): ("Knob Creek", "Single Barrel Reserve Rye 7 Year", ["Knob Creek Single Barrel Rye"]),
    ("www.makersmark.com", "makers-mark"): ("Maker's Mark", None, []),
    ("www.makersmark.com", "makers-mark-46"): ("Maker's Mark", "46", ["Maker's 46", "Maker's Mark No. 46 French Oaked"]),
    ("www.makersmark.com", "makers-mark-wood-finishing-series"): ("Maker's Mark", "Wood Finishing Series", []),
    ("www.makersmark.com", "makers-mark-wood-finishing-series-bourbon-keepers-release"): ("Maker's Mark", "Wood Finishing Series", []),
    ("www.makersmark.com", "makers-mark-wood-finishing-series-bourbon-stewards-release"): ("Maker's Mark", "Wood Finishing Series", []),
    ("www.makersmark.com", "star-hill-farm-whisky"): ("Star Hill Farm", None, ["Star Hill Farm Whisky"]),
    ("www.basilhaydenbourbon.com", "basil-hayden-kentucky-straight-bourbon"): ("Basil Hayden", None, []),
    ("www.beamdistilling.com", "bakers-13-year-old-bourbon"): ("Baker's", "13 Year Single Barrel", ["Baker's 13 Year Limited Edition Single Barrel", "Baker's Single Barrel 13 Year"]),
    ("www.beamdistilling.com", "bourbon"): ("Baker's", "7 Year Single Barrel", ["Baker's Single Barrel 7 Year", "Baker's 7 Year"]),
    ("www.beamdistilling.com", "booker-the-reserves-2025"): ("Booker's", "The Reserves", []),
    ("www.beamdistilling.com", "bookers-the-reserves-limited-edition-bourbon"): ("Booker's", "The Reserves", []),
    ("www.beamdistilling.com", "old-grand-dad-bourbon-80proof"): ("Old Grand-Dad", None, ["Old Grand-Dad 80 Proof"]),
    ("www.beamdistilling.com", "old-grand-dad-bottled-in-bond"): ("Old Grand-Dad", "Bonded", ["Old Grand-Dad Bonded Bourbon", "Old Grand-Dad Bottled in Bond"]),
    ("www.beamdistilling.com", "old-overholt-original"): ("Old Overholt", None, ["Old Overholt Rye", "Old Overholt Straight Rye"]),
    ("www.beamdistilling.com", "old-overholt-bonded-rye"): ("Old Overholt", "Bonded", ["Old Overholt Bottled in Bond Rye", "Old Overholt Bonded Rye"]),
    ("www.beamdistilling.com", "a-overholt-monongahela-mash"): ("Old Overholt", "A. Overholt Monongahela Mash", ["A. Overholt Monongahela Mash Rye"]),
    ("www.beamdistilling.com", "clermont-steep-american-whiskey"): ("Clermont Steep", None, ["Clermont Steep American Single Malt"]),
    ("www.beamdistilling.com", "release-1-clermont"): ("Hardin's Creek", "Kentucky Series: Clermont", []),
    ("www.beamdistilling.com", "release-2-frankfort"): ("Hardin's Creek", "Kentucky Series: Frankfort", []),
    ("www.beamdistilling.com", "release-3-Boston"): ("Hardin's Creek", "Kentucky Series: Boston", []),
    ("www.beamdistilling.com", "release-1-the-mushroom"): ("Hardin's Creek", "Warehouse Series: Warehouse R The Mushroom", []),
    ("www.beamdistilling.com", "release-2-the-beaver"): ("Hardin's Creek", "Warehouse Series: Warehouse W The Beaver", []),
    ("www.beamdistilling.com", "release-3-the-owl"): ("Hardin's Creek", "Warehouse Series: Warehouse G The Owl", []),
    ("www.beamdistilling.com", "release-1-jacobs-well"): ("Hardin's Creek", "Jacob's Well", ["Hardin's Creek Jacob s Well"]),
    ("www.beamdistilling.com", "release-2-col-james-b-beam"): ("Hardin's Creek", "Colonel James B. Beam", ["Hardin's Creek Col. James B. Beam"]),
    ("www.beamdistilling.com", "little-book-the-infinite-edition"): ("Little Book", "The Infinite", ["Little Book The Infinite: Edition 1"]),
    ("www.beamdistilling.com", "little-book-the-infinite-edition-II"): ("Little Book", "The Infinite", ["Little Book Infinite Edition II"]),
    ("www.basilhaydenbourbon.com", "basil-hayden-two-by-two-rye-whiskey"): ("Basil Hayden", "Two by Two Rye", ["Basil Hayden Two by Two"]),
}
LITTLE_BOOK_CHAPTER = re.compile(r"^little-book-chapter-")  # every chapter is a release of the one Little Book bottling
# The label's class where the product name doesn't say (a blend is not a bourbon).
CLASS_BY_SLUG = {"basil-hayden-two-by-two-rye-whiskey": "Blend of Straight Whiskeys", "little-book-the-infinite-edition": "Blended Straight Whiskey",
                 "little-book-the-infinite-edition-II": "Blended Straight Whiskey", "jim-beam-sunshine-blended-bourbon": "Blended Bourbon Whiskey"}
FAMILY_CLASS = {"Little Book": "Blended Straight Whiskey", "Old Overholt": "Straight Rye Whiskey"}
CLASS_BY_SLUG["smoked-maple-bourbon-whiskey"] = "Flavored Whiskey"  # bourbon with natural flavors is not on the bourbon shelf
BOOKERS_BATCH = re.compile(r"^\d{4}-\d{2}-")  # every batch page is the one Booker's bottling; the batch lives on the bottle

NOT_CORE = re.compile(r"limited|anniversary|reserves|hardin's creek|little book|winter reserve|repeal batch|greats of the gate|wood finishing|cellar aged|"
                      r"private selection|cognac cask|13 year|16 year|18 year|21 year|blender's|cask strength rye|toast\b|star hill|caribbean|wildsam|subtle smoke|red wine", re.I)
RARITY = [
    (r"hardin's creek|little book|booker's the reserves|old grand-dad 16|knob creek (18|21)|baker's 13|cellar aged|greats of the gate|winter reserve|blender's", "lottery"),
    (r"booker's|wood finishing|private selection|cognac cask|knob creek (12 year cask|single barrel cask|15)|old overholt cask|a\. overholt|basil hayden 10|jim beam lineage|star hill", "allocated"),
    (r"limited|toast\b|repeal|old tub|single barrel reserve rye", "limited"),
    (r".", "shelf"),
]
# Named recipes these brands state; everything else is unknown unless the copy gives percentages.
MASH_BILLS = {}


def _links(page: str, host: str, pattern: str) -> set[str]:
    out = set()
    for href in re.findall(r'href="([^"#?]+)"', page):
        path = urlparse(href).path if href.startswith("http") else href
        if href.startswith("http") and urlparse(href).netloc != host:
            continue
        if re.search(pattern, path):
            out.add(f"https://{host}{path.rstrip('/')}")
    return out


def list_urls(fetcher) -> list[str]:
    urls: set[str] = set()
    for host, (_, pattern, indexes, skip) in SITES.items():
        xml = fetcher.get(f"https://{host}/sitemap.xml")
        for u in re.findall(r"<loc>(https://" + re.escape(host) + r"[^<]*)</loc>", xml):
            if re.search(pattern, urlparse(u).path):
                urls.add(u.rstrip("/"))
        for idx in indexes:  # brand sites list bottlings their sitemaps leave out
            try:
                urls |= _links(fetcher.get(f"https://{host}{idx}"), host, pattern)
            except HTTPError:
                pass  # a listing page that moved; the sitemap still carries the rest
        urls = {u for u in urls if not (urlparse(u).netloc == host and re.search(skip, urlparse(u).path))}
    return sorted(urls)


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'").replace("®", "").replace("™", "")
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


def _notes(page: str) -> dict[str, str]:
    """The tasting-note slider: {NOSE: ..., PROOF: '100', AGE: ...}."""
    out = {}
    for title, body in re.findall(r'class="tasting-note__title[^"]*">\s*(.*?)\s*</h3>\s*<div class="tasting-note__description">(.*?)</div>', page, re.S):
        out[_text(title).upper()] = _text(body) or ""
    return out


def parse(url: str, page: str) -> BottlingRecord | None:
    host, path = urlparse(url).netloc, urlparse(url).path
    slug = path.rstrip("/").split("/")[-1]
    prod = _product(page)
    h1 = _text(m.group(1)) if (m := re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)) else None
    name_raw = _text((prod or {}).get("name")) or h1
    if not name_raw or (prod is None and not BOOKERS_BATCH.search(slug)):
        return None
    family = SITES[host][0] or BD_FAMILIES.get(path.split("/")[1])
    if family is None:
        return None
    description = _text((prod or {}).get("description"))
    notes = _notes(page)
    text = " ".join(x for x in (name_raw, description, notes.get("AGE")) if x)
    # Proof: the PROOF note, else the product's own copy, else the brand footer when it names one strength.
    pf = proof(notes.get("PROOF"))
    if pf is None:
        copy = " ".join([description or "", _text(page[page.find("<main"):page.find("</main>")] or "") or ""])
        if re.search(r"\d{2,3}(?:\.\d+)?\s*(?:-|–|to|and)\s*\d{2,3}(?:\.\d+)?[- ]proof|proof\s+(?:is\s+)?\d{2,3}(?:\.\d+)?\s*(?:-|–|to|and)\s*\d{2,3}", copy, re.I):
            pf = None  # "108 to 114 proof": a range is not a statement
        else:
            m = re.search(r"(\d{2,3}(?:\.\d+)?)[- ]proof\b|\bproof (?:of the batch )?(?:is )?(\d{2,3}(?:\.\d+)?)\b|bottled at (\d{2,3}(?:\.\d+)?)", copy, re.I)
            pf = float(next(g for g in m.groups() if g)) if m else None
    if pf is None:
        footer = re.findall(r"(\d{2}(?:\.\d)?)\s*%\s*Alc", page)
        if len(set(footer)) == 1 and slug in {"jim-beam", "makers-mark", "basil-hayden-kentucky-straight-bourbon"}:
            pf = round(float(footer[0]) * 2, 1)  # the legal line is the flagship's statement
    years, label = age(text)
    if family == "Booker's" and BOOKERS_BATCH.search(slug):  # "The age of the batch is 7 years, 2 months" in the page copy
        m = re.search(r"(?:aged|age of the batch is)\s+(\d{1,2}) years?(?:,\s*(\d{1,2}) months?)?", _text(page[page.find("<main"):page.find("</main>")]) or "", re.I)
        years, label = (round(int(m.group(1)) + int(m.group(2) or 0) / 12, 2), f"{m.group(1)} yr {m.group(2)} mo" if m.group(2) else f"{m.group(1)} yr") if m else (None, None)

    if (host, slug) in REFILE:
        family, expression, aliases = REFILE[(host, slug)]
    elif family == "Booker's" and BOOKERS_BATCH.search(slug):
        family, expression, aliases = "Booker's", None, [f"Booker's {name_raw}"]
    elif family == "Little Book" and LITTLE_BOOK_CHAPTER.search(slug):
        family, expression, aliases = "Little Book", None, [name_raw]
    else:
        rest = re.sub(r"^LIMITED EDITION:?\s*", "", name_raw.upper())
        for pre in PREFIXES.get(family, []):
            if rest.startswith(pre):
                rest = rest[len(pre):]
                break
        rest = rest.strip(" -–—:,")
        rest = re.sub(r"\b(\d+)[- ]YEARS?[- ]OLD\b", r"\1 YEAR", rest)
        rest = re.sub(r"\b(\d+)\s+YEARS\b", r"\1 YEAR", rest)
        for _ in range(3):  # "Golden Rye Kentucky Straight Rye Whiskey" → "Golden Rye"
            rest = re.sub(r"\s*\b(KENTUCKY STRAIGHT (BOURBON|RYE MALT|RYE|MALT)( WHISKEY)?|(KENTUCKY )?BLENDED( WHISKEY)?|BOURBON WHISKEY|STRAIGHT BOURBON|BOURBON|WHISKEY|WHISKY)$", "", rest).strip()
        rest = re.sub(r"^KENTUCKY STRAIGHT$", "", rest).strip()
        expression = titlecase(rest) if rest else None
        aliases = []
    name = family if expression is None else f"{family} {expression}"
    class_raw = CLASS_BY_SLUG.get(slug) or FAMILY_CLASS.get(family) or (
                "Straight Rye Whiskey" if re.search(r"\brye\b", name_raw, re.I) and not re.search(r"bourbon", name_raw, re.I) else \
                "American Single Malt Whiskey" if re.search(r"single malt|clermont steep", name_raw, re.I) else \
                "Blended Whiskey" if re.search(r"blended|bourbon x rye", name_raw, re.I) else "Kentucky Straight Bourbon Whiskey")
    if re.search(r"smoked maple|with natural flavors", name_raw, re.I):
        class_raw = "Flavored Whiskey"  # bourbon with natural flavors is not on the bourbon shelf
    img = (prod or {}).get("image") or (re.search(r'property="og:image" content="([^"]+)"', page) or [None, None])[1]
    if isinstance(img, dict):
        img = img.get("url")
    mash = "high_rye" if re.search(r"high rye", name_raw, re.I) else ("rye" if class_raw.startswith("Straight Rye") else None)
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=pf,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=None, mash_style=mash,
        description=description, image_url=img.split("?")[0] if img and "/styles/" not in img else img,
        aliases=sorted({name_raw, *aliases} - {name}), is_core_range=not NOT_CORE.search(name),
    )

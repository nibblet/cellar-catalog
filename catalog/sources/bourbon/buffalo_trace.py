"""buffalotracedistillery.com — Sazerac's Frankfort distillery. Next.js site; one page per bottling at
/our-brands/<brand>/<expression>/, brand index pages one level up. Each bottling page carries a
brand_title, an h1 (the bottling, often with "AGED N YEARS"), a description_title (the class as
printed on most pages, a tagline on some), a Proof / Mash / Style block, a description and an
og:image bottle shot. No prices, and an age only where the label states one.

The family comes from the URL's brand slug, not the page's brand_title: the Antique Collection and
Kosher pages print the collection's name where the brand would be."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age, proof, spirit_type, titlecase

PRODUCER = "Buffalo Trace"
DELAY = 5
SITEMAP = "https://www.buffalotracedistillery.com/sitemap.xml"
IMAGE_PREFIX = "https://cms.buffalotracedistillery.com/"
# The catalog families this site speaks for (export.py pulls these plus every row with PRODUCER).
CATALOG_FAMILIES = ["Buffalo Trace", "Weller", "William Larue Weller", "Daniel Weller", "Eagle Rare", "Double Eagle Very Rare",
                    "Colonel E.H. Taylor", "Blanton's", "George T. Stagg", "Stagg", "Sazerac", "Thomas H. Handy", "Benchmark",
                    "Elmer T. Lee", "Old Charter", "Old Charter Oak", "Van Winkle", "Old Rip Van Winkle", "Pappy Van Winkle",
                    "Traveller", "Rock Hill Farms", "Hancock's", "Hancock's Reserve", "Ancient Age", "Prohibition", "Experimental Collection"]

# Brand pages that are not whiskey, or index pages with nothing to parse.
SKIP_BRANDS = {"clix", "wheatley", "freddies-old-fashioned-soda", "bourbon-cream", "white-dog", "o-f-c-vintages",
               "experimental-collection", "single-oak-project", "kosher-whiskey", "buffalo-trace-antique-collection"}

# URL brand slug → (catalog family, the ways the h1 spells the brand, longest first). A family of None
# means the h1 names the family itself (Van Winkle's three brands; the Prohibition Collection's revivals).
SLUGS = {
    "buffalo-trace": ("Buffalo Trace", ["BUFFALO TRACE"]),
    "w-l-weller": ("Weller", ["W.L. WELLER", "W. L. WELLER", "WELLER"]),
    "eagle-rare": ("Eagle Rare", ["EAGLE RARE"]),
    "e-h-taylor-jr": ("Colonel E.H. Taylor", ["COLONEL E.H. TAYLOR, JR.", "COLONEL E.H. TAYLOR", "E.H. TAYLOR, JR.", "E.H. TAYLOR, JR", "E.H. TAYLOR JR.", "E.H. TAYLOR"]),
    "blantons-single-barrel": ("Blanton's", ["BLANTON'S"]),
    "george-t-stagg": ("George T. Stagg", ["GEORGE T. STAGG"]),
    "sazerac-rye-whiskey": ("Sazerac", ["SAZERAC"]),  # the bar says "Sazerac Rye"; "Rye" stays in the expression
    "benchmark": ("Benchmark", ["BENCHMARK"]),
    "elmer-t-lee-single-barrel": ("Elmer T. Lee", ["ELMER T. LEE"]),
    "old-charter-oak": ("Old Charter Oak", ["OLD CHARTER OAK", "OLD CHARTER"]),
    "traveller": ("Traveller", ["TRAVELLER WHISKEY", "TRAVELLER"]),
    "van-winkle": (None, [("OLD RIP VAN WINKLE", "Old Rip Van Winkle"), ("PAPPY VAN WINKLE", "Pappy Van Winkle"), ("VAN WINKLE", "Van Winkle")]),
    "prohibition-collection-3": (None, []),
}

# Bottlings the site files under one brand that the catalog (and the bar) call by another name,
# keyed by the page's slug. (brand slug, expression slug) → (family, expression); None = the flagship.
REFILE = {
    ("george-t-stagg", "stagg-bourbon"): ("Stagg", None),
    ("george-t-stagg", "george-t-stagg-bourbon"): ("George T. Stagg", None),
    ("w-l-weller", "william-larue-weller"): ("William Larue Weller", None),
    ("w-l-weller", "daniel-weller"): ("Daniel Weller", None),
    ("w-l-weller", "w-l-weller-special-reserve-colorado"): ("Weller", "Special Reserve Colorado"),  # same h1 as Special Reserve
    ("sazerac-rye-whiskey", "thomas-h-handy-sazerac"): ("Thomas H. Handy", None),
    ("eagle-rare", "double-eagle-very-rare"): ("Double Eagle Very Rare", None),
    ("old-charter-oak", "old-charter-8"): ("Old Charter", "8"),
    ("blantons-single-barrel", "blantons-original-single-barrel"): ("Blanton's", "Single Barrel"),  # the bar orders "Blanton's"; the label says Original
    ("elmer-t-lee-single-barrel", "elmer-t-lee-single-barrel-bourbon"): ("Elmer T. Lee", None),  # one bottling; "Single Barrel" is the brand's subtitle
    ("traveller", "traveller-whiskey-blend-40"): ("Traveller", None),  # "Blend No. 40" is the flagship's batch name
    ("buffalo-trace", "kosher-whiskey-rye-recipe"): ("Buffalo Trace", "Kosher Rye Recipe"),
    ("buffalo-trace", "kosher-whiskey-wheat-recipe"): ("Buffalo Trace", "Kosher Wheat Recipe"),
    ("buffalo-trace", "kosher-whiskey-straight-rye"): ("Buffalo Trace", "Kosher Straight Rye"),
}

# Bottlings that are annual / one-off releases rather than an always-on lineup.
NOT_CORE = re.compile(r"antique collection|17 year|18 year|25 year|30 year|prohibition|o\.f\.c|experimental|old charter oak|"
                      r"single oak|warehouse c|tornado|marriage|distiller.s council|millennium|"
                      r"double eagle|william larue|thomas h\. handy|sazerac 18|george t\. stagg|pappy|van winkle|"
                      r"cured oak|seasoned wood|amaranth|four grain|old fashioned sour mash|colorado|kosher", re.I)

# How hard each bottling is to find, for rows this importer creates (matched rows keep theirs). First
# pattern that matches the bar-order name wins; nothing matched stays null and shows in the dry run.
RARITY = [
    (r"pappy van winkle 23|eagle rare (25|30)|double eagle|o\.f\.c", "unicorn"),
    (r"pappy|van winkle|william larue|thomas h\. handy|george t\. stagg|sazerac rye 18|eagle rare 17|taylor bottled in bond|18 year marriage|warehouse c|millennium|prohibition", "lottery"),
    (r"blanton's (gold|straight from)|eagle rare 12|elmer t\. lee|rock hill|hancock|weller (12|full proof|single barrel|c\.y\.p\.b|special reserve colorado)|taylor (single barrel|small batch|straight rye|barrel proof|amaranth|four grain|cured oak|seasoned wood|old fashioned|distiller|warehouse)|^stagg$|daniel weller|kosher", "allocated"),
    (r"old charter oak|experimental|single oak|blanton's special reserve|traveller full proof", "limited"),
    (r".", "shelf"),
]

# The site names its mash bills; these are the families they belong to. Unlisted names stay unknown.
MASH_BILLS = {"mash bill #1": "traditional", "mash bill #2": "traditional", "wheated": "wheated", "wheated mash": "wheated",
              "4 grain": "four_grain", "four grain": "four_grain"}  # "Rye Mash" on a bourbon page says nothing about the rye share


def list_urls(fetcher) -> list[str]:
    xml = fetcher.get(SITEMAP)
    urls = sorted(set(re.findall(r"<loc>(https://www\.buffalotracedistillery\.com/our-brands/[^/<]+/[^/<]+/)</loc>", xml)))
    return [u for u in urls if u.split("/")[4] not in SKIP_BRANDS]


def _text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ").replace("’", "'").replace("‘", "'")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _grab(page: str, pattern: str) -> str | None:
    m = re.search(pattern, page, re.S)
    return _text(m.group(1)) if m else None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.split("/")[4]
    brand_title = _grab(page, r'class="brand_title">(.*?)</div>')
    h1 = _grab(page, r"<h1[^>]*>(.*?)</h1>")
    if not h1 or not brand_title:
        return None  # a brand index page, or nothing published
    proof_raw = _grab(page, r'<div class="proof">(.*?)</div>\s*</div>') or ""
    pf = proof(proof_raw)
    uncut = bool(re.search(r"uncut|barrel proof", proof_raw, re.I))  # Thomas H. Handy prints "Uncut/Unfiltered" where the proof goes
    if pf is None and not uncut:
        return None  # merchandise, or a spirit the site lists without a proof
    description_title = _grab(page, r'class="description_title">(.*?)</div>')
    style_raw = _grab(page, r'class="style">(.*?)</div>')
    mash_raw = _grab(page, r'class="mash">(.*?)</div>')
    description = _grab(page, r'class="description">(.*?)</div>')
    og = re.search(r'property="og:image" content="([^"]+)"', page)
    # description_title is the class on most pages ("Kentucky Straight Bourbon Whiskey") and a tagline on
    # a few ("The World's First Single Barrel Bourbon"); the Style block always names the class.
    class_raw = description_title if spirit_type(description_title) or (description_title and re.search(r"liqueur|cream", description_title, re.I)) else style_raw
    if uncut:
        class_raw = f"{class_raw or ''} (Uncut/Unfiltered)".strip()

    hh = h1.upper().replace("’", "'")
    family, prefixes = SLUGS.get(slug, (None, []))
    if (slug, url.rstrip("/").split("/")[-1]) in REFILE:
        family, expression = REFILE[(slug, url.rstrip("/").split("/")[-1])]
        rest = ""
    else:
        rest = hh
        if family is None:
            for pre, fam in prefixes:
                if hh.startswith(pre):
                    family, rest = fam, hh[len(pre):]
                    break
            if family is None:  # the h1 is the brand (Prohibition Collection revivals)
                family, rest = titlecase(h1), ""
        else:
            for pre in prefixes + [brand_title.upper()]:
                if hh.startswith(pre):
                    rest = hh[len(pre):]
                    break
        rest = rest.strip(" -–—:,")
        rest = re.sub(r"^AGED\s+(\d+)\s+YEARS?$", r"\1 YEAR", rest)
        rest = re.sub(r"\b(\d+)[- ]YEARS?(?:[- ]OLD)?\b", r"\1 YEAR", rest)
        rest = re.sub(r"(?:^|\s+)(?:KENTUCKY STRAIGHT )?(?:BOURBON|WHISKEY|WHISKY)$", "", rest).strip()
        if re.fullmatch(r"\d{1,2}", rest):
            rest += " YEAR"  # "W.L. WELLER 12" is the 12 Year
        expression = titlecase(rest) if rest else None

    years, label = age(" ".join(x for x in (h1, description or "") if x))
    name = family if expression is None else f"{family} {expression}"
    aliases = {titlecase(h1)} if hh.startswith(brand_title.upper()) else {titlecase(h1), f"{titlecase(brand_title)} {titlecase(h1)}"}
    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url,
        proof=pf, age_years=years, age_label=label, class_raw=class_raw,
        mash_raw=mash_raw, mash_style=MASH_BILLS.get((mash_raw or "").lower()),
        style_raw=style_raw, description=description, image_url=og.group(1) if og else None,
        aliases=sorted(aliases - {name}),
        is_core_range=not (NOT_CORE.search(name) or "ANTIQUE COLLECTION" in brand_title.upper()),
    )

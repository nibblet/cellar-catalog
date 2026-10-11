"""stillaustin.com (Still Austin Whiskey Co., Austin, Texas; stillaustin.com 301s to www.stillaustin.com; a Webflow
site). robots.txt allows everything except /search, a few query forms and a handful of slugs ("/*straight-oated-bourbon",
"/*double-barreled-whiskey", ...), none of which is fetched here, and sets no Crawl-delay, so DELAY is the project's 6.
Every page opens with a "You are not old enough to visit this site | YES | NO" overlay in its static HTML; the product
copy is served regardless and nothing here clicks through it (Journeyman precedent).

The list is the site's "Our Spirits" nav: Straight Bourbon "The Musician", Straight Rye "The Artist", Cask Strength Rye,
Cask Strength Bourbon, American Gin (not whiskey, not fetched), Single Barrel Whiskey, Bottled in Bond, Tanager, Limited
Releases and Archive. The product pages have a spec tile ("Alc / Vol / Proof | 49.2% / 98.4" and a "Mashbill" block of
percentages); the Tanager page prints "53% ALC / VOL | 106 proof".

What is a row (decided here, so a re-run reproduces it):
  - Bottled in Bond is ONE seasonal series page listing four whiskeys by season, each with several releases on the page
    (Summer Red Corn Bourbon, Fall Straight Bourbon, Winter Blue Corn Bourbon, Spring Straight Rye): the four are four rows
    (the seed names are kept), each carrying the LAST listing's facts for that type - 100 proof (Bottled in Bond; every
    listing prints it) and the mash bill, which is the same across releases. They are seasonal limited releases, so none is core.
  - "AGED AT LEAST 6 YEARS" is a floor, not an age statement, and it changes every release (Red Corn: 6 in Summer 2025, 7 in
    Summer 2026): no age is read for any Bottled in Bond row. The seeded 6, 7, 6 and 4 yr are listed for the owner.
  - Cask Strength Bourbon: the product page says "bottled at a ... 116 proof" and its tile reads "58% / 116"; the Our Spirits
    index blurb says 118 and the seed was 118. The product's own page is read (116).
  - Tanager: "Aged for 6 years" in the product copy is read as 6 (the same page also says "at least 6 years" and quotes
    "our finest 6-year old high rye bourbon" as a component; the plain sentence is the bottle's). Its class is bourbon: the
    page's "Cigar Blend" is a style, not a cross-type blend, so class_raw leaves the word out (spirit_type() would read it
    as 'blend'). Its "mashbill" block is the three blended bourbons (53% Blue Corn, 25% Red Corn, 22% White Corn), stored as printed.
  - The Musician and The Artist say "oak-aged at least two years" (a floor, on the Our Spirits index and the Single Barrel FAQ)
    and the product pages state no age: none is read; the seeded 2 yr on The Musician, The Artist and both Cask Strengths is
    listed for the owner.
Not imported, and why: Single Barrel Whiskey (a retailer/bar program; every barrel differs, the page prints no proof),
the Limited Releases page (Nancy's Pick monthly, Distillery Exclusives #01-#02, Rare Stock #01-#08, each a one-off or
small-run release) and the Archive (Distillery Reserve Series, Monster Mash 2020-2025, earlier batches): these are listed with
proofs but are one-off bottlings, not the standing lineup, and no seed asks for them; they are cached as evidence. American
Gin is not whiskey. Merchandise (`/product/...`) is not whiskey."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Still Austin Whiskey Co."
DELAY = 6
BASE = "https://www.stillaustin.com/"
IMAGE_PREFIX = "https://cdn.prod.website-files.com/"
CATALOG_FAMILIES = ["Still Austin"]
PRODUCER_BY_FAMILY = {}
FAMILY = "Still Austin"

# path → (expression, [catalog names it answers to], class statement)
PAGES = {
    "spirits/straight-bourbon-whiskey": ("The Musician", ["Still Austin Straight Bourbon", "Still Austin Straight Bourbon Whiskey", "Still Austin Straight Bourbon: The Musician"],
                                         "Straight Bourbon Whiskey"),
    "spirits/the-artist-straight-rye-whiskey": ("The Artist Rye", ["Still Austin The Artist", "Still Austin The Artist Straight Rye Whiskey", "Still Austin Straight Rye"],
                                                "Straight Rye Whiskey"),
    "spirits/cask-strength-bourbon": ("Cask Strength", ["Still Austin Cask Strength Bourbon", "Still Austin Cask Strength Bourbon Whiskey"], "Straight Bourbon Whiskey"),
    "spirits/cask-strength-rye-whiskey": ("Cask Strength Rye", ["Still Austin Cask Strength Rye Whiskey"], "Straight Rye Whiskey"),
    "tanager-cigar-blend-bourbon-whiskey": ("Tanager Cigar Blend", ["Still Austin Tanager", "Still Austin Tanager Cigar Blend Bourbon Whiskey"], "Bourbon Whiskey"),
}
# the Bottled in Bond page's four whiskeys: listing heading → (expression, [aliases], class statement, image file keyword)
BIB_PAGE = "spirits/bottled-in-bond"
BIB = {
    "RED CORN BOURBON WHISKEY": ("Bottled in Bond Red Corn", ["Still Austin Red Corn Bourbon Whiskey", "Still Austin Bottled in Bond Red Corn Bourbon Whiskey"],
                                 "Bottled in Bond Straight Bourbon Whiskey", "Redcorn"),
    "STRAIGHT BOURBON WHISKEY": ("Bottled in Bond", ["Still Austin Bottled in Bond Straight Bourbon Whiskey"], "Bottled in Bond Straight Bourbon Whiskey", "Horse"),
    "BLUE CORN BOURBON WHISKEY": ("Blue Corn Bottled in Bond", ["Still Austin Bottled in Bond Blue Corn Bourbon Whiskey", "Still Austin Blue Corn Bourbon Whiskey"],
                                  "Bottled in Bond Straight Bourbon Whiskey", "Bluecorn"),
    "STRAIGHT RYE WHISKEY": ("Bottled in Bond Rye", ["Still Austin Bottled in Bond Straight Rye Whiskey", "Still Austin Bottled in Bond Straight Rye"],
                             "Bottled in Bond Straight Rye Whiskey", "StraightRye"),
}
# Cached as evidence only (no records): the lineup index, the Single Barrel program, Limited Releases, the Archive.
EVIDENCE = ["spirits", "singlebarrel", "limited-releases", "spirits/archive"]

DISCONTINUED_BY_MAKER = set()
CORE = {"The Musician", "The Artist Rye", "Cask Strength", "Cask Strength Rye"}
RARITY = [(r"bottled in bond|tanager", "limited"), (r".", "shelf")]
MASH_BILLS = {}


def list_urls(fetcher) -> list[str]:
    return [BASE + p for p in [*PAGES, BIB_PAGE, *EVIDENCE]]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body)).replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\|\s*)+", "| ", t)


def _mash_block(text: str) -> str | None:
    """'Mashbill| 70%| Whitecorn| 25%| Rye| 5%| Malted barley| 100%| Texas|' → '70% White Corn, 25% Rye, 5% Malted Barley'."""
    i = text.find("Mashbill|")
    if i < 0:
        return None
    seg = text[i + len("Mashbill|"):]
    seg = seg.split("100%| Texas", 1)[0]
    parts = re.findall(r"(\d{1,3})%\|\s*([^|]+?)\s*(?=\||$)", seg)
    return ", ".join(f"{p}% {g.replace('Whitecorn', 'White Corn').title()}" for p, g in parts) or None


def _image(page: str, keyword: str | None = None) -> str | None:
    for tag in re.findall(r"<img[^>]*>", page):
        src = re.search(r'src="(https://cdn\.prod\.website-files\.com/[^"]+\.(?:webp|avif|png|jpg|jpeg))"', tag)
        alt = re.search(r'alt="([^"]*)"', tag)
        if not src or src.group(1).endswith(".svg"):
            continue
        if keyword:
            if keyword in src.group(1):
                return src.group(1)
        elif alt and re.match(r"(?:A )?bottle of still austin", alt.group(1), re.I) and not re.search(r"hero|box", src.group(1), re.I):
            return src.group(1)
    return None


def _bib(url: str, page: str) -> list[BottlingRecord]:
    text = _flat(page)
    out = []
    for heading, (expression, aliases, class_raw, key) in BIB.items():
        found = list(re.finditer(re.escape(heading) + r"\| 50% (?:ABV|ALC / VOL)\s*(?:/|\|)\s*100 PROOF\b.*?MASHBILL:\| ([^|]+)\|", text))
        if not found:
            continue
        last = found[-1]  # the newest listing of this whiskey
        mash = ", ".join(w.strip().title() for w in last.group(1).split(","))
        name = f"{FAMILY} {expression}"
        out.append(BottlingRecord(
            brand_family=FAMILY, expression=expression, name=name, source_url=url, proof=100.0,  # the listing prints "100 PROOF"
            class_raw=class_raw, mash_raw=mash, image_url=_image(page, key),
            aliases=sorted(set(aliases) - {name}), is_core_range=False,
        ))
    return out


def parse(url: str, page: str):
    path = url.replace(BASE, "").strip("/")
    if path == BIB_PAGE:
        return _bib(url, page)
    if path not in PAGES:
        return None
    expression, aliases, class_raw = PAGES[path]
    name = f"{FAMILY} {expression}"
    text = _flat(page)

    proof = years = label = mash = None
    if path == "tanager-cigar-blend-bourbon-whiskey":
        m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", text, re.I)
        proof = float(m.group(1)) if m else None
        am = re.search(r"Aged for \d{1,2} years", text)
        years, label = age(am.group(0)) if am else (None, None)
        mm = re.search(r"MASHBILL\| (.*?)\| ALC / VOL", text)
        mash = re.sub(r"\band\s+", "", mm.group(1)).strip() if mm else None
    else:
        m = re.search(r"Alc / Vol / Proof\| [\d.]+% / (\d{2,3}(?:\.\d+)?)\|", text)
        proof = float(m.group(1)) if m else None
        mash = _mash_block(text)

    return BottlingRecord(
        brand_family=FAMILY, expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, mash_raw=mash, image_url=_image(page),
        aliases=sorted(set(aliases) - {name}), is_core_range=expression in CORE,
    )

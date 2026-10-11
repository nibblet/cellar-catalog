"""boundaryoak.co (Boundary Oak Distillery, Radcliff, Kentucky; the Lincoln, War Eagle, St. Michael, Patton ... brands).
Squarespace. robots.txt blocks named AI-training bots and a few query-string views and sets no Crawl-delay (our
honest "CellarCatalog" agent is not named), so DELAY is the project's usual 6. The sitemap lists every page; the
products index lists the whole range, including vodka, wine, moonshine, a cane spirit (Patton Armored Diesel) and
a lavender/cinnamon liqueur pair, none of which is whiskey and none of which is imported.

Each whiskey page carries two lines in its own copy: "PROOF: 105" and "AGE: 2-4 YEARS". Both are read from the page
text only. A RANGE is not a statement (BOURBON.md): the Lincoln page says "PROOF: 105-120 / AGE: 2-4 YEARS" for the
whole line, so it states no proof for any Lincoln bottling and confirms none of the three catalog rows; Mizunara,
Amburana ("105-115") and Wine Barrel Bourbon ("100-110") likewise state none. An age range is kept as the maker's
display label ("2-4 yr") and never an age_years; "5+ YEARS" (Patton) is a floor, kept as the label "5+ yr".

What the importer cannot do, on purpose: reproduce the hand-entered 'Lincoln 8 Year Single Barrel' (105 proof, 8
yr, source 'manual'). The Lincoln page lists no 8-year bottling and no single proof; those two figures come from
the owner's label photo (sql/20261010_lincoln_8yr.sql), which this track does not OCR. The row stays manual.
The seeded 'Lincoln KY Straight Bourbon' and its 'Cask Strength' twin (both 118 proof, 2 yr) are not on the page
either: it neither names a cask-strength bottling nor states 118, so they are left as seeds, not merged and not
marked discontinued (see the hand-off for the duplicate evidence).

The maker's online store (shop.boundaryoak.co, linked from every page; its sitemap lists lincoln-straight-bourbon-12,
gs-patton-bourbon-whiskey, war-eagle, st-michael ...) answers every product URL with a 307 to /age-verification,
so its product pages are not read: passing the gate would mean asserting an age on someone's behalf. Parked; a
person can read it, and a 'lincoln-straight-bourbon-12' page is the first thing to look at.

Not imported, and why:
- My Old Kentucky Home: states "PROOF: 100 / AGE: 2-4 YEARS" but its copy never says what the spirit is (only that
  Kentucky is "the home of bourbon distilleries"), so no spirit class is stated and the module will not invent one.
- Mizunara, Amburana, Wine Barrel Bourbon: proof is a range (above), the catalog holds no row for them, and a
  proof-less record is never added, so their pages are not crawled.
- St. Luke Lavender, Cinnful 69, the two moonshines, vodka, wines, Patton Armored Diesel: not whiskey bottlings.
- Bottled-in-Bond etc.: none of the pages claims it.

Naming: each brand is its own family (Lincoln already is). The page titles are the maker's names: 'Big Red 1
"Lady Victory"' is filed 'Big Red 1'. Class is read from the page's own words: Lincoln, Patton and Big Red 1 print
their class; War Eagle ("this exceptional Kentucky bourbon"), St. Michael ("A bourbon whiskey to celebrate") and Iron
Mike ("this bourbon honors") state it in the opening sentence, so their class is "Bourbon Whiskey" (not "Straight":
the pages never say straight)."""
from __future__ import annotations

import html
import re

from ...bourbon.model import BottlingRecord
from ...bourbon.normalize import age

PRODUCER = "Boundary Oak Distillery"
DELAY = 6
SITEMAP = "https://www.boundaryoak.co/sitemap.xml"
IMAGE_PREFIX = "https://images.squarespace-cdn.com/"
BASE = "https://www.boundaryoak.co/"
CATALOG_FAMILIES = ["Lincoln", "War Eagle", "St. Michael", "Big Red 1", "Patton", "Iron Mike", "My Old Kentucky Home"]
PRODUCER_BY_FAMILY = {}

BOURBON = "Bourbon Whiskey"
STRAIGHT = "Straight Bourbon Whiskey"
# slug → (family, expression, [catalog names it answers to], class statement or None, bottle-photo file name pattern)
PAGES = {
    "lincoln": ("Lincoln", None, [], STRAIGHT, r"lincoln-PNG"),
    "war-eagle": ("War Eagle", None, [], BOURBON, r"WAR-EAGLE-PNG"),
    "st-michael": ("St. Michael", None, [], BOURBON, r"RED-ST-MICHAEL"),
    "st-michael-special-edition": ("St. Michael", "Special Edition", [], BOURBON, r"BLUE-ST-MICHAEL"),
    "big-red-1": ("Big Red 1", None, ['Big Red 1 "Lady Victory"'], BOURBON, r"BIG-RED-1-PNG"),
    "patton-bourbon": ("Patton", None, ["Patton Bourbon", "Patton Bourbon Whiskey", "G. S. Patton Jr. Bourbon"], STRAIGHT, r"patton-bourbon-PNG"),
    "iron-mike": ("Iron Mike", None, ["Iron Mike Bourbon"], BOURBON, r"IRON-MIKE-png"),
    # States a proof and age but never says what the spirit is (see the docstring): crawled, class left out, skipped by the diff
    "my-old-kentucky-home": ("My Old Kentucky Home", None, [], None, r"MOKH"),
}
CORE = {"Lincoln", "Patton", "My Old Kentucky Home"}  # the "Flagship Flight" on the home page: Lincoln, MOKH, Patton ... (Platinum Flight: War Eagle, St. Michael, Mizunara)
RARITY = [(r"special edition", "limited"), (r".", "shelf")]
MASH_BILLS = {}

NAV_END = "Our Story | Contact |"
PAGE_END = "Be sure to visit our online store!"


def list_urls(fetcher) -> list[str]:
    return [BASE + slug for slug in PAGES]


def _flat(page: str) -> str:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", body))
    t = re.sub(r"\s+", " ", t).replace("’", "'").replace("\xa0", " ")
    return re.sub(r"(\|\s*)+", "| ", t)


def _own(text: str) -> str:
    """The product's own copy: after the site menu (the last 'Contact |' of the nav), before the store footer."""
    i = text.rfind(NAV_END)
    j = text.find(PAGE_END)
    return text[i + len(NAV_END):j] if 0 <= i < j else text


def _image(page: str, pattern: str) -> str | None:
    for u in re.findall(r'data-image="([^"]+)"', page):
        if re.search(pattern, u, re.I):
            return html.unescape(u)
    return None


def parse(url: str, page: str) -> BottlingRecord | None:
    slug = url.rstrip("/").split("/")[-1]
    if slug not in PAGES:
        return None
    family, expression, aliases, class_raw, image_pat = PAGES[slug]
    name = f"{family} {expression}" if expression else family
    own = _own(_flat(page))

    proof = None
    pm = re.search(r"PROOF:\s*([\d.]+)(\s*[-–]\s*[\d.]+)?", own)  # "PROOF: 105" is a statement, "PROOF: 105-120" a range
    if pm and not pm.group(2):
        proof = float(pm.group(1))

    years, label = None, None
    am = re.search(r"AGE:\s*([^|]+?)\s*\|", own)
    if am:
        raw = am.group(1).strip()
        plus = re.fullmatch(r"(\d{1,2})\+\s*YEARS?", raw, re.I)
        if plus:
            label = f"{plus.group(1)}+ yr"  # a floor ("over five years"), not an age
        else:
            years, label = age(raw)

    return BottlingRecord(
        brand_family=family, expression=expression, name=name, source_url=url, proof=proof,
        age_years=years, age_label=label, class_raw=class_raw, image_url=_image(page, image_pat),
        aliases=sorted(set(aliases) - {name}), is_core_range=family in CORE,
    )
